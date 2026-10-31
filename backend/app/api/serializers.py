from datetime import datetime, timezone

from app.agents.document_types import type_label
from app.models import AgentExecution, Approval, AuditEvent, Document, Workflow


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def document_out(d: Document, with_workflows: bool = False) -> dict:
    latest = d.workflows[-1] if d.workflows else None
    out = {
        "id": d.id, "filename": d.filename, "content_type": d.content_type, "size_bytes": d.size_bytes,
        "sha256": d.sha256, "detected_type": d.detected_type, "type_label": type_label(d.detected_type) if d.detected_type else None,
        "status": d.status, "is_sample": d.is_sample, "is_seeded": d.is_seeded, "created_at": iso(d.created_at),
        "has_file": d.storage_key != "seeded-no-file",
        "latest_workflow": {"id": latest.id, "status": latest.status, "current_stage": latest.current_stage} if latest else None,
    }
    if with_workflows:
        out["workflows"] = [workflow_summary(w) for w in d.workflows]
    return out


def workflow_summary(w: Workflow) -> dict:
    return {
        "id": w.id, "document_id": w.document_id, "filename": w.document.filename if w.document else None,
        "status": w.status, "current_stage": w.current_stage, "document_type": w.document_type,
        "type_label": type_label(w.document_type) if w.document_type else None,
        "validation_status": w.validation_status, "requires_approval": w.requires_approval,
        "approval_reasons": w.approval_reasons, "priority": w.priority, "error": w.error, "is_seeded": w.is_seeded,
        "created_at": iso(w.created_at), "completed_at": iso(w.completed_at), "duration_ms": w.duration_ms,
    }


def execution_out(e: AgentExecution) -> dict:
    return {"id": e.id, "agent": e.agent, "status": e.status, "attempt": e.attempt, "input": e.input_summary,
            "output": e.output, "explanation": e.explanation, "error": e.error, "engine": e.engine,
            "started_at": iso(e.started_at), "finished_at": iso(e.finished_at), "duration_ms": e.duration_ms}


def approval_out(a: Approval) -> dict:
    return {"id": a.id, "workflow_id": a.workflow_id, "status": a.status, "reasons": a.reasons, "priority": a.priority,
            "reviewer_name": a.reviewer_name, "comment": a.comment, "corrections": a.corrections,
            "created_at": iso(a.created_at), "decided_at": iso(a.decided_at)}


def workflow_detail(w: Workflow) -> dict:
    out = workflow_summary(w)
    out.update({
        "document": document_out(w.document),
        "executions": [execution_out(e) for e in w.executions],
        "fields": [{"id": f.id, "name": f.name, "label": f.label, "value": f.value, "confidence": f.confidence,
                    "status": f.status, "note": f.note} for f in w.fields],
        "validations": [{"id": v.id, "rule_code": v.rule_code, "rule_type": v.rule_type, "field": v.field,
                         "status": v.status, "message": v.message, "details": v.details} for v in w.validations],
        "actions": [{"id": a.id, "step": a.step, "action": a.action, "title": a.title, "department": a.department,
                     "priority": a.priority, "impact": a.impact, "requires_approval": a.requires_approval,
                     "reasoning": a.reasoning, "status": a.status} for a in sorted(w.action_plans, key=lambda a: a.step)],
        "approvals": [approval_out(a) for a in w.approvals],
        "execution_result": w.execution_result,
    })
    return out


def audit_out(e: AuditEvent, anchor: dict | None = None) -> dict:
    return {"id": e.id, "sequence": e.sequence, "workflow_id": e.workflow_id, "timestamp": iso(e.timestamp),
            "user_id": e.user_id, "actor": e.actor, "agent": e.agent, "event_type": e.event_type,
            "description": e.description, "payload": e.payload, "previous_hash": e.previous_hash, "hash": e.hash,
            "seeded": bool((e.payload or {}).get("seeded")), "anchor": anchor}
