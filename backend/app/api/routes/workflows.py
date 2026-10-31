from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.serializers import workflow_detail, workflow_summary
from app.core.security import get_current_user, require_role
from app.database.session import get_db
from app.models import Document, User, Workflow
from app.orchestration.graph import GRAPH_TOPOLOGY
from app.schemas.api import StartWorkflowRequest
from app.services import workflow_service

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def _get(db: Session, wf_id: str, user: User) -> Workflow:
    wf = db.get(Workflow, wf_id)
    if not wf or wf.document.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")
    return wf


@router.post("/start", status_code=202)
def start(body: StartWorkflowRequest, db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    doc = db.get(Document, body.document_id)
    if not doc or doc.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    if doc.storage_key == "seeded-no-file":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Seeded history records cannot be reprocessed")
    try:
        wf = workflow_service.start_workflow(db, doc, user)
    except workflow_service.WorkflowConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return workflow_summary(wf)


@router.get("")
def list_workflows(status_filter: str | None = Query(None, alias="status"), include_seeded: bool = False,
                   limit: int = Query(30, le=200), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = select(Workflow).join(Document).where(Document.organization_id == user.organization_id)
    if status_filter:
        q = q.where(Workflow.status == status_filter)
    if not include_seeded:
        q = q.where(Workflow.is_seeded.is_(False))
    return [workflow_summary(w) for w in db.execute(q.order_by(Workflow.created_at.desc()).limit(limit)).scalars()]


@router.get("/topology")
def topology():
    return GRAPH_TOPOLOGY


@router.get("/{wf_id}")
def get_workflow(wf_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return workflow_detail(_get(db, wf_id, user))


@router.get("/{wf_id}/status")
def get_status(wf_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    wf = _get(db, wf_id, user)
    return {"id": wf.id, "status": wf.status, "current_stage": wf.current_stage,
            "agents": {e.agent: e.status for e in wf.executions}, "error": wf.error}


@router.post("/{wf_id}/retry", status_code=202)
def retry(wf_id: str, db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    wf = _get(db, wf_id, user)
    try:
        new = workflow_service.retry_workflow(db, wf, user)
    except workflow_service.WorkflowConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return workflow_summary(new)
