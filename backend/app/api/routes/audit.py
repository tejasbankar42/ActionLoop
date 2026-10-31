import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.serializers import audit_out
from app.blockchain.network_config import network
from app.blockchain.verification_service import anchor_dict, verify_event
from app.core.security import get_current_user
from app.database.session import get_db
from app.models import AuditEvent, BlockchainAnchor, User
from app.schemas.api import VerifyRequest
from app.services import audit_service

router = APIRouter(prefix="/api/audit", tags=["audit"])


def _filtered(q, search, workflow_id, event_type, agent, include_seeded):
    if workflow_id:
        q = q.where(AuditEvent.workflow_id == workflow_id)
    if event_type:
        q = q.where(AuditEvent.event_type == event_type)
    if agent:
        q = q.where(AuditEvent.agent == agent)
    if search:
        like = f"%{search}%"
        q = q.where(or_(AuditEvent.description.ilike(like), AuditEvent.actor.ilike(like), AuditEvent.hash.ilike(like),
                        AuditEvent.workflow_id.ilike(like), AuditEvent.id.ilike(like)))
    if not include_seeded:
        q = q.where(~AuditEvent.description.startswith("[seeded]"))
    return q


@router.get("/events")
def events(search: str | None = None, workflow_id: str | None = None, event_type: str | None = None,
           agent: str | None = None, include_seeded: bool = False, limit: int = Query(100, le=500), offset: int = 0,
           db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = _filtered(select(AuditEvent), search, workflow_id, event_type, agent, include_seeded)
    rows = db.execute(q.order_by(AuditEvent.sequence.desc()).offset(offset).limit(limit)).scalars().all()
    chain = network()["chain_id"]
    anchors = {a.audit_event_id: anchor_dict(a) for a in db.execute(select(BlockchainAnchor).where(
        BlockchainAnchor.audit_event_id.in_([r.id for r in rows]), BlockchainAnchor.chain_id == chain)).scalars()}
    return {"events": [audit_out(r, anchors.get(r.id)) for r in rows], "total_in_chain": audit_service.count_events(db),
            "event_types": sorted({t for (t,) in db.execute(select(AuditEvent.event_type).distinct())})}


@router.post("/verify")
def verify(body: VerifyRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Recompute the full SHA-256 chain from the genesis hash. `simulate_tamper_event_id` alters an
    in-memory copy only, to demonstrate detection without touching stored records."""
    rows = audit_service.all_events(db)
    tamper = None
    if body.simulate_tamper_event_id:
        tamper = {"event_id": body.simulate_tamper_event_id, "field": "description",
                  "value": "Approved payment of INR 9,99,999 (altered)"}
    result = audit_service.verify_chain(rows, tamper=tamper)
    if body.workflow_id:
        result["workflow_events"] = [audit_out(r) for r in rows if r.workflow_id == body.workflow_id]
    if not tamper:
        audit_service.append_event(db, event_type="AUDIT_VERIFIED",
                                   description=f"Hash chain verified: {result['checked']} events, "
                                               f"{'VALID' if result['valid'] else str(len(result['broken'])) + ' broken link(s)'}.",
                                   actor=user.full_name, user_id=user.id,
                                   payload={"valid": result["valid"], "checked": result["checked"], "head": result["head_hash"]})
    return result


@router.get("/events/{event_id}/verify")
def verify_one(event_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ev = db.get(AuditEvent, event_id)
    if not ev:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audit event not found")
    out = verify_event(db, ev)
    out["event"] = audit_out(ev)
    return out


@router.get("/export.csv")
def export_csv(search: str | None = None, workflow_id: str | None = None, event_type: str | None = None,
               include_seeded: bool = True, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = _filtered(select(AuditEvent), search, workflow_id, event_type, None, include_seeded)
    rows = db.execute(q.order_by(AuditEvent.sequence)).scalars().all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["sequence", "event_id", "workflow_id", "timestamp", "actor", "agent", "event_type", "description",
                "previous_hash", "hash"])
    for r in rows:
        w.writerow([r.sequence, r.id, r.workflow_id or "", audit_out(r)["timestamp"], r.actor, r.agent or "",
                    r.event_type, r.description, r.previous_hash, r.hash])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="actionloop-audit.csv"'})
