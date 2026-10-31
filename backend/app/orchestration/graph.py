"""LangGraph multi-agent orchestration.

Processing graph
  START -> extract -> (quality gate) -> validate -> plan -> (approval gate) -> execute -> finalize -> END
                         | failed                                  | needs human
                         v                                         v
                       fail -> END                         await_approval -> END   (checkpoint persisted)

Resume graph (after a reviewer decides)
  START -> apply_decision -> (approve) -> execute -> finalize -> END
                          -> (reject / request_correction) -> close -> END

The approval pause is a persistent checkpoint: the full graph state is stored in
`workflows.checkpoint`, so a decision can resume the run after a server restart.
"""

import time
from datetime import datetime, timezone

from langgraph.graph import END, START, StateGraph
from sqlalchemy import delete, select

from app.agents.action_planner import run_planner
from app.agents.extractor import ExtractionError, run_extractor
from app.agents.validator import run_validator
from app.core.config import get_settings
from app.database.session import SessionLocal
from app.models import (
    ActionPlan,
    AgentExecution,
    Approval,
    Document,
    ExtractedField,
    ValidationResult,
    Workflow,
)
from app.orchestration.state import WorkflowState
from app.services import audit_service
from app.services.storage import get_storage


def _now():
    return datetime.now(timezone.utc)


def _pace():
    ms = get_settings().demo_step_delay_ms
    if get_settings().demo_mode and ms > 0:
        time.sleep(ms / 1000)


class _AgentRun:
    """Records an AgentExecution row around one node."""

    def __init__(self, db, workflow_id: str, agent: str, input_summary: dict):
        self.db = db
        prev = db.execute(select(AgentExecution).where(
            AgentExecution.workflow_id == workflow_id, AgentExecution.agent == agent)).scalars().all()
        self.row = AgentExecution(workflow_id=workflow_id, agent=agent, status="running",
                                  attempt=len(prev) + 1, input_summary=input_summary)
        db.add(self.row)
        wf = db.get(Workflow, workflow_id)
        wf.current_stage = agent
        wf.status = "running"
        db.commit()
        self.t0 = time.perf_counter()

    def done(self, output: dict, explanation: str, engine: str = "deterministic", status: str = "completed"):
        r = self.row
        r.status, r.output, r.explanation, r.engine = status, output, explanation, engine
        r.finished_at = _now()
        r.duration_ms = int((time.perf_counter() - self.t0) * 1000)
        self.db.commit()

    def fail(self, error: str):
        r = self.row
        r.status, r.error = "failed", error
        r.finished_at = _now()
        r.duration_ms = int((time.perf_counter() - self.t0) * 1000)
        self.db.commit()


# ----------------------------------------------------------------------------- nodes

def extract_node(state: WorkflowState) -> WorkflowState:
    _pace()
    with SessionLocal() as db:
        doc = db.get(Document, state["document_id"])
        run = _AgentRun(db, state["workflow_id"], "extractor",
                        {"filename": doc.filename, "content_type": doc.content_type, "size_bytes": doc.size_bytes})
        try:
            out = run_extractor(get_storage().path(doc.storage_key), doc.content_type)
        except ExtractionError as exc:
            run.fail(str(exc))
            audit_service.append_event(db, event_type="EXTRACTION_FAILED", description=f"Extraction failed: {exc}",
                                       actor="Extractor Agent", agent="extractor", workflow_id=state["workflow_id"])
            return {"error": str(exc)}
        wf = db.get(Workflow, state["workflow_id"])
        db.execute(delete(ExtractedField).where(ExtractedField.workflow_id == wf.id))
        for f in out["fields"]:
            db.add(ExtractedField(workflow_id=wf.id, name=f["name"], label=f["label"], value=f["value"],
                                  confidence=f["confidence"], status=f["status"], note=f["note"]))
        wf.document_type = out["document_type"]
        doc.detected_type = out["document_type"]
        doc.status = "processing"
        ok = sum(1 for f in out["fields"] if f["status"] == "ok")
        explanation = (f"Classified as {out['document_type'] or 'unknown'} "
                       f"({int(out['type_confidence'] * 100)}% confidence). Extracted {ok}/{len(out['fields'])} fields cleanly"
                       + (f"; {len(out['warnings'])} issue(s) flagged." if out["warnings"] else "."))
        run.done(out, explanation, engine=out["engine"])
        audit_service.append_event(db, event_type="EXTRACTION_COMPLETED", description=explanation,
                                   actor="Extractor Agent", agent="extractor", workflow_id=wf.id,
                                   payload={"document_type": out["document_type"], "fields": len(out["fields"]),
                                            "warnings": len(out["warnings"]), "engine": out["engine"]})
    return {"extraction": out}


