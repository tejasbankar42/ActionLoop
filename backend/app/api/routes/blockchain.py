import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.blockchain import contract_service as cs
from app.blockchain import transaction_service as ts
from app.blockchain.network_config import contract_address, load_abi, network
from app.blockchain.verification_service import anchor_dict, network_status
from app.core.security import get_current_user, require_role
from app.database.session import get_db
from app.models import AuditEvent, BlockchainAnchor, User
from app.schemas.api import SubmitterRequest, WalletSubmissionRequest

router = APIRouter(prefix="/api/blockchain", tags=["blockchain"])


@router.get("/config")
def config():
    """Public chain parameters the browser wallet needs (no secrets)."""
    net = network()
    return {"network": net, "contract_address": contract_address(), "abi": load_abi(), "configured": cs.is_configured()}


@router.get("/status")
def chain_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    out = network_status()
    chain = network()["chain_id"]
    counts = dict(db.execute(select(BlockchainAnchor.status, func.count()).where(BlockchainAnchor.chain_id == chain)
                             .group_by(BlockchainAnchor.status)).all())
    out["anchor_counts"] = counts
    return out


@router.get("/anchors")
def anchors(status_filter: str | None = Query(None, alias="status"), limit: int = Query(50, le=200),
            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = select(BlockchainAnchor).where(BlockchainAnchor.chain_id == network()["chain_id"])
    if status_filter:
        q = q.where(BlockchainAnchor.status == status_filter)
    rows = db.execute(q.order_by(BlockchainAnchor.created_at.desc()).limit(limit)).scalars().all()
    events = {e.id: e for e in db.execute(select(AuditEvent).where(AuditEvent.id.in_([r.audit_event_id for r in rows]))).scalars()}
    return [anchor_dict(r) | {"description": events[r.audit_event_id].description if r.audit_event_id in events else None}
            for r in rows]


@router.post("/events/{event_id}/anchor", status_code=202)
def queue_event(event_id: str, db: Session = Depends(get_db), user: User = Depends(require_role("reviewer"))):
    ev = db.get(AuditEvent, event_id)
    if not ev:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audit event not found")
    if (ev.payload or {}).get("seeded"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Seeded demo history is never anchored on-chain")
    return anchor_dict(ts.queue_existing_event(db, ev))


@router.post("/anchors/{anchor_id}/process")
def process(anchor_id: str, db: Session = Depends(get_db), user: User = Depends(require_role("reviewer"))):
    """Submit (or re-check) one anchor through the backend relayer. Safe to call repeatedly."""
    a = db.get(BlockchainAnchor, anchor_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anchor not found")
    if a.status == "failed":
        a.status, a.attempts = "queued", 0
        db.commit()
    return anchor_dict(ts.process_anchor(db, a))


@router.post("/anchors/{anchor_id}/wallet-submission")
def wallet_submission(anchor_id: str, body: WalletSubmissionRequest, db: Session = Depends(get_db),
                      user: User = Depends(require_role("reviewer"))):
    a = db.get(BlockchainAnchor, anchor_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anchor not found")
    if a.status == "confirmed":
        return anchor_dict(a)
    try:
        return anchor_dict(ts.record_wallet_submission(db, a, body.tx_hash))
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not verify transaction on MST: {exc}"[:300])


@router.get("/verify/{event_hash}")
def verify_hash(event_hash: str, user: User = Depends(get_current_user)):
    if not re.fullmatch(r"(0x)?[0-9a-fA-F]{64}", event_hash):
        raise HTTPException(422, "Expected a 32-byte hex hash")
    if not cs.is_configured():
        return {"configured": False, "anchored": False}
    try:
        rec = cs.get_record(event_hash)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"MST RPC error: {exc}"[:300])
    return {"configured": True, "anchored": rec is not None, "record": rec, "contract_address": contract_address()}


@router.get("/submitters/{address}")
def is_submitter(address: str, user: User = Depends(get_current_user)):
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", address):
        raise HTTPException(422, "Expected a 20-byte address")
    if not cs.is_configured():
        return {"address": address, "configured": False, "authorized": False}
    from web3 import Web3

    try:
        ok = cs.get_contract().functions.isSubmitter(Web3.to_checksum_address(address)).call()
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"MST RPC error: {exc}"[:300])
    return {"address": address, "configured": True, "authorized": bool(ok)}


@router.post("/submitters")
def set_submitter(body: SubmitterRequest, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    try:
        out = ts.set_submitter(body.address, body.authorized)
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"MST transaction failed: {exc}"[:300])
    from app.services import audit_service

    audit_service.append_event(db, event_type="SUBMITTER_UPDATED",
                               description=f"{'Authorized' if body.authorized else 'Revoked'} {out['address']} as audit submitter on MST.",
                               actor=user.full_name, user_id=user.id, payload={k: out[k] for k in ("address", "authorized", "tx_hash")})
    return out


@router.post("/requeue")
def requeue(db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    return {"requeued": ts.requeue_unconfigured(db)}
