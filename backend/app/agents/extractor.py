"""Agent 1 - Extractor.

LIVE mode  : the document (PDF or image) is sent to Claude, which returns schema-constrained JSON
             with per-field confidence.
DEMO mode  : no API key. Text-layer PDFs are parsed with deterministic label/pattern rules; the
             confidence is a documented heuristic (label found + value matches the expected format,
             unreadable characters lower it). Images cannot be read without a vision model, so every
             field is returned as missing and the workflow is routed to a human.
Missing or unreadable values are never invented.
"""

import base64
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

from app.agents.document_types import (
    COMPLAINT_CATEGORIES,
    DATE,
    DOCUMENT_TYPES,
    URGENT_WORDS,
    field_specs,
)
from app.core.config import get_settings

log = logging.getLogger("actionloop.extractor")

HIGH, FORMAT_MISMATCH, UNREADABLE = 0.96, 0.68, 0.41
DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%d/%m/%y"]


class ExtractionError(RuntimeError):
    pass


# --------------------------------------------------------------------------- helpers

def read_text(path: Path, content_type: str) -> str | None:
    if content_type != "application/pdf":
        return None
    try:
        reader = PdfReader(str(path))
        return "\n".join((p.extract_text() or "") for p in reader.pages).strip()
    except Exception as exc:
        raise ExtractionError(f"PDF could not be read: {exc}") from exc


def classify(text: str) -> tuple[str | None, float, dict]:
    low = text.lower()
    scores = {t: sum(low.count(k) for k in spec["keywords"]) for t, spec in DOCUMENT_TYPES.items()}
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return None, 0.0, scores
    return best, round(min(0.99, 0.55 + 0.45 * scores[best] / total), 2), scores


def normalize_date(raw: str) -> str | None:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def normalize_amount(raw: str) -> str | None:
    cleaned = re.sub(r"(INR|Rs\.?|₹|\s|,)", "", raw)
    try:
        return f"{float(cleaned):.2f}"
    except ValueError:
        return None


def _find_labelled(lines: list[str], aliases: list[str]) -> str | None:
    for alias in aliases:
        rx = re.compile(rf"^\s*{re.escape(alias)}\s*[:\-]\s*(.*)$", re.IGNORECASE)
        for line in lines:
            m = rx.match(line)
            if m:
                return m.group(1).strip()
    return None


def _field(spec: dict, value, confidence: float, status: str, note: str = "", raw: str | None = None) -> dict:
    return {
        "name": spec["name"], "label": spec["label"], "value": value, "raw": raw,
        "confidence": round(confidence, 2), "status": status, "note": note, "required": spec["required"],
    }


# --------------------------------------------------------------------------- demo parser

def demo_extract(text: str, doc_type: str) -> list[dict]:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    fields = []
    for spec in field_specs(doc_type):
        if not spec["aliases"]:
            continue  # derived fields handled below
        raw = _find_labelled(lines, spec["aliases"])
        if raw is None or raw == "" or raw.lower() in {"-", "n/a", "na", "not provided"}:
            fields.append(_field(spec, None, 0.0, "missing", "Label not found or left blank on the document."))
            continue
        if "?" in raw or "[illegible]" in raw.lower():
            fields.append(_field(spec, None, UNREADABLE, "uncertain",
                                 f"Characters are unreadable in the source ('{raw}'). Needs human verification.", raw))
            continue
        m = re.fullmatch(spec["pattern"], raw)
        value = m.group(1).strip() if m else raw
        if spec["pattern"] == DATE:
            iso = normalize_date(value)
            if iso is None:
                fields.append(_field(spec, value, FORMAT_MISMATCH, "uncertain", "Date format not recognised.", raw))
                continue
            value = iso
        if spec["name"] in {"total_amount", "amount_paid"}:
            amt = normalize_amount(value)
            if amt is None:
                fields.append(_field(spec, value, FORMAT_MISMATCH, "uncertain", "Amount could not be parsed.", raw))
                continue
            value = amt
        if m is None:
            fields.append(_field(spec, value, FORMAT_MISMATCH, "uncertain", "Value does not match the expected format.", raw))
        else:
            fields.append(_field(spec, value, HIGH, "ok", "", raw))

    if doc_type == "complaint_email":
        fields.extend(_complaint_derived(text, lines))
    return fields


def _complaint_derived(text: str, lines: list[str]) -> list[dict]:
    specs = {s["name"]: s for s in field_specs("complaint_email")}
    body_lines, in_body = [], False
    for ln in text.splitlines():
        if in_body:
            body_lines.append(ln.strip())
        elif not ln.strip() or ln.lower().startswith("dear") or ln.lower().startswith("respected"):
            in_body = True
            if ln.strip():
                body_lines.append(ln.strip())
    body = " ".join(b for b in body_lines if b).strip()
    summary = body[:400] if body else None
    low = text.lower()
    hits = {cat: sum(low.count(k) for k in kws) for cat, kws in COMPLAINT_CATEGORIES.items()}
    cat = max(hits, key=hits.get)
    category = cat if hits[cat] > 0 else "General Administration"
    urgent_hits = [w for w in URGENT_WORDS if w in low]
    urgency = "high" if len(urgent_hits) >= 2 or "safety" in category.lower() else ("medium" if urgent_hits else "normal")
    return [
        _field(specs["description"], summary, HIGH if summary else 0.0, "ok" if summary else "missing",
               "" if summary else "No message body found."),
        _field(specs["complaint_category"], category, 0.9 if hits[cat] else 0.55, "ok" if hits[cat] else "uncertain",
               f"Keyword match: {hits[cat]} signal(s) for {category}."),
        _field(specs["urgency"], urgency, 0.88, "ok",
               f"Urgency cues found: {', '.join(urgent_hits) or 'none'}."),
    ]


