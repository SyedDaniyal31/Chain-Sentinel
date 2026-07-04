"""On-chain contract type classification for security intelligence."""

from __future__ import annotations

import logging

from web3 import AsyncWeb3

from app.blockchain.erc165 import (
    INTERFACE_ID_ERC1155,
    INTERFACE_ID_ERC165,
    INTERFACE_ID_ERC721,
    encode_supports_interface_call,
    parse_supports_interface_result,
)
from app.blockchain.eip1967 import (
    EIP1967_ADMIN_SLOT,
    EIP1967_BEACON_SLOT,
    EIP1967_IMPLEMENTATION_SLOT,
    parse_eip1967_admin,
    parse_eip1967_implementation,
)
from app.blockchain.multisig import is_gnosis_safe_multisig
from app.blockchain.source_verification import ContractSourceProvider, NullContractSourceProvider
from app.blockchain.token_standards import TokenStandardFlags, detect_token_standards_from_bytecode
from app.core.validators import normalize_eth_address
from app.models.enums import ContractType, ProxyType
from app.schemas.scan_result import ContractClassificationData
from app.services.timelock_analyzer import TimelockAnalyzer

logger = logging.getLogger(__name__)


class ContractClassifier:
    """
    Classify EVM targets using ERC-165, bytecode selectors, and EIP-1967 proxy slots.

    Priority for ``contract_type``:
        EOA → Timelock → Multisig → ERC1155 → ERC721 → ERC20 → Proxy → Unknown
    """

    def __init__(
        self,
        web3: AsyncWeb3,
        *,
        chain_id: int | None = None,
        source_provider: ContractSourceProvider | None = None,
        timelock_analyzer: TimelockAnalyzer | None = None,
    ) -> None:
        self._web3 = web3
        self._chain_id = chain_id
        self._source_provider = source_provider or NullContractSourceProvider()
        self._timelock_analyzer = timelock_analyzer or TimelockAnalyzer(web3)

    async def classify(
        self,
        target_address: str,
        *,
        bytecode: bytes,
        is_contract: bool,
        implementation_address: str | None = None,
        implementation_bytecode: bytes | None = None,
        admin_address: str | None = None,
        is_timelock_hint: bool = False,
    ) -> ContractClassificationData:
        """Return contract_type, proxy_type, and Etherscan verification status."""
        if not is_contract:
            return ContractClassificationData(
                contract_type=ContractType.EOA,
                proxy_type=ProxyType.NONE,
                is_verified=False,
            )

        normalized = normalize_eth_address(target_address)
        proxy_type = await self._detect_proxy_type(normalized, admin_address, implementation_address)
        logic_bytecode = implementation_bytecode if implementation_bytecode is not None else bytecode
        logic_address = implementation_address or normalized

        is_verified = await self._is_verified_on_explorer(logic_address)
        contract_type = await self._resolve_contract_type(
            normalized,
            bytecode=bytecode,
            logic_address=logic_address,
            logic_bytecode=logic_bytecode,
            is_timelock_hint=is_timelock_hint,
            proxy_type=proxy_type,
        )

        return ContractClassificationData(
            contract_type=contract_type,
            proxy_type=proxy_type,
            is_verified=is_verified,
        )

    async def _detect_proxy_type(
        self,
        target_address: str,
        admin_address: str | None,
        implementation_address: str | None,
    ) -> ProxyType:
        checksum = AsyncWeb3.to_checksum_address(target_address)

        try:
            beacon_word = await self._web3.eth.get_storage_at(checksum, EIP1967_BEACON_SLOT)
            beacon_address = parse_eip1967_implementation(bytes(beacon_word))
            if beacon_address is not None:
                return ProxyType.EIP1967_BEACON
        except Exception:
            logger.debug("Beacon slot read failed for %s", target_address)

        if implementation_address is None:
            try:
                impl_word = await self._web3.eth.get_storage_at(
                    checksum,
                    EIP1967_IMPLEMENTATION_SLOT,
                )
                implementation_address = parse_eip1967_implementation(bytes(impl_word))
            except Exception:
                logger.debug("Implementation slot read failed for %s", target_address)
                return ProxyType.NONE

        if implementation_address is None:
            return ProxyType.NONE

        if admin_address is None:
            try:
                admin_word = await self._web3.eth.get_storage_at(checksum, EIP1967_ADMIN_SLOT)
                admin_address = parse_eip1967_admin(bytes(admin_word))
            except Exception:
                logger.debug("Admin slot read failed for %s", target_address)

        if admin_address is not None:
            return ProxyType.EIP1967_TRANSPARENT
        return ProxyType.EIP1967_UUPS

    async def _resolve_contract_type(
        self,
        target_address: str,
        *,
        bytecode: bytes,
        logic_address: str,
        logic_bytecode: bytes,
        is_timelock_hint: bool,
        proxy_type: ProxyType,
    ) -> ContractType:
        if is_timelock_hint:
            return ContractType.TIMELOCK

        timelock_analysis = await self._timelock_analyzer.analyze(target_address)
        if timelock_analysis.is_timelock:
            return ContractType.TIMELOCK

        if is_gnosis_safe_multisig(bytecode):
            return ContractType.MULTISIG

        token_flags = await self._detect_token_standards(logic_address, logic_bytecode)
        if token_flags.is_erc1155:
            return ContractType.ERC1155
        if token_flags.is_erc721:
            return ContractType.ERC721
        if token_flags.is_erc20:
            return ContractType.ERC20

        if proxy_type != ProxyType.NONE:
            return ContractType.PROXY

        return ContractType.UNKNOWN

    async def _detect_token_standards(
        self,
        logic_address: str,
        logic_bytecode: bytes,
    ) -> TokenStandardFlags:
        erc165_flags = await self._detect_token_standards_via_erc165(logic_address)
        if erc165_flags.is_erc1155 or erc165_flags.is_erc721:
            return erc165_flags

        bytecode_flags = detect_token_standards_from_bytecode(logic_bytecode)
        if bytecode_flags.is_erc1155 or bytecode_flags.is_erc721 or bytecode_flags.is_erc20:
            return bytecode_flags

        return erc165_flags if erc165_flags.is_erc20 else bytecode_flags

    async def _detect_token_standards_via_erc165(self, contract_address: str) -> TokenStandardFlags:
        checksum = AsyncWeb3.to_checksum_address(normalize_eth_address(contract_address))

        supports_165 = await self._supports_interface(checksum, INTERFACE_ID_ERC165)
        if not supports_165:
            return TokenStandardFlags()

        is_erc1155 = await self._supports_interface(checksum, INTERFACE_ID_ERC1155)
        if is_erc1155:
            return TokenStandardFlags(is_erc1155=True)

        is_erc721 = await self._supports_interface(checksum, INTERFACE_ID_ERC721)
        if is_erc721:
            return TokenStandardFlags(is_erc721=True)

        return TokenStandardFlags()

    async def _supports_interface(self, checksum_address: str, interface_id: bytes) -> bool:
        try:
            return_data = await self._web3.eth.call(
                {
                    "to": checksum_address,
                    "data": encode_supports_interface_call(interface_id),
                }
            )
        except Exception:
            return False
        return parse_supports_interface_result(bytes(return_data))

    async def _is_verified_on_explorer(self, contract_address: str) -> bool:
        if self._chain_id is None:
            return False
        verified = await self._source_provider.get_verified_source(
            contract_address,
            self._chain_id,
        )
        return verified is not None
