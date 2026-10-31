from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.serializers import approval_out, workflow_detail
from app.core.security import get_current_user, require_role
from app.database.session import get_db
from app.models import Approval, Document, User, Workflow
from app.schemas.api import DecisionRequest
from app.services import workflow_service

router = APIRouter(prefix="/api/approvals", tags=["approvals"])
PRIORITY_ORDER = {"urgent": 0, "high": 1, "normal": 2, "low": 3}


@router.get("/pending")
def pending(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(select(Approval).join(Workflow).join(Document).where(
        Approval.status == "pending", Document.organization_id == user.organization_id)).scalars().all()
    rows.sort(key=lambda a: (PRIORITY_ORDER.get(a.priority, 9), a.created_at))
    out = []
    for a in rows:
        item = approval_out(a)
        item["workflow"] = workflow_detail(db.get(Workflow, a.workflow_id))
        out.append(item)
    return out


@router.get("/history")
def history(limit: int = Query(30, le=200), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(select(Approval).join(Workflow).join(Document).where(
        Approval.status != "pending", Document.organization_id == user.organization_id, Workflow.is_seeded.is_(False))
        .order_by(Approval.decided_at.desc()).limit(limit)).scalars().all()
    return [approval_out(a) | {"filename": db.get(Workflow, a.workflow_id).document.filename} for a in rows]


@router.post("/{approval_id}/decision")
def decide(approval_id: str, body: DecisionRequest, db: Session = Depends(get_db),
           user: User = Depends(require_role("reviewer"))):
    approval = db.get(Approval, approval_id)
    if not approval or db.get(Workflow, approval.workflow_id).document.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Approval not found")
    if body.decision != "approve" and not body.comment:
        raise HTTPException(422, "A comment is required when rejecting or requesting correction")
    try:
        wf = workflow_service.decide(db, approval, user, body.decision, body.comment, body.corrections)
    except workflow_service.WorkflowConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return {"approval": approval_out(approval), "workflow_id": wf.id, "status": "resuming"}
