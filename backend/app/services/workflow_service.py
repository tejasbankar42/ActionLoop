import logging
import threading

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models import AgentExecution, Approval, Document, User, Workflow, utcnow
from app.orchestration.graph import processing_graph, resume_graph
from app.services import audit_service

log = logging.getLogger("actionloop.workflow")
ACTIVE = ("queued", "running", "awaiting_approval")
_start_lock = threading.Lock()


class WorkflowConflict(Exception):
    pass


def start_workflow(db: Session, document: Document, user: User, background: bool = True) -> Workflow:
    # Lock + active-workflow check prevents duplicate submissions (double clicks, retries).
    with _start_lock:
        active = db.execute(select(Workflow).where(
            Workflow.document_id == document.id, Workflow.status.in_(ACTIVE))).scalar_one_or_none()
        if active:
            raise WorkflowConflict(f"Document already has an active workflow ({active.id})")
        wf = Workflow(document_id=document.id, started_by=user.id, status="queued", current_stage="uploaded")
        db.add(wf)
        document.status = "queued"
        db.commit()
        audit_service.append_event(db, event_type="WORKFLOW_STARTED",
                                   description=f"Workflow started for '{document.filename}'.",
                                   actor=user.full_name, user_id=user.id, workflow_id=wf.id,
                                   payload={"document_id": document.id, "document_sha256": document.sha256})
    state = {"workflow_id": wf.id, "document_id": document.id, "organization_id": user.organization_id,
             "user_id": user.id, "actor": user.full_name}
    if background:
        threading.Thread(target=_run_processing, args=(state,), daemon=True, name=f"wf-{wf.id[:8]}").start()
    else:
        _run_processing(state)
    return wf


def _run_processing(state: dict) -> None:
    try:
        processing_graph.invoke(state)
    except Exception as exc:  # unexpected crash: surface it instead of leaving a zombie "running" row
        log.exception("workflow %s crashed", state["workflow_id"])
        with SessionLocal() as db:
            wf = db.get(Workflow, state["workflow_id"])
            wf.status, wf.error = "failed", f"Unexpected error: {exc}"
            db.commit()
            audit_service.append_event(db, event_type="WORKFLOW_FAILED", description=f"Unexpected error: {exc}",
                                       actor="Orchestrator", workflow_id=wf.id)


def retry_workflow(db: Session, wf: Workflow, user: User) -> Workflow:
    if wf.status != "failed":
        raise WorkflowConflict("Only failed workflows can be retried")
    return start_workflow(db, wf.document, user)


def decide(db: Session, approval: Approval, reviewer: User, decision: str, comment: str | None,
           corrections: dict | None, background: bool = True) -> Workflow:
    if approval.status != "pending":
        raise WorkflowConflict("This approval has already been decided")
    wf = db.get(Workflow, approval.workflow_id)
    if wf.status != "awaiting_approval" or not wf.checkpoint:
        raise WorkflowConflict("Workflow is not waiting for approval")
    approval.status = {"approve": "approved", "reject": "rejected", "request_correction": "correction_requested"}[decision]
    approval.reviewer_id = reviewer.id
    approval.reviewer_name = reviewer.full_name
    approval.comment = comment
    approval.corrections = corrections or {}
    approval.decided_at = utcnow()
    waiting = db.execute(select(AgentExecution).where(AgentExecution.workflow_id == wf.id,
                                                      AgentExecution.agent == "human_approval",
                                                      AgentExecution.status == "waiting")).scalars().first()
    if waiting:
        waiting.status = "completed"
        waiting.finished_at = utcnow()
        waiting.output = {"decision": decision, "reviewer": reviewer.full_name, "comment": comment}
        waiting.explanation = f"{reviewer.full_name} chose '{decision}'."
    wf.status = "running"
    wf.current_stage = "human_approval"
    db.commit()
    audit_service.append_event(
        db, event_type="APPROVAL_DECISION",
        description=f"{reviewer.full_name} ({reviewer.role}) decided '{decision}'" + (f": {comment}" if comment else "."),
        actor=reviewer.full_name, user_id=reviewer.id, agent="human_approval", workflow_id=wf.id,
        payload={"decision": decision, "approval_id": approval.id, "corrected_fields": sorted((corrections or {}).keys())},
    )
    state = dict(wf.checkpoint)
    state["decision"] = {"decision": decision, "reviewer": reviewer.full_name, "reviewer_id": reviewer.id,
                         "comment": comment, "corrections": corrections or {}}
    if background:
        threading.Thread(target=_run_resume, args=(state,), daemon=True).start()
    else:
        _run_resume(state)
    return wf


def _run_resume(state: dict) -> None:
    try:
        resume_graph.invoke(state)
    except Exception as exc:
        log.exception("resume %s crashed", state["workflow_id"])
        with SessionLocal() as db:
            wf = db.get(Workflow, state["workflow_id"])
            wf.status, wf.error = "failed", f"Unexpected error: {exc}"
            db.commit()
