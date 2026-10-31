"""Agent 2 - Validator. Fully deterministic: configurable rules from the `validation_rules` table
plus database lookups. LLM output is never treated as authoritative here."""

import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ExtractedField, ValidationRule, Workflow


def _val(fields: dict, name: str):
    f = fields.get(name)
    return f["value"] if f and f["status"] != "missing" else None


def _as_date(v) -> date | None:
    try:
        return date.fromisoformat(str(v))
    except (TypeError, ValueError):
        return None


def _as_float(v) -> float | None:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _result(rule: ValidationRule, status: str, message: str, **details) -> dict:
    return {"rule_code": rule.code, "rule_type": rule.rule_type, "field": rule.field,
            "status": status, "message": message, "details": details}


def _check(rule: ValidationRule, fields: dict, db: Session, workflow_id: str, doc_type: str) -> dict | None:
    p = rule.params or {}
    sev = rule.severity
    label = fields.get(rule.field, {}).get("label", rule.field) if rule.field else ""
    v = _val(fields, rule.field) if rule.field else None

    if rule.rule_type == "required":
        f = fields.get(rule.field)
        if v in (None, ""):
            reason = "unreadable" if f and f["status"] == "uncertain" else "missing"
            return _result(rule, sev, f"{label} is {reason}. {rule.description}".strip(), reason=reason)
        return _result(rule, "passed", f"{label} is present.")

    if v in (None, "") and rule.rule_type not in ("duplicate", "confidence"):
        return None  # nothing to check; `required` rules report absence

    if rule.rule_type == "regex":
        ok = re.fullmatch(p["pattern"], str(v)) is not None
        return _result(rule, "passed" if ok else sev,
                       f"{label} format is valid." if ok else f"{label} '{v}' does not match the expected format ({p.get('hint', p['pattern'])}).")

    if rule.rule_type == "range":
        num = _as_float(v)
        if num is None:
            return _result(rule, sev, f"{label} '{v}' is not a number.")
        lo, hi = p.get("min"), p.get("max")
        if (lo is not None and num < lo) or (hi is not None and num > hi):
            return _result(rule, sev, f"{label} {num:g} is outside the allowed range {lo}–{hi}. {rule.description}".strip(), value=num)
        return _result(rule, "passed", f"{label} {num:g} is within {lo}–{hi}.", value=num)

    if rule.rule_type == "not_future":
        d = _as_date(v)
        if d is None:
            return _result(rule, "warning", f"{label} '{v}' is not a valid date.")
        if d > date.today():
            return _result(rule, sev, f"{label} {d.isoformat()} is in the future.")
        return _result(rule, "passed", f"{label} {d.isoformat()} is not in the future.")

    if rule.rule_type == "date_order":
        a, b = _as_date(_val(fields, p["after"])), _as_date(v)
        if a and b and b < a:
            return _result(rule, sev, f"{label} {b} is before {fields[p['after']]['label']} {a}.")
        return _result(rule, "passed", f"{label} is on or after {fields.get(p['after'], {}).get('label', p['after'])}.")

    if rule.rule_type == "age":
        d = _as_date(v)
        if d is None:
            return _result(rule, "warning", f"{label} '{v}' is not a valid date.")
        today = date.today()
        age = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
        if not (p.get("min", 0) <= age <= p.get("max", 150)):
            return _result(rule, sev, f"Applicant age {age} is outside {p.get('min')}–{p.get('max')} years.", age=age)
        return _result(rule, "passed", f"Age {age} is within {p.get('min')}–{p.get('max')} years.", age=age)

    if rule.rule_type == "duplicate":
        keys = p.get("fields", [rule.field])
        values = {k: _val(fields, k) for k in keys}
        if any(x in (None, "") for x in values.values()):
            return _result(rule, "warning", f"Duplicate check skipped: {', '.join(k for k, x in values.items() if not x)} unavailable.")
        matches = None
        for k, x in values.items():
            ids = set(db.execute(select(ExtractedField.workflow_id).where(
                ExtractedField.name == k, ExtractedField.value == x, ExtractedField.workflow_id != workflow_id
            )).scalars())
            matches = ids if matches is None else matches & ids
        prior = []
        if matches:
            prior = db.execute(select(Workflow).where(
                Workflow.id.in_(matches), Workflow.document_type == doc_type,
                Workflow.status.in_(["completed", "awaiting_approval", "running", "needs_correction"]),
            )).scalars().all()
        if prior:
            ref = prior[0]
            return _result(rule, sev,
                           f"Duplicate: a {doc_type.replace('_', ' ')} with the same {', '.join(keys)} was already processed "
                           f"(workflow {ref.id[:8]}, {ref.created_at:%d %b %Y}, status {ref.status}).",
                           duplicate_of=ref.id, matched_on=values)
        return _result(rule, "passed", f"No existing record with the same {', '.join(keys)}.")

    if rule.rule_type == "confidence":
        threshold = p.get("threshold", 0.75)
        low = [f["label"] for f in fields.values() if f["status"] == "uncertain" or (f["value"] and f["confidence"] < threshold)]
        if low:
            return _result(rule, sev, f"Low-confidence extraction needs human verification: {', '.join(low)}.", fields=low)
        return _result(rule, "passed", f"All extracted fields are at or above {int(threshold * 100)}% confidence.")
    return None


def run_validator(db: Session, workflow_id: str, organization_id: str, doc_type: str | None, fields: list[dict]) -> dict:
    by_name = {f["name"]: f for f in fields}
    results: list[dict] = []
    if doc_type is None:
        results.append({"rule_code": "DOC_TYPE_KNOWN", "rule_type": "classification", "field": None, "status": "failed",
                        "message": "Document type could not be identified, so business rules cannot be applied.", "details": {}})
    else:
        rules = db.execute(select(ValidationRule).where(
            ValidationRule.organization_id == organization_id,
            ValidationRule.enabled.is_(True),
            ValidationRule.document_type.in_([doc_type, "*"]),
        ).order_by(ValidationRule.code)).scalars().all()
        for rule in rules:
            r = _check(rule, by_name, db, workflow_id, doc_type)
            if r:
                results.append(r)
    statuses = {r["status"] for r in results}
    overall = "failed" if "failed" in statuses else "warning" if "warning" in statuses else "passed"
    counts = {s: sum(1 for r in results if r["status"] == s) for s in ("passed", "warning", "failed")}
    duplicate = next((r for r in results if r["rule_type"] == "duplicate" and r["status"] == "failed"), None)
    return {"status": overall, "results": results, "counts": counts, "duplicate": duplicate}