def route_after_extract(state: WorkflowState) -> str:
    return "fail" if state.get("error") else "validate"


def validate_node(state: WorkflowState) -> WorkflowState:
    _pace()
    ex = state["extraction"]
    with SessionLocal() as db:
        run = _AgentRun(db, state["workflow_id"], "validator",
                        {"document_type": ex["document_type"], "fields": len(ex["fields"])})
        out = run_validator(db, state["workflow_id"], state["organization_id"], ex["document_type"], ex["fields"])
        db.execute(delete(ValidationResult).where(ValidationResult.workflow_id == state["workflow_id"]))
        for r in out["results"]:
            db.add(ValidationResult(workflow_id=state["workflow_id"], rule_code=r["rule_code"], rule_type=r["rule_type"],
                                    field=r["field"], status=r["status"], message=r["message"], details=r["details"]))
        wf = db.get(Workflow, state["workflow_id"])
        wf.validation_status = out["status"]
        c = out["counts"]
        explanation = f"{c['passed']} passed, {c['warning']} warning(s), {c['failed']} failed → {out['status'].upper()}."
        run.done(out, explanation)
        audit_service.append_event(db, event_type="VALIDATION_COMPLETED", description=f"Validation {out['status']}: {explanation}",
                                   actor="Validator Agent", agent="validator", workflow_id=wf.id,
                                   payload={"status": out["status"], "counts": c})
        if out["duplicate"]:
            audit_service.append_event(db, event_type="VALIDATION_BLOCKED", description=out["duplicate"]["message"],
                                       actor="Validator Agent", agent="validator", workflow_id=wf.id,
                                       payload={"rule": out["duplicate"]["rule_code"]})
    return {"validation": out}


def plan_node(state: WorkflowState) -> WorkflowState:
    _pace()
    with SessionLocal() as db:
        run = _AgentRun(db, state["workflow_id"], "action_planner",
                        {"validation_status": state["validation"]["status"]})
        out = run_planner(state["extraction"]["document_type"], state["extraction"]["fields"], state["validation"])
        db.execute(delete(ActionPlan).where(ActionPlan.workflow_id == state["workflow_id"]))
        for a in out["actions"]:
            db.add(ActionPlan(workflow_id=state["workflow_id"], step=a["step"], action=a["action"], title=a["title"],
                              department=a["department"], priority=a["priority"], impact=a["impact"],
                              requires_approval=a["requires_approval"], reasoning=a["reasoning"],
                              status="blocked" if out["blocked"] and a["action"] not in ("block_duplicate", "request_correction", "human_verification", "manual_triage") else "planned"))
        wf = db.get(Workflow, state["workflow_id"])
        wf.requires_approval = out["requires_approval"]
        wf.approval_reasons = out["approval_reasons"]
        wf.priority = out["priority"]
        run.done(out, out["summary"])
        audit_service.append_event(db, event_type="PLAN_CREATED", description=out["summary"],
                                   actor="Action Planner", agent="action_planner", workflow_id=wf.id,
                                   payload={"actions": [a["action"] for a in out["actions"]],
                                            "requires_approval": out["requires_approval"]})
    return {"plan": out}


def route_after_plan(state: WorkflowState) -> str:
    return "await_approval" if state["plan"]["requires_approval"] else "execute"


