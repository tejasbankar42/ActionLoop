"""Anchoring pipeline: audit event -> BlockchainAnchor row -> MST transaction -> verified receipt.

Status machine (blockchain_anchors.status):
  queued         waiting for the relayer worker or a reviewer's BridgeKey wallet
  submitted      tx broadcast, tx_hash stored, waiting for receipt
  confirmed      receipt status == 1 AND contract.isAnchored(eventHash) == true
  failed         receipt reverted or repeated submission errors (retryable)
  not_configured contract or relayer not configured; nothing was sent

Duplicate protection: one row per (chain_id, event_hash); before (re)submitting we always ask the
contract whether the hash is already anchored, and the contract itself reverts on duplicates.
"""

import logging
import threading
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.blockchain import contract_service as cs
from app.blockchain import mst_client
from app.blockchain.network_config import contract_address, network
from app.core.config import get_settings
from app.database.session import SessionLocal
from app.models import AuditEvent, BlockchainAnchor

log = logging.getLogger("actionloop.blockchain")
MAX_ATTEMPTS = 3
_worker_wake = threading.Event()
_process_lock = threading.Lock()


def _now():
    return datetime.now(timezone.utc)


def maybe_queue_anchor(db: Session, ev: AuditEvent) -> BlockchainAnchor | None:
    if ev.event_type not in get_settings().anchor_types or (ev.payload or {}).get("seeded"):
        return None  # seeded history is illustrative and is never written on-chain
    net = network()
    anchor = BlockchainAnchor(
        audit_event_id=ev.id,
        workflow_id=ev.workflow_id,
        event_hash="0x" + ev.hash,
        workflow_id_hash=cs.workflow_id_hash(ev.workflow_id),
        event_type=ev.event_type,
        network=net["key"],
        chain_id=net["chain_id"],
        contract_address=contract_address(),
        status="queued" if cs.is_configured() else "not_configured",
    )
    db.add(anchor)
    db.flush()
    _worker_wake.set()
    return anchor


def queue_existing_event(db: Session, ev: AuditEvent) -> BlockchainAnchor:
    """Manually queue any audit event (e.g. a reviewer anchors it from the UI)."""
    net = network()
    existing = db.execute(select(BlockchainAnchor).where(
        BlockchainAnchor.chain_id == net["chain_id"], BlockchainAnchor.event_hash == "0x" + ev.hash
    )).scalar_one_or_none()
    if existing:
        return existing
    anchor = BlockchainAnchor(
        audit_event_id=ev.id, workflow_id=ev.workflow_id, event_hash="0x" + ev.hash,
        workflow_id_hash=cs.workflow_id_hash(ev.workflow_id), event_type=ev.event_type,
        network=net["key"], chain_id=net["chain_id"], contract_address=contract_address(),
        status="queued" if cs.is_configured() else "not_configured",
    )
    db.add(anchor)
    db.commit()
    _worker_wake.set()
    return anchor


def _mark_confirmed(db: Session, a: BlockchainAnchor, tx_hash: str | None, block: int | None,
                    gas_used: int | None = None, submitter: str | None = None):
    a.status = "confirmed"
    a.tx_hash = tx_hash or a.tx_hash
    a.block_number = block or a.block_number
    a.gas_used = gas_used or a.gas_used
    a.submitter_address = submitter or a.submitter_address
    a.contract_address = contract_address()
    a.onchain_verified_at = _now()
    a.last_error = None
    db.commit()
    log.info("anchor confirmed event=%s tx=%s", a.event_hash, a.tx_hash)


def _adopt_existing_onchain(db: Session, a: BlockchainAnchor) -> bool:
    """If the hash is already on-chain (e.g. earlier attempt succeeded), adopt that proof."""
    if not cs.is_anchored(a.event_hash):
        return False
    rec = cs.get_record(a.event_hash) or {}
    found = None
    try:
        found = cs.find_anchor_tx(a.event_hash, from_block=max(0, rec.get("block_number", 0) - 1))
    except Exception as exc:  # log query limits vary by RPC
        log.warning("log lookup failed: %s", exc)
    _mark_confirmed(db, a, found and found["tx_hash"], rec.get("block_number"), submitter=rec.get("submitter"))
    return True