# --------------------------------------------------------------------------- live (Claude)

def _llm_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "document_type": {"type": "string", "enum": list(DOCUMENT_TYPES) + ["unknown"]},
            "type_confidence": {"type": "number"},
            "fields": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": ["string", "null"]},
                        "confidence": {"type": "number"},
                        "note": {"type": "string"},
                    },
                    "required": ["name", "value", "confidence", "note"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["document_type", "type_confidence", "fields"],
        "additionalProperties": False,
    }


def _llm_prompt() -> str:
    catalogue = {t: [f["name"] for f in spec["fields"]] for t, spec in DOCUMENT_TYPES.items()}
    return (
        "You are the Extractor agent of an administrative workflow system. Identify the document type, "
        "then extract every field listed for that type.\n"
        f"Field catalogue (type -> field names): {json.dumps(catalogue)}\n"
        "Rules: return null for any value that is absent or unreadable - never guess or fill in a "
        "plausible value. Give each field a confidence between 0 and 1 reflecting how legible and "
        "unambiguous it is in the source. Dates as YYYY-MM-DD, amounts as plain decimals (e.g. 45230.00). "
        "Use the note to explain any uncertainty. For complaints, `description` is a short neutral "
        "summary, `complaint_category` one of: " + ", ".join(COMPLAINT_CATEGORIES) +
        ", General Administration; `urgency` one of high, medium, normal."
    )


def llm_extract(path: Path, content_type: str) -> tuple[str | None, float, list[dict], str]:
    import anthropic

    s = get_settings()
    client = anthropic.Anthropic(api_key=s.anthropic_api_key)
    data = base64.standard_b64encode(path.read_bytes()).decode()
    if content_type == "application/pdf":
        block = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}}
    else:
        block = {"type": "image", "source": {"type": "base64", "media_type": content_type, "data": data}}
    try:
        response = client.beta.messages.create(
            model=s.anthropic_model,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={
                "effort": "medium",
                "format": {"type": "json_schema", "schema": _llm_schema()},
            },
            messages=[{"role": "user", "content": [block, {"type": "text", "text": _llm_prompt()}]}],
        )
    except anthropic.RateLimitError as exc:
        raise ExtractionError("Model provider rate limit reached; retry shortly.") from exc
    except anthropic.APIStatusError as exc:
        raise ExtractionError(f"Model provider error {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise ExtractionError("Could not reach the model provider.") from exc

    if response.stop_reason == "refusal":
        raise ExtractionError("The model declined to process this document.")
    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise ExtractionError("Model returned no structured output.")
    out = json.loads(text)
    doc_type = out["document_type"] if out["document_type"] in DOCUMENT_TYPES else None
    by_name = {f["name"]: f for f in out["fields"]}
    fields = []
    for spec in field_specs(doc_type or ""):
        f = by_name.get(spec["name"])
        value = f and f["value"]
        conf = float(f["confidence"]) if f else 0.0
        threshold = s.low_confidence_threshold
        status = "missing" if value in (None, "") else ("uncertain" if conf < threshold else "ok")
        fields.append(_field(spec, value if value not in ("",) else None, conf if value else 0.0, status,
                             (f or {}).get("note", "") or ("Not present in the document." if status == "missing" else "")))
    return doc_type, float(out.get("type_confidence", 0.0)), fields, f"claude:{response.model}"


# --------------------------------------------------------------------------- entry point

def run_extractor(path: Path, content_type: str) -> dict:
    s = get_settings()
    warnings: list[str] = []
    if not path.exists():
        raise ExtractionError("Stored file is missing")

    if not s.demo_mode:
        doc_type, type_conf, fields, engine = llm_extract(path, content_type)
        text_chars = None
    else:
        text = read_text(path, content_type)
        engine = "demo:pdf-text-parser"
        if text is None:
            return {
                "document_type": None, "type_confidence": 0.0, "fields": [], "engine": "demo:no-vision",
                "text_chars": 0,
                "warnings": ["DEMO MODE: image documents need a vision LLM (set ANTHROPIC_API_KEY). "
                             "No fields were extracted; a reviewer must enter them."],
            }
        if len(text) < 20:
            raise ExtractionError("PDF has no readable text layer (scanned image). Enable a vision LLM or upload a text PDF.")
        text_chars = len(text)
        doc_type, type_conf, _ = classify(text)
        fields = demo_extract(text, doc_type) if doc_type else []

    if doc_type is None:
        warnings.append("Document type could not be identified.")
    for f in fields:
        if f["required"] and f["status"] == "missing":
            warnings.append(f"Required field missing: {f['label']}")
        elif f["status"] == "uncertain":
            warnings.append(f"Low confidence: {f['label']}")
    return {
        "document_type": doc_type,
        "type_confidence": type_conf,
        "fields": fields,
        "engine": engine,
        "text_chars": text_chars,
        "warnings": warnings,
    }
