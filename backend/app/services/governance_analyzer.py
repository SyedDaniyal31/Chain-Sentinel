"""Unified governance intelligence: patterns, roles, and upgrade authority."""

from __future__ import annotations

import logging

from web3 import AsyncWeb3

from app.blockchain.access_control import (
    KNOWN_ROLES,
    encode_get_role_admin_call,
    encode_has_role_call,
    has_access_control_selectors,
    parse_has_role_result,
    parse_role_admin,
    role_id_hex,
    role_name_for_id,
)
from app.blockchain.contract_source_provider import ContractSourceProvider, NullContractSourceProvider
from app.blockchain.governance_patterns import (
    has_access_control_bytecode,
    has_ownable2step_selectors,
    has_proxy_admin_selectors,
)
from app.blockchain.multisig import is_gnosis_safe_multisig
from app.blockchain.ownable import OWNER_FUNCTION_SELECTOR, parse_ownable_owner
from app.blockchain.source_analysis_engine import SourceAnalysisEngine
from app.core.validators import normalize_eth_address
from app.models.enums import AdminType, ConfidenceLevel, ContractType, GovernanceType, UpgradeAuthority
from app.schemas.scan_result import GovernanceAnalysisData, GovernanceRoleData

logger = logging.getLogger(__name__)


class GovernanceAnalyzer:
    """
    Detect governance patterns, AccessControl role hierarchy, and upgrade authority.

    Builds on existing proxy/admin/owner/timelock reconnaissance from ContractAnalyzer.
    M4.2 enriches detections with verified source intelligence at HIGH confidence.
    """

    def __init__(
        self,
        web3: AsyncWeb3,
        *,
        chain_id: int | None = None,
        source_provider: ContractSourceProvider | None = None,
        source_engine: SourceAnalysisEngine | None = None,
    ) -> None:
        self._web3 = web3
        self._chain_id = chain_id
        self._source_provider = source_provider or NullContractSourceProvider()
        self._source_engine = source_engine or SourceAnalysisEngine()

    async def analyze(
        self,
        target_address: str,
        *,
        bytecode: bytes,
        logic_address: str | None,
        logic_bytecode: bytes | None,
        is_upgradeable: bool,
        admin_address: str | None,
        admin_type: AdminType | None,
        owner_address: str | None,
        owner_type: AdminType | None,
        is_timelock: bool,
        ownership_capability: bool,
        contract_type: ContractType | None,
    ) -> GovernanceAnalysisData:
        """Return governance typing, upgrade authority, and AccessControl role hierarchy."""
        if not bytecode:
            return GovernanceAnalysisData()

        logic = logic_bytecode if logic_bytecode is not None else bytecode
        probe_address = logic_address or target_address
        ownership_address = await self._probe_owner(probe_address, logic, ownership_capability)

        verified = await self._fetch_verified_source(probe_address)
        source_analysis = self._source_engine.analyze(
            verified,
            ownership_address=ownership_address,
        )

        roles = await self._analyze_roles(probe_address, logic, source_analysis=source_analysis)
        governance_type = self._resolve_governance_type(
            bytecode=bytecode,
            logic_bytecode=logic,
            is_upgradeable=is_upgradeable,
            admin_address=admin_address,
            admin_type=admin_type,
            is_timelock=is_timelock,
            ownership_capability=ownership_capability,
            contract_type=contract_type,
            roles=roles,
            source_analysis=source_analysis,
        )
        upgrade_authority = self._resolve_upgrade_authority(
            is_upgradeable=is_upgradeable,
            admin_type=admin_type,
            owner_type=owner_type,
            is_timelock=is_timelock,
        )

        ownership_renounced = bool(source_analysis and source_analysis.renounced_ownership)
        if ownership_renounced:
            ownership_address = None

        source_confidence = (
            source_analysis.source_confidence
            if source_analysis is not None
            else ConfidenceLevel.LOW
        )

        return GovernanceAnalysisData(
            governance_type=governance_type,
            upgrade_authority=upgrade_authority,
            has_timelock=is_timelock,
            role_count=len(roles),
            roles=roles,
            ownership_address=ownership_address,
            ownership_renounced=ownership_renounced,
            source_confidence=source_confidence,
        )

    async def _fetch_verified_source(self, logic_address: str):
        if self._chain_id is None:
            return None
        return await self._source_provider.get_verified_source(logic_address, self._chain_id)

    async def _probe_owner(
        self,
        contract_address: str,
        logic_bytecode: bytes,
        ownership_capability: bool,
    ) -> str | None:
        owner_selector = bytes.fromhex(OWNER_FUNCTION_SELECTOR[2:])
        if not ownership_capability and owner_selector not in logic_bytecode:
            return None

        checksum = AsyncWeb3.to_checksum_address(normalize_eth_address(contract_address))
        try:
            return_data = await self._web3.eth.call(
                {"to": checksum, "data": OWNER_FUNCTION_SELECTOR}
            )
        except Exception:
            logger.debug("owner() unavailable on %s", contract_address)
            return None

        return parse_ownable_owner(bytes(return_data))

    async def _analyze_roles(
        self,
        contract_address: str,
        logic_bytecode: bytes,
        *,
        source_analysis,
    ) -> list[GovernanceRoleData]:
        has_on_chain_ac = has_access_control_selectors(logic_bytecode) or has_access_control_bytecode(
            logic_bytecode
        )
        has_source_ac = bool(source_analysis and source_analysis.access_control.detected)

        if not has_on_chain_ac and not has_source_ac:
            return []

        checksum = AsyncWeb3.to_checksum_address(normalize_eth_address(contract_address))
        roles: list[GovernanceRoleData] = []
        role_names = set(KNOWN_ROLES.keys())
        if source_analysis is not None:
            role_names.update(source_analysis.role_names)

        for role_name in sorted(role_names):
            role_id = KNOWN_ROLES.get(role_name)
            if role_id is None and role_name.endswith("_ROLE"):
                continue
            if role_id is None:
                continue

            admin_role_id = await self._read_role_admin(checksum, role_id)
            if admin_role_id is None and not has_source_ac:
                continue

            admin_role_name = (
                role_name_for_id(admin_role_id) if admin_role_id is not None else "DEFAULT_ADMIN_ROLE"
            )
            roles.append(
                GovernanceRoleData(
                    name=role_name,
                    role_id=role_id_hex(role_id),
                    admin_role_name=admin_role_name,
                    admin_role_id=role_id_hex(admin_role_id) if admin_role_id is not None else None,
                    is_default_admin=role_name == "DEFAULT_ADMIN_ROLE",
                )
            )

        if roles:
            return _sort_roles(roles)

        if has_source_ac and source_analysis is not None:
            for role_name in sorted(source_analysis.role_names):
                roles.append(
                    GovernanceRoleData(
                        name=role_name,
                        role_id="0x" + "00" * 32,
                        admin_role_name="DEFAULT_ADMIN_ROLE",
                        admin_role_id="0x" + "00" * 32,
                        is_default_admin=role_name == "DEFAULT_ADMIN_ROLE",
                    )
                )

        return _sort_roles(roles)

    async def _read_role_admin(self, checksum_address: str, role_id: bytes) -> bytes | None:
        try:
            return_data = await self._web3.eth.call(
                {
                    "to": checksum_address,
                    "data": encode_get_role_admin_call(role_id),
                }
            )
        except Exception:
            return None
        return parse_role_admin(bytes(return_data))

    async def _probe_has_role(
        self,
        checksum_address: str,
        role_id: bytes,
        account: str,
    ) -> bool | None:
        try:
            return_data = await self._web3.eth.call(
                {
                    "to": checksum_address,
                    "data": encode_has_role_call(role_id, account),
                }
            )
        except Exception:
            return None
        return parse_has_role_result(bytes(return_data))

    def _resolve_governance_type(
        self,
        *,
        bytecode: bytes,
        logic_bytecode: bytes,
        is_upgradeable: bool,
        admin_address: str | None,
        admin_type: AdminType | None,
        is_timelock: bool,
        ownership_capability: bool,
        contract_type: ContractType | None,
        roles: list[GovernanceRoleData],
        source_analysis,
    ) -> GovernanceType:
        if contract_type == ContractType.MULTISIG or is_gnosis_safe_multisig(bytecode):
            return GovernanceType.MULTISIG

        if is_timelock or contract_type == ContractType.TIMELOCK:
            return GovernanceType.TIMELOCK

        if roles or (source_analysis and source_analysis.access_control.detected):
            return GovernanceType.ACCESS_CONTROL

        if is_upgradeable and admin_address and admin_type == AdminType.CONTRACT:
            admin_code_hint = has_proxy_admin_selectors(bytecode)
            if admin_code_hint or admin_address:
                return GovernanceType.PROXY_ADMIN

        if has_ownable2step_selectors(logic_bytecode):
            return GovernanceType.OWNABLE2STEP

        owner_selector = bytes.fromhex(OWNER_FUNCTION_SELECTOR[2:])
        if (
            ownership_capability
            or owner_selector in logic_bytecode
            or (source_analysis and source_analysis.ownable.detected)
        ):
            return GovernanceType.OWNABLE

        if is_upgradeable or admin_address:
            return GovernanceType.UNKNOWN

        return GovernanceType.NONE

    def _resolve_upgrade_authority(
        self,
        *,
        is_upgradeable: bool,
        admin_type: AdminType | None,
        owner_type: AdminType | None,
        is_timelock: bool,
    ) -> UpgradeAuthority:
        if not is_upgradeable:
            return UpgradeAuthority.NONE

        if is_timelock:
            return UpgradeAuthority.TIMELOCK

        effective_type = owner_type if owner_type is not None else admin_type

        if effective_type == AdminType.MULTISIG:
            return UpgradeAuthority.MULTISIG
        if effective_type == AdminType.EOA:
            return UpgradeAuthority.EOA
        if effective_type == AdminType.CONTRACT:
            return UpgradeAuthority.CONTRACT

        return UpgradeAuthority.UNKNOWN


def _sort_roles(roles: list[GovernanceRoleData]) -> list[GovernanceRoleData]:
    return sorted(
        roles,
        key=lambda role: (0 if role.is_default_admin else 1, role.name),
    )