def process_anchor(db: Session, a: BlockchainAnchor) -> BlockchainAnchor:
    with _process_lock:
        db.refresh(a)
        if a.status == "confirmed":
            return a
        if not cs.is_configured():
            a.status = "not_configured"
            db.commit()
            return a
        provider = mst_client.get_provider()
        w3 = provider.web3
        try:
            mst_client.assert_expected_chain()
            if _adopt_existing_onchain(db, a):
                return a

            if a.status == "submitted" and a.tx_hash:
                receipt = _get_receipt(w3, a.tx_hash)
                if receipt is None:
                    age = (_now() - _aware(a.updated_at)).total_seconds()
                    if age < get_settings().anchor_receipt_timeout_s:
                        return a  # still pending; check again later, do not resubmit
                    a.last_error = "Receipt not found before timeout; will re-check on-chain state and resubmit"
                    a.status = "queued"
                    db.commit()
                    return a
                return _finish_with_receipt(db, a, receipt)

            signer = mst_client.get_signer()
            if signer is None:
                a.last_error = "No relayer key configured; anchor with a BridgeKey wallet from the Blockchain page"
                db.commit()
                return a
            if a.attempts >= MAX_ATTEMPTS:
                a.status = "failed"
                db.commit()
                return a

            tx = cs.build_anchor_tx(a.event_hash, a.workflow_id_hash, a.event_type, signer.address)
            tx.pop("gasPrice", None)
            tx.pop("maxFeePerGas", None)
            tx.pop("maxPriorityFeePerGas", None)
            tx["gas"] = int(provider.estimate_gas({k: tx[k] for k in ("from", "to", "data")}) * 1.25)
            a.attempts += 1
            tx_hash = signer.send_transaction(tx)  # MST SDK: signs with eth-account and broadcasts
            a.tx_hash = tx_hash if tx_hash.startswith("0x") else "0x" + tx_hash
            a.status = "submitted"
            a.submitted_via = "relayer"
            a.submitter_address = signer.address
            a.last_error = None
            db.commit()
            receipt = provider.wait_for_transaction(a.tx_hash)
            return _finish_with_receipt(db, a, receipt)
        except Exception as exc:
            db.rollback()
            a = db.get(BlockchainAnchor, a.id)
            a.last_error = f"{type(exc).__name__}: {exc}"[:1000]
            if a.status != "submitted":
                a.status = "failed" if a.attempts >= MAX_ATTEMPTS else "queued"
            db.commit()
            log.warning("anchor %s error: %s", a.id, exc)
            return a


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _get_receipt(w3, tx_hash: str):
    try:
        return w3.eth.get_transaction_receipt(tx_hash)
    except Exception:
        return None


def _finish_with_receipt(db: Session, a: BlockchainAnchor, receipt) -> BlockchainAnchor:
    if receipt["status"] != 1:
        a.status = "failed"
        a.last_error = "Transaction reverted on-chain"
        a.block_number = int(receipt["blockNumber"])
        db.commit()
        return a
    # Success is only declared after the contract itself confirms the hash.
    if cs.receipt_anchors(receipt, a.event_hash) and cs.is_anchored(a.event_hash):
        _mark_confirmed(db, a, a.tx_hash, int(receipt["blockNumber"]), int(receipt["gasUsed"]),
                        receipt["from"])
    else:
        a.status = "failed"
        a.last_error = "Receipt succeeded but no matching EventAnchored log / isAnchored() is false"
        db.commit()
    return a


