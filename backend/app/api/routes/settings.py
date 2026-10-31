from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.blockchain.network_config import contract_address
from app.blockchain.mst_client import relayer_address
from app.core.config import get_settings
from app.core.security import get_current_user, require_role
from app.database.session import engine, get_db
from app.models import User, ValidationRule
from app.schemas.api import RuleUpdate
from app.services import audit_service

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/system/status")
def system_status():
    """Public, secret-free integration status used for the DEMO MODE banner."""
    s = get_settings()
    return {
        "app": s.app_name,
        "demo_mode": s.demo_mode,
        "llm": {"provider": s.llm_provider, "model": s.anthropic_model if not s.demo_mode else None,
                "configured": not s.demo_mode},
        "database": engine.dialect.name,
        "storage": "local",
        "execution": "simulated",
        "blockchain": {"network": s.network["name"], "chain_id": s.network["chain_id"],
                       "contract_address": contract_address(), "relayer_address": relayer_address()},
        "low_confidence_threshold": s.low_confidence_threshold,
        "max_upload_mb": s.max_upload_mb,
    }


@router.get("/settings/rules")
def rules(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(select(ValidationRule).where(ValidationRule.organization_id == user.organization_id)
                      .order_by(ValidationRule.document_type, ValidationRule.code)).scalars().all()
    return [{"id": r.id, "code": r.code, "document_type": r.document_type, "rule_type": r.rule_type, "field": r.field,
             "params": r.params, "severity": r.severity, "description": r.description, "enabled": r.enabled} for r in rows]


@router.patch("/settings/rules/{rule_id}")
def update_rule(rule_id: str, body: RuleUpdate, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    r = db.get(ValidationRule, rule_id)
    if not r or r.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    changes = body.model_dump(exclude_none=True)
    for k, v in changes.items():
        setattr(r, k, v)
    db.commit()
    audit_service.append_event(db, event_type="RULE_UPDATED", description=f"Validation rule {r.code} updated: {changes}.",
                               actor=user.full_name, user_id=user.id, payload={"rule": r.code, "changes": changes})
    return {"id": r.id, "code": r.code, "enabled": r.enabled, "severity": r.severity, "params": r.params}
