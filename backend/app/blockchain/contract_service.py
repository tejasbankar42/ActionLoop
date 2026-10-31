"""Read/write access to the deployed ActionLoopAuditRegistry contract."""

import hashlib

from web3 import Web3

from app.blockchain import mst_client
from app.blockchain.network_config import contract_address, load_abi

EVENT_ANCHORED_SIG = "EventAnchored(bytes32,bytes32,bytes32,address,uint64)"


class NotConfiguredError(RuntimeError):
    pass


def to_bytes32_hex(hex_hash: str) -> str:
    h = hex_hash.lower().removeprefix("0x")
    if len(h) != 64:
        raise ValueError("expected a 32-byte hex hash")
    return "0x" + h


def workflow_id_hash(workflow_id: str | None) -> str:
    # Only the hash of the workflow UUID goes on-chain, never the UUID itself.
    return "0x" + hashlib.sha256((workflow_id or "system").encode()).hexdigest()


def event_type_bytes32(label: str) -> bytes:
    raw = label.encode("ascii")[:32]
    return raw.ljust(32, b"\0")


def event_type_from_bytes32(raw: bytes) -> str:
    return raw.rstrip(b"\0").decode("ascii", errors="replace")


def is_configured() -> bool:
    return bool(contract_address() and load_abi())


def get_contract():
    address = contract_address()
    abi = load_abi()
    if not address or not abi:
        raise NotConfiguredError("Audit registry contract address or ABI is not configured")
    w3 = mst_client.get_provider().web3
    return w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)


def is_anchored(event_hash: str) -> bool:
    return bool(get_contract().functions.isAnchored(to_bytes32_hex(event_hash)).call())


def get_record(event_hash: str) -> dict | None:
    rec = get_contract().functions.getRecord(to_bytes32_hex(event_hash)).call()
    workflow_hash, event_type, submitter, anchored_at, block_number = rec
    if anchored_at == 0:
        return None
    return {
        "workflow_id_hash": "0x" + bytes(workflow_hash).hex(),
        "event_type": event_type_from_bytes32(bytes(event_type)),
        "submitter": submitter,
        "anchored_at": int(anchored_at),
        "block_number": int(block_number),
    }


def contract_summary() -> dict:
    c = get_contract()
    relayer = mst_client.relayer_address()
    return {
        "owner": c.functions.owner().call(),
        "paused": c.functions.paused().call(),
        "total_anchored": int(c.functions.totalAnchored().call()),
        "relayer_is_submitter": bool(c.functions.isSubmitter(relayer).call()) if relayer else None,
    }


def event_topic() -> str:
    return "0x" + Web3.keccak(text=EVENT_ANCHORED_SIG).hex().removeprefix("0x")


def find_anchor_tx(event_hash: str, from_block: int | None = None) -> dict | None:
    """Locate the transaction that anchored `event_hash` via the indexed EventAnchored log."""
    c = get_contract()
    w3 = mst_client.get_provider().web3
    latest = w3.eth.block_number
    start = from_block if from_block is not None else max(0, latest - 200_000)
    logs = w3.eth.get_logs({
        "address": c.address,
        "fromBlock": start,
        "toBlock": latest,
        "topics": [event_topic(), to_bytes32_hex(event_hash)],
    })
    if not logs:
        return None
    log = logs[0]
    return {"tx_hash": "0x" + bytes(log["transactionHash"]).hex().removeprefix("0x"),
            "block_number": int(log["blockNumber"])}


def build_anchor_tx(event_hash: str, wf_hash: str, event_type: str, sender: str) -> dict:
    fn = get_contract().functions.anchorEvent(
        to_bytes32_hex(event_hash), to_bytes32_hex(wf_hash), event_type_bytes32(event_type)
    )
    return fn.build_transaction({"from": sender})


def receipt_anchors(receipt, event_hash: str) -> bool:
    """True if a mined receipt contains EventAnchored(eventHash=...) emitted by our contract."""
    c = get_contract()
    want_topic = event_topic().lower()
    want_hash = to_bytes32_hex(event_hash).lower()
    for log in receipt["logs"]:
        if log["address"].lower() != c.address.lower() or len(log["topics"]) < 2:
            continue
        t0 = "0x" + bytes(log["topics"][0]).hex().removeprefix("0x")
        t1 = "0x" + bytes(log["topics"][1]).hex().removeprefix("0x")
        if t0.lower() == want_topic and t1.lower() == want_hash:
            return True
    return False