def record_wallet_submission(db: Session, a: BlockchainAnchor, tx_hash: str) -> BlockchainAnchor:
    """A reviewer signed anchorEvent() in BridgeKey. Never trust the client: re-verify on-chain."""
    w3 = mst_client.get_provider().web3
    mst_client.assert_expected_chain()
    tx = w3.eth.get_transaction(tx_hash)
    if tx["to"] is None or tx["to"].lower() != (contract_address() or "").lower():
        raise ValueError("Transaction is not addressed to the ActionLoop audit registry")
    a.tx_hash = tx_hash
    a.status = "submitted"
    a.submitted_via = "wallet"
    a.submitter_address = tx["from"]
    a.attempts += 1
    db.commit()
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=get_settings().anchor_receipt_timeout_s)
    return _finish_with_receipt(db, a, receipt)


def set_submitter(address: str, authorized: bool) -> dict:
    """Owner-only contract call, signed by the backend key (which is the deployer/owner)."""
    from web3 import Web3

    signer = mst_client.get_signer()
    if signer is None or not cs.is_configured():
        raise RuntimeError("Relayer key or contract not configured")
    mst_client.assert_expected_chain()
    contract = cs.get_contract()
    if contract.functions.owner().call().lower() != signer.address.lower():
        raise RuntimeError("Backend key is not the registry owner; use the owner wallet instead")
    target = Web3.to_checksum_address(address)
    with _process_lock:
        tx = contract.functions.setSubmitter(target, authorized).build_transaction({"from": signer.address})
        tx.pop("gasPrice", None)
        tx.pop("maxFeePerGas", None)
        tx.pop("maxPriorityFeePerGas", None)
        provider = mst_client.get_provider()
        tx["gas"] = int(provider.estimate_gas({k: tx[k] for k in ("from", "to", "data")}) * 1.25)
        tx_hash = signer.send_transaction(tx)
        tx_hash = tx_hash if tx_hash.startswith("0x") else "0x" + tx_hash
        receipt = provider.wait_for_transaction(tx_hash)
    ok = receipt["status"] == 1 and contract.functions.isSubmitter(target).call() == authorized
    return {"address": target, "authorized": authorized, "tx_hash": tx_hash, "block_number": int(receipt["blockNumber"]),
            "confirmed": ok}


class AnchorWorker(threading.Thread):
    """Background relayer: drains queued anchors one at a time (keeps nonces sequential)."""

    def __init__(self):
        super().__init__(daemon=True, name="anchor-worker")
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()
        _worker_wake.set()

    def run(self):
        while not self._stop.is_set():
            _worker_wake.wait(timeout=10)
            _worker_wake.clear()
            if self._stop.is_set():
                break
            s = get_settings()
            if not (s.blockchain_auto_anchor and cs.is_configured() and mst_client.get_signer()):
                continue
            db = SessionLocal()
            try:
                pending = db.execute(select(BlockchainAnchor).where(
                    BlockchainAnchor.status.in_(["queued", "submitted"]),
                    BlockchainAnchor.chain_id == network()["chain_id"],
                ).order_by(BlockchainAnchor.created_at).limit(10)).scalars().all()
                for a in pending:
                    if a.status == "queued" and a.submitted_via == "wallet":
                        continue
                    process_anchor(db, a)
                    time.sleep(0.5)
            except Exception as exc:
                log.warning("anchor worker loop error: %s", exc)
            finally:
                db.close()


def requeue_unconfigured(db: Session) -> int:
    """After a contract is configured, move not_configured anchors back into the queue."""
    if not cs.is_configured():
        return 0
    rows = db.execute(select(BlockchainAnchor).where(BlockchainAnchor.status == "not_configured")).scalars().all()
    net = network()
    for r in rows:
        r.status = "queued"
        r.contract_address = contract_address()
        r.chain_id = net["chain_id"]
        r.network = net["key"]
    db.commit()
    if rows:
        _worker_wake.set()
    return len(rows)
