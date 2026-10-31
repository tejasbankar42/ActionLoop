"""Thin factory around the official MST Python SDK (`mst-sdk-python`).

The SDK's Provider wraps web3.py and its Signer wraps eth-account. We construct them directly
with the configured RPC URL (the SDK's `Client("testnet")` hard-codes its own URL table, and its
constants list mainnet's chain id as 1 while the live RPC reports 4646), then validate the chain
id reported by the RPC before any write.
"""

from functools import lru_cache

from mst_blockchain_sdk import Provider, Signer

from app.blockchain.network_config import network
from app.core.config import get_settings


class ChainMismatchError(RuntimeError):
    pass


@lru_cache
def get_provider() -> Provider:
    return Provider(network()["rpc_url"])


@lru_cache
def get_signer() -> Signer | None:
    key = get_settings().mst_relayer_private_key
    if not key:
        return None
    return Signer(key, get_provider())


def relayer_address() -> str | None:
    signer = get_signer()
    return signer.address if signer else None


def assert_expected_chain() -> int:
    chain_id = get_provider().web3.eth.chain_id
    expected = network()["chain_id"]
    if chain_id != expected:
        raise ChainMismatchError(f"RPC reports chain {chain_id}, expected {expected}")
    return chain_id


def reset_clients() -> None:
    get_provider.cache_clear()
    get_signer.cache_clear()