def await_approval_node(state: WorkflowState) -> WorkflowState:
    _pace()
    with SessionLocal() as db:
        wf = db.get(Workflow, state["workflow_id"])
        checkpoint = dict(state)
        wf.checkpoint = checkpoint
        wf.status = "awaiting_approval"
        wf.current_stage = "human_approval"
        db.add(AgentExecution(workflow_id=wf.id, agent="human_approval", status="waiting",
                              input_summary={"reasons": state["plan"]["approval_reasons"]},
                              explanation="Waiting for an authorized reviewer."))
        db.add(Approval(workflow_id=wf.id, status="pending", reasons=state["plan"]["approval_reasons"],
                        priority=state["plan"]["priority"]))
        wf.document.status = "awaiting_approval"
        db.commit()
        audit_service.append_event(db, event_type="APPROVAL_REQUESTED",
                                   description="Human approval required: " + "; ".join(state["plan"]["approval_reasons"]),
                                   actor="Approval Gate", agent="human_approval", workflow_id=wf.id,
                                   payload={"reasons": state["plan"]["approval_reasons"]})
    return {"outcome": "awaiting_approval"}


def execute_node(state: WorkflowState) -> WorkflowState:
    """Runs approved actions. DEMO: every external effect is simulated and labelled as such."""
    _pace()
    results = []
    with SessionLocal() as db:
        run = _AgentRun(db, state["workflow_id"], "executor",
                        {"actions": [a["action"] for a in state["plan"]["actions"]]})
        rows = db.execute(select(ActionPlan).where(ActionPlan.workflow_id == state["workflow_id"])
                          .order_by(ActionPlan.step)).scalars().all()
        for row in rows:
            if row.status == "blocked":
                results.append({"action": row.action, "status": "skipped", "result": "Blocked by validation."})
                continue
            row.status = "executed"
            results.append({"action": row.action, "status": "executed",
                            "result": f"SIMULATED: '{row.title}' handed to {row.department}. No external system was called."})
        db.commit()
        run.done({"results": results}, f"{sum(r['status'] == 'executed' for r in results)} action(s) executed in simulation mode.",
                 engine="simulated-executor")
        audit_service.append_event(db, event_type="ACTIONS_EXECUTED",
                                   description=f"{sum(r['status'] == 'executed' for r in results)} planned action(s) executed (simulated).",
                                   actor="Execution Service", agent="executor", workflow_id=state["workflow_id"],
                                   payload={"results": [{"action": r["action"], "status": r["status"]} for r in results]})
    return {"execution": results}


def finalize_node(state: WorkflowState) -> WorkflowState:
    with SessionLocal() as db:
        wf = db.get(Workflow, state["workflow_id"])
        actions = {a["action"] for a in state["plan"]["actions"]}
        unresolved = {"request_correction", "human_verification", "manual_triage"}
        outcome = "needs_correction" if actions & unresolved else "completed"
        _close(db, wf, outcome, state)
    return {"outcome": outcome}


def fail_node(state: WorkflowState) -> WorkflowState:
    with SessionLocal() as db:
        wf = db.get(Workflow, state["workflow_id"])
        wf.error = state.get("error")
        _close(db, wf, "failed", state)
    return {"outcome": "failed"}


def _close(db, wf: Workflow, outcome: str, state: WorkflowState):
    wf.status = outcome
    wf.current_stage = "audit"
    wf.completed_at = _now()
    created = wf.created_at if wf.created_at.tzinfo else wf.created_at.replace(tzinfo=timezone.utc)
    wf.duration_ms = int((wf.completed_at - created).total_seconds() * 1000)
    wf.execution_result = {"outcome": outcome, "actions": state.get("execution", []),
                           "decision": {k: v for k, v in (state.get("decision") or {}).items() if k != "corrections"}}
    wf.checkpoint = {}
    wf.document.status = {"completed": "processed", "needs_correction": "needs_correction",
                          "rejected": "rejected", "failed": "failed"}[outcome]
    db.commit()
    event = {"completed": "WORKFLOW_COMPLETED", "needs_correction": "CORRECTION_REQUESTED",
             "rejected": "WORKFLOW_REJECTED", "failed": "WORKFLOW_FAILED"}[outcome]
    audit_service.append_event(db, event_type=event, description=f"Workflow closed with outcome '{outcome}'.",
                               actor="Audit Service", agent="audit", workflow_id=wf.id,
                               payload={"outcome": outcome, "duration_ms": wf.duration_ms,
                                        "document_sha256": wf.document.sha256})


