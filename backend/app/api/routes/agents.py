from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.serializers import execution_out
from app.core.config import get_settings
from app.core.security import get_current_user
from app.database.session import get_db
from app.models import AgentExecution, User, Workflow

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/executions/{workflow_id}")
def executions(workflow_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    wf = db.get(Workflow, workflow_id)
    if not wf or wf.document.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")
    return [execution_out(e) for e in wf.executions]


@router.get("/status")
def agent_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = get_settings()
    out = []
    for agent in ("extractor", "validator", "action_planner", "human_approval", "executor"):
        rows = db.execute(select(AgentExecution.status, func.count()).where(AgentExecution.agent == agent)
                          .group_by(AgentExecution.status)).all()
        last = db.execute(select(AgentExecution).where(AgentExecution.agent == agent)
                          .order_by(AgentExecution.started_at.desc()).limit(1)).scalar_one_or_none()
        avg = db.scalar(select(func.avg(AgentExecution.duration_ms)).where(AgentExecution.agent == agent,
                                                                          AgentExecution.status == "completed"))
        out.append({
            "agent": agent, "counts": {k: v for k, v in rows}, "avg_duration_ms": int(avg) if avg else None,
            "last": execution_out(last) if last else None,
            "engine": ("claude:" + s.anthropic_model if not s.demo_mode else "demo:pdf-text-parser") if agent == "extractor"
            else "simulated-executor" if agent == "executor" else "human" if agent == "human_approval" else "deterministic-rules",
        })
    return out
