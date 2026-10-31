"""MST network + deployed-contract resolution. Everything is overridable through backend/.env."""

import json
from pathlib import Path

from app.core.config import BACKEND_DIR, get_settings

ABI_PATH = Path(__file__).parent / "abi" / "ActionLoopAuditRegistry.json"
DEPLOYMENTS_DIR = BACKEND_DIR.parent / "contracts" / "deployments"
HARDHAT_NETWORK_NAME = {"testnet": "mstTestnet", "mainnet": "mstMainnet"}


def network() -> dict:
    return get_settings().network


def load_abi() -> list:
    if not ABI_PATH.exists():
        return []
    return json.loads(ABI_PATH.read_text())["abi"]


def deployment_record() -> dict | None:
    """Deployment written by contracts/scripts/deploy.js for the active network, if any."""
    net = get_settings().mst_network
    path = DEPLOYMENTS_DIR / f"{HARDHAT_NETWORK_NAME.get(net, net)}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return None
    return None


def contract_address() -> str | None:
    s = get_settings()
    if s.audit_registry_address:
        return s.audit_registry_address
    rec = deployment_record()
    if rec and rec.get("chainId") == network()["chain_id"]:
        return rec.get("address")
    return None


def explorer_tx(tx_hash: str | None) -> str | None:
    return f"{network()['explorer']}/tx/{tx_hash}" if tx_hash else None


def explorer_address(address: str | None) -> str | None:
    return f"{network()['explorer']}/address/{address}" if address else None