# --------------------------------------------------------------------------- resume

def apply_decision_node(state: WorkflowState) -> WorkflowState:
    d = state["decision"]
    if d["decision"] != "approve" or not d.get("corrections"):
        return {}
    # Reviewer corrected fields: re-run the deterministic validator + planner on the corrected data.
    fields = state["extraction"]["fields"]
    for f in fields:
        if f["name"] in d["corrections"]:
            f.update(value=d["corrections"][f["name"]], status="corrected", confidence=1.0,
                     note=f"Corrected by {d['reviewer']}")
    with SessionLocal() as db:
        for f in fields:
            row = db.execute(select(ExtractedField).where(ExtractedField.workflow_id == state["workflow_id"],
                                                          ExtractedField.name == f["name"])).scalar_one_or_none()
            if row and f["status"] == "corrected":
                row.value, row.status, row.confidence, row.note = f["value"], "corrected", 1.0, f["note"]
                row.corrected_by = d.get("reviewer_id")
        db.commit()
    new_state = {**state, "extraction": {**state["extraction"], "fields": fields}}
    new_state.update(validate_node(new_state))
    new_state.update(plan_node(new_state))
    return {"extraction": new_state["extraction"], "validation": new_state["validation"], "plan": new_state["plan"]}


def route_decision(state: WorkflowState) -> str:
    return "execute" if state["decision"]["decision"] == "approve" else "close"


def close_node(state: WorkflowState) -> WorkflowState:
    with SessionLocal() as db:
        wf = db.get(Workflow, state["workflow_id"])
        outcome = "rejected" if state["decision"]["decision"] == "reject" else "needs_correction"
        for row in db.execute(select(ActionPlan).where(ActionPlan.workflow_id == wf.id)).scalars():
            row.status = "skipped"
        db.commit()
        _close(db, wf, outcome, state)
    return {"outcome": outcome}


def build_processing_graph():
    g = StateGraph(WorkflowState)
    g.add_node("extract", extract_node)
    g.add_node("validate", validate_node)
    g.add_node("plan", plan_node)
    g.add_node("await_approval", await_approval_node)
    g.add_node("execute", execute_node)
    g.add_node("finalize", finalize_node)
    g.add_node("fail", fail_node)
    g.add_edge(START, "extract")
    g.add_conditional_edges("extract", route_after_extract, {"fail": "fail", "validate": "validate"})
    g.add_edge("validate", "plan")
    g.add_conditional_edges("plan", route_after_plan, {"await_approval": "await_approval", "execute": "execute"})
    g.add_edge("await_approval", END)
    g.add_edge("execute", "finalize")
    g.add_edge("finalize", END)
    g.add_edge("fail", END)
    return g.compile()


def build_resume_graph():
    g = StateGraph(WorkflowState)
    g.add_node("apply_decision", apply_decision_node)
    g.add_node("execute", execute_node)
    g.add_node("finalize", finalize_node)
    g.add_node("close", close_node)
    g.add_edge(START, "apply_decision")
    g.add_conditional_edges("apply_decision", route_decision, {"execute": "execute", "close": "close"})
    g.add_edge("execute", "finalize")
    g.add_edge("finalize", END)
    g.add_edge("close", END)
    return g.compile()


processing_graph = build_processing_graph()
resume_graph = build_resume_graph()

GRAPH_TOPOLOGY = {
    "nodes": ["document_input", "extractor", "validator", "action_planner", "human_approval", "executor", "audit"],
    "edges": [
        ["document_input", "extractor"], ["extractor", "validator"], ["validator", "action_planner"],
        ["action_planner", "human_approval"], ["action_planner", "executor"], ["human_approval", "executor"],
        ["executor", "audit"], ["human_approval", "audit"], ["extractor", "audit"],
    ],
}
