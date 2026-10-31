"""Metrics computed from stored workflow data. Seeded history is included but reported separately
so the UI can label it as illustrative."""

import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.extractor import classify, demo_extract, read_text
from app.models import AgentExecution, Approval, Document, Workflow
from app.utils.sample_docs import SAMPLES_DIR

CLOSED = ("completed", "rejected", "needs_correction", "failed")


def _aware(dt):
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _workflows(db: Session, org_id: str, start: datetime | None = None, end: datetime | None = None):
    q = select(Workflow).join(Document).where(Document.organization_id == org_id)
    if start:
        q = q.where(Workflow.created_at >= start)
    if end:
        q = q.where(Workflow.created_at < end)
    return db.execute(q).scalars().all()


def _automated_ms(db: Session, ids: list[str]) -> dict[str, int]:
    rows = db.execute(select(AgentExecution.workflow_id, func.sum(AgentExecution.duration_ms)).where(
        AgentExecution.workflow_id.in_(ids), AgentExecution.agent.in_(["extractor", "validator", "action_planner", "executor"])
    ).group_by(AgentExecution.workflow_id)).all()
    return {k: int(v or 0) for k, v in rows}


def _rates(wfs: list[Workflow]) -> dict:
    closed = [w for w in wfs if w.status in CLOSED]
    n = len(closed) or 1
    return {
        "completion_rate": round(sum(w.status == "completed" for w in closed) / n, 3),
        "validation_failure_rate": round(sum(w.validation_status == "failed" for w in wfs) / (len(wfs) or 1), 3),
        "human_intervention_rate": round(sum(w.requires_approval for w in wfs) / (len(wfs) or 1), 3),
        "failure_rate": round(sum(w.status == "failed" for w in closed) / n, 3),
    }


def overview(db: Session, org_id: str) -> dict:
    wfs = _workflows(db, org_id)
    live = [w for w in wfs if not w.is_seeded]
    auto = _automated_ms(db, [w.id for w in wfs])
    autos = [auto[w.id] for w in wfs if auto.get(w.id)]
    e2e = [w.duration_ms for w in wfs if w.duration_ms]
    closed = [w for w in wfs if w.status in CLOSED]
    pending = db.scalar(select(func.count(Approval.id)).join(Workflow).join(Document).where(
        Approval.status == "pending", Document.organization_id == org_id)) or 0
    today = datetime.now(timezone.utc).date()
    days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    buckets = {d: {"date": d.isoformat(), "processed": 0, "completed": 0, "exceptions": 0, "live": 0} for d in days}
    for w in wfs:
        d = _aware(w.created_at).date()
        if d in buckets:
            b = buckets[d]
            b["processed"] += 1
            b["live"] += 0 if w.is_seeded else 1
            b["completed"] += w.status == "completed"
            b["exceptions"] += w.status in ("failed", "needs_correction", "rejected")
    return {
        "totals": {
            "documents_processed": len(wfs),
            "live_workflows": len(live),
            "seeded_workflows": len(wfs) - len(live),
            "successful_workflows": sum(w.status == "completed" for w in wfs),
            "pending_approvals": pending,
            "validation_failures": sum(w.validation_status == "failed" for w in wfs),
            "avg_automated_ms": int(sum(autos) / len(autos)) if autos else None,
            "avg_end_to_end_ms": int(sum(e2e) / len(e2e)) if e2e else None,
            "success_rate": round(sum(w.status == "completed" for w in closed) / len(closed), 3) if closed else None,
            "in_progress": sum(w.status in ("queued", "running") for w in wfs),
        },
        "activity": list(buckets.values()),
        "by_type": _by_type(wfs),
    }


def _by_type(wfs):
    out = defaultdict(int)
    for w in wfs:
        out[w.document_type or "unknown"] += 1
    return dict(out)


def report(db: Session, org_id: str, start: date, end: date) -> dict:
    s = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    e = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    wfs = _workflows(db, org_id, s, e)
    auto = _automated_ms(db, [w.id for w in wfs])
    series = {}
    d = start
    while d <= end:
        series[d] = {"date": d.isoformat(), "documents": 0, "completed": 0, "durations": [], "auto": []}
        d += timedelta(days=1)
    for w in wfs:
        b = series.get(_aware(w.created_at).date())
        if not b:
            continue
        b["documents"] += 1
        b["completed"] += w.status == "completed"
        if w.duration_ms:
            b["durations"].append(w.duration_ms)
        if auto.get(w.id):
            b["auto"].append(auto[w.id])
    daily = [{"date": b["date"], "documents": b["documents"], "completed": b["completed"],
              "avg_end_to_end_s": round(sum(b["durations"]) / len(b["durations"]) / 1000, 1) if b["durations"] else None,
              "avg_automated_s": round(sum(b["auto"]) / len(b["auto"]) / 1000, 2) if b["auto"] else None}
             for b in series.values()]
    approvals = db.execute(select(Approval).where(Approval.workflow_id.in_([w.id for w in wfs]))).scalars().all()
    decided = [a for a in approvals if a.status != "pending"]
    agents = []
    for agent in ("extractor", "validator", "action_planner", "executor"):
        rows = db.execute(select(AgentExecution).where(AgentExecution.workflow_id.in_([w.id for w in wfs]),
                                                       AgentExecution.agent == agent)).scalars().all()
        done = [r for r in rows if r.status == "completed"]
        agents.append({"agent": agent, "runs": len(rows), "completed": len(done),
                       "failed": sum(r.status == "failed" for r in rows),
                       "avg_ms": int(sum(r.duration_ms or 0 for r in done) / len(done)) if done else None})
    return {
        "range": {"from": start.isoformat(), "to": end.isoformat()},
        "workflows": len(wfs), "seeded_workflows": sum(w.is_seeded for w in wfs),
        "daily": daily,
        "rates": _rates(wfs) | {
            "approval_rate": round(sum(a.status == "approved" for a in decided) / len(decided), 3) if decided else None},
        "by_type": _by_type(wfs),
        "agents": agents,
        "extraction_accuracy": extraction_accuracy(),
    }


@lru_cache
def extraction_accuracy() -> dict:
    """Field-level accuracy of the DEMO parser on the labelled sample set (real measurement)."""
    gt_path = SAMPLES_DIR / "ground_truth.json"
    if not gt_path.exists():
        return {"available": False}
    manifest = json.loads(gt_path.read_text())
    total = correct = 0
    per_doc = []
    for m in manifest:
        if not m["truth"]:
            continue
        text = read_text(SAMPLES_DIR / m["file"], "application/pdf") or ""
        dtype, _, _ = classify(text)
        fields = {f["name"]: f["value"] for f in demo_extract(text, dtype)} if dtype else {}
        ok = 0
        for k, v in m["truth"].items():
            total += 1
            got = fields.get(k)
            if (v is None and got is None) or (v is not None and got is not None and str(got).strip() == str(v).strip()):
                ok += 1
        correct += ok
        per_doc.append({"file": m["file"], "fields": len(m["truth"]), "correct": ok, "document_type": dtype})
    return {"available": True, "engine": "demo:pdf-text-parser", "samples": len(per_doc), "fields": total,
            "correct": correct, "accuracy": round(correct / total, 3) if total else None, "per_document": per_doc,
            "note": "Measured on the bundled labelled demo samples. Unreadable values count as correct only when left empty."}
