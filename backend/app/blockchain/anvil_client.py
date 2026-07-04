"""Low-level JSON-RPC helpers for Foundry Anvil fork management."""

from __future__ import annotations

import asyncio
import logging
import shutil
import socket
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AnvilForkConfig:
    """Parameters for resetting an Anvil instance to a mainnet fork."""

    fork_rpc_url: str
    chain_id: int
    block_number: int | None = None


class AnvilRpcClient:
    """Client for Anvil-specific JSON-RPC methods used during trade simulation."""

    def __init__(
        self,
        rpc_url: str,
        *,
        timeout_seconds: int = 30,
    ) -> None:
        self._rpc_url = rpc_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._request_id = 0

    async def reset_fork(self, config: AnvilForkConfig) -> None:
        """Reset Anvil state to a fresh fork of the upstream chain."""
        forking: dict[str, Any] = {"jsonRpcUrl": config.fork_rpc_url}
        if config.block_number is not None:
            forking["blockNumber"] = hex(config.block_number)

        await self._rpc("anvil_reset", [{"forking": forking}])
        await self._rpc("anvil_setChainId", [hex(config.chain_id)])

    async def impersonate_account(self, address: str) -> None:
        await self._rpc("anvil_impersonateAccount", [address])

    async def stop_impersonating_account(self, address: str) -> None:
        await self._rpc("anvil_stopImpersonatingAccount", [address])

    async def set_balance(self, address: str, balance_wei: int) -> None:
        await self._rpc("anvil_setBalance", [address, hex(balance_wei)])

    async def eth_call(self, transaction: dict[str, Any]) -> bytes:
        result = await self._rpc("eth_call", [transaction, "latest"])
        if not isinstance(result, str):
            raise RuntimeError("eth_call returned unexpected payload")
        return bytes.fromhex(result[2:] if result.startswith("0x") else result)

    async def eth_send_transaction(self, transaction: dict[str, Any]) -> str:
        tx_hash = await self._rpc("eth_sendTransaction", [transaction])
        if not isinstance(tx_hash, str):
            raise RuntimeError("eth_sendTransaction returned unexpected payload")
        return tx_hash

    async def wait_for_transaction(self, tx_hash: str, *, timeout_seconds: int = 30) -> bool:
        deadline = asyncio.get_event_loop().time() + timeout_seconds
        while asyncio.get_event_loop().time() < deadline:
            receipt = await self._rpc("eth_getTransactionReceipt", [tx_hash])
            if isinstance(receipt, dict) and receipt.get("status") is not None:
                return receipt["status"] == "0x1"
            await asyncio.sleep(0.05)
        return False

    async def get_balance(self, address: str) -> int:
        result = await self._rpc("eth_getBalance", [address, "latest"])
        if not isinstance(result, str):
            return 0
        return int(result, 16)

    async def _rpc(self, method: str, params: list[Any]) -> Any:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._request_id,
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(self._rpc_url, json=payload)
            response.raise_for_status()
            body = response.json()

        if "error" in body:
            raise RuntimeError(f"Anvil RPC {method} failed: {body['error']}")

        return body.get("result")


class AnvilProcessManager:
    """Optional helper to spawn a local Anvil fork process when none is running."""

    def __init__(
        self,
        *,
        anvil_binary: str = "anvil",
        host: str = "127.0.0.1",
    ) -> None:
        self._anvil_binary = anvil_binary
        self._host = host
        self._process: asyncio.subprocess.Process | None = None
        self._rpc_url: str | None = None

    @property
    def rpc_url(self) -> str | None:
        return self._rpc_url

    async def start_fork(self, config: AnvilForkConfig) -> str:
        """Launch Anvil with --fork-url and return the JSON-RPC URL."""
        if self._process is not None and self._process.returncode is None:
            return self._rpc_url or ""

        if shutil.which(self._anvil_binary) is None:
            raise FileNotFoundError(f"Anvil binary not found: {self._anvil_binary}")

        port = _find_free_port(self._host)
        cmd = [
            self._anvil_binary,
            "--fork-url",
            config.fork_rpc_url,
            "--chain-id",
            str(config.chain_id),
            "--host",
            self._host,
            "--port",
            str(port),
        ]
        if config.block_number is not None:
            cmd.extend(["--fork-block-number", str(config.block_number)])

        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        self._rpc_url = f"http://{self._host}:{port}"
        await asyncio.sleep(1.5)
        return self._rpc_url

    async def stop(self) -> None:
        if self._process is None:
            return
        if self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except TimeoutError:
                self._process.kill()
        self._process = None
        self._rpc_url = None


def _find_free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])
