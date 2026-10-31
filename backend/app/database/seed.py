"""Demo seed: organization, users, validation rules, sample documents and ~6 weeks of
illustrative history. Everything seeded is flagged (`is_seeded`, payload.seeded) so the UI can
label it and so it is never anchored on-chain."""

import hashlib
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    ActionPlan,
    AgentExecution,
    Approval,
    Document,
    ExtractedField,
    Organization,
    User,
    ValidationRule,
    Workflow,
)
from app.services import audit_service
from app.services.storage import get_storage
from app.utils.sample_docs import SAMPLES_DIR, generate

DEMO_PASSWORD = "ActionLoop@2026"
DEMO_USERS = [
    ("admin@actionloop.demo", "Aditya Shelke", "admin", "Administration"),
    ("reviewer@actionloop.demo", "Siddhika Hanumante", "reviewer", "Accounts Department"),
    ("operator@actionloop.demo", "Tejas Bankar", "operator", "Front Office"),
    ("viewer@actionloop.demo", "Guest Judge", "viewer", "External"),
]

GSTIN = r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$"
EMAIL = r"^[\w.+\-]+@[\w\-]+\.[\w.\-]+$"
PHONE = r"^\+?[0-9][0-9 \-]{8,14}$"

RULES = [
    # code, doc_type, rule_type, field, params, severity, description
    ("INV_REQ_NUMBER", "invoice", "required", "invoice_number", {}, "failed", "Every invoice needs a unique number."),
    ("INV_REQ_VENDOR", "invoice", "required", "vendor_name", {}, "failed", ""),
    ("INV_REQ_GSTIN", "invoice", "required", "vendor_gstin", {}, "failed", "GST law requires the supplier GSTIN."),
    ("INV_REQ_DATE", "invoice", "required", "invoice_date", {}, "failed", ""),
    ("INV_REQ_TOTAL", "invoice", "required", "total_amount", {}, "failed", ""),
    ("INV_GSTIN_FORMAT", "invoice", "regex", "vendor_gstin", {"pattern": GSTIN, "hint": "15-char GSTIN"}, "failed", ""),
    ("INV_DATE_NOT_FUTURE", "invoice", "not_future", "invoice_date", {}, "failed", ""),
    ("INV_DUE_AFTER_DATE", "invoice", "date_order", "due_date", {"after": "invoice_date"}, "warning", ""),
    ("INV_TOTAL_RANGE", "invoice", "range", "total_amount", {"min": 1, "max": 10_000_000}, "failed", ""),
    ("INV_DUPLICATE", "invoice", "duplicate", "invoice_number", {"fields": ["invoice_number", "vendor_gstin"]}, "failed", ""),
    ("FEE_REQ_RECEIPT", "fee_receipt", "required", "receipt_number", {}, "failed", ""),
    ("FEE_REQ_STUDENT", "fee_receipt", "required", "student_name", {}, "failed", ""),
    ("FEE_REQ_ID", "fee_receipt", "required", "student_id", {}, "failed", ""),
    ("FEE_REQ_AMOUNT", "fee_receipt", "required", "amount_paid", {}, "failed", ""),
    ("FEE_REQ_DATE", "fee_receipt", "required", "payment_date", {}, "failed", ""),
    ("FEE_ID_FORMAT", "fee_receipt", "regex", "student_id", {"pattern": r"^NMIET-[A-Z]{2}-\d{4}-\d{3}$", "hint": "NMIET-XX-YYYY-NNN"}, "warning", ""),
    ("FEE_DATE_NOT_FUTURE", "fee_receipt", "not_future", "payment_date", {}, "failed", ""),
    ("FEE_AMOUNT_RANGE", "fee_receipt", "range", "amount_paid", {"min": 500, "max": 500_000}, "failed", ""),
    ("FEE_DUPLICATE", "fee_receipt", "duplicate", "receipt_number", {"fields": ["receipt_number"]}, "failed", ""),
    ("ADM_REQ_NAME", "admission_form", "required", "applicant_name", {}, "failed", ""),
    ("ADM_REQ_DOB", "admission_form", "required", "date_of_birth", {}, "failed", ""),
    ("ADM_REQ_EMAIL", "admission_form", "required", "email", {}, "failed", ""),
    ("ADM_REQ_PHONE", "admission_form", "required", "phone", {}, "failed", ""),
    ("ADM_REQ_COURSE", "admission_form", "required", "course_applied", {}, "failed", ""),
    ("ADM_REQ_MARKS", "admission_form", "required", "previous_marks_percent", {}, "failed", ""),
    ("ADM_REQ_GUARDIAN", "admission_form", "required", "guardian_name", {}, "failed", "Guardian details are mandatory for minors and hostel allotment."),
    ("ADM_EMAIL_FORMAT", "admission_form", "regex", "email", {"pattern": EMAIL, "hint": "name@domain"}, "failed", ""),
    ("ADM_PHONE_FORMAT", "admission_form", "regex", "phone", {"pattern": PHONE, "hint": "10+ digit phone"}, "failed", ""),
    ("ADM_MARKS_RANGE", "admission_form", "range", "previous_marks_percent", {"min": 0, "max": 100}, "failed", ""),
    ("ADM_AGE", "admission_form", "age", "date_of_birth", {"min": 16, "max": 30}, "warning", ""),
    ("ADM_DUPLICATE", "admission_form", "duplicate", "email", {"fields": ["email"]}, "warning", ""),
    ("CLN_REQ_NAME", "clinic_registration", "required", "patient_name", {}, "failed", ""),
    ("CLN_REQ_DOB", "clinic_registration", "required", "date_of_birth", {}, "failed", ""),
    ("CLN_REQ_PHONE", "clinic_registration", "required", "phone", {}, "failed", ""),
    ("CLN_REQ_EMERGENCY", "clinic_registration", "required", "emergency_contact", {}, "failed", ""),
    ("CLN_REQ_REASON", "clinic_registration", "required", "visit_reason", {}, "failed", ""),
    ("CLN_PHONE_FORMAT", "clinic_registration", "regex", "phone", {"pattern": PHONE, "hint": "10+ digit phone"}, "failed", ""),
    ("CLN_AGE", "clinic_registration", "age", "date_of_birth", {"min": 0, "max": 120}, "failed", ""),
    ("CLN_RETURNING", "clinic_registration", "duplicate", "phone", {"fields": ["phone", "date_of_birth"]}, "warning", ""),
    ("CMP_REQ_EMAIL", "complaint_email", "required", "sender_email", {}, "failed", ""),
    ("CMP_REQ_SUBJECT", "complaint_email", "required", "subject", {}, "failed", ""),
    ("CMP_REQ_BODY", "complaint_email", "required", "description", {}, "failed", ""),
    ("CMP_REQ_DATE", "complaint_email", "required", "received_date", {}, "warning", ""),
    ("CMP_EMAIL_FORMAT", "complaint_email", "regex", "sender_email", {"pattern": EMAIL, "hint": "name@domain"}, "failed", ""),
    ("ALL_CONFIDENCE", "*", "confidence", None, {"threshold": 0.75}, "warning", "Fields below the confidence threshold are routed to a human."),
]

HISTORY_TEMPLATES = [
    ("invoice", "inv_{n}.pdf", {"invoice_number": "INV-{y}-{n:04d}", "vendor_name": "{vendor}", "vendor_gstin": "{gstin}",
                                "invoice_date": "{date}", "total_amount": "{amount}.00"}),
    ("fee_receipt", "fee_{n}.pdf", {"receipt_number": "FR-{y}-{n:05d}", "student_name": "{student}",
                                    "student_id": "NMIET-CE-2024-{n3:03d}", "amount_paid": "{amount}.00", "payment_date": "{date}"}),
    ("admission_form", "admission_{n}.pdf", {"applicant_name": "{student}", "email": "applicant{n}@example.com",
                                             "course_applied": "B.E. Mechanical Engineering"}),
    ("clinic_registration", "clinic_{n}.pdf", {"patient_name": "{student}", "phone": "+91 9{n:09d}"}),
    ("complaint_email", "complaint_{n}.pdf", {"subject": "Projector not working in room A-{n3:03d}",
                                              "complaint_category": "IT Services", "urgency": "medium"}),
]
VENDORS = [("Shree Ganesh Office Supplies", "27AAKFS5521M1Z2"), ("Pune TechSupplies Pvt. Ltd.", "27AABCP1234Q1Z5"),
           ("Sahyadri Electricals", "27AAGFS9087L1Z4"), ("Deccan Lab Instruments", "27AADCD7781K1Z9")]
NAMES = ["Sneha Pawar", "Rohan Jadhav", "Ananya Iyer", "Vikram Shinde", "Pooja Kale", "Harsh Mehta", "Kavya Nair",
         "Aditya More", "Isha Gokhale", "Siddharth Rao", "Neha Chavan", "Yash Thakur"]


def seed(db: Session) -> None:
    if db.scalar(select(func.count(User.id))):
        return
    org = Organization(name="Nutan Maharashtra Institute of Engineering and Technology", sector="education", city="Talegaon Dabhade, Pune")
    db.add(org)
    db.flush()
    users = {}
    for email, name, role, dept in DEMO_USERS:
        u = User(organization_id=org.id, email=email, full_name=name, role=role, department=dept,
                 password_hash=hash_password(DEMO_PASSWORD))
        db.add(u)
        users[role] = u
    for code, dt, rt, field, params, sev, desc in RULES:
        db.add(ValidationRule(organization_id=org.id, code=code, document_type=dt, rule_type=rt, field=field,
                              params=params, severity=sev, description=desc))
    db.commit()
    _seed_history(db, org, users)
    _register_samples(db, org, users["operator"])


def _register_samples(db: Session, org: Organization, user: User) -> None:
    manifest = generate(SAMPLES_DIR)
    storage = get_storage()
    for m in manifest:
        data = (SAMPLES_DIR / m["file"]).read_bytes()
        ctype = "image/png" if m["file"].endswith(".png") else "application/pdf"
        key = storage.save(data, "." + m["file"].rsplit(".", 1)[1])
        db.add(Document(organization_id=org.id, uploaded_by=user.id, filename=m["file"], content_type=ctype,
                        size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), storage_key=key,
                        is_sample=True, status="uploaded"))
    db.commit()


def _seed_history(db: Session, org: Organization, users: dict) -> None:
    rng = random.Random(42)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=42)
    plan = []
    for n in range(1, 61):
        ts = start + timedelta(days=rng.uniform(0, 41), hours=rng.uniform(9, 17) - 12)
        plan.append((ts, n))
    plan.sort()
    # The record scenario C duplicates: processed and paid on 4 Sep 2026.
    special = datetime(2026, 9, 4, 11, 20, tzinfo=timezone.utc)
    plan.append((special, 0))
    plan.sort()

    for ts, n in plan:
        if n == 0:
            doc_type, values = "invoice", {"invoice_number": "INV-SGO-2026-0412", "vendor_name": "Shree Ganesh Office Supplies",
                                           "vendor_gstin": "27AAKFS5521M1Z2", "invoice_date": "2026-09-02", "total_amount": "18240.00"}
            fname, status = "INV-SGO-2026-0412.pdf", "completed"
        else:
            doc_type, fname_t, tmpl = HISTORY_TEMPLATES[n % len(HISTORY_TEMPLATES)]
            vendor, gstin = VENDORS[n % len(VENDORS)]
            ctx = {"n": n, "n3": (n * 7) % 1000, "y": ts.year, "vendor": vendor, "gstin": gstin,
                   "date": ts.date().isoformat(), "amount": rng.choice([8400, 12650, 18240, 23900, 42000, 61500, 4500, 38500]),
                   "student": NAMES[n % len(NAMES)]}
            values = {k: v.format(**ctx) for k, v in tmpl.items()}
            fname = fname_t.format(**ctx)
            r = rng.random()
            status = "completed" if r < 0.74 else "needs_correction" if r < 0.86 else "rejected" if r < 0.93 else "failed"
        _seed_workflow(db, org, users, ts, doc_type, fname, values, status, rng)


def _seed_workflow(db, org, users, ts, doc_type, fname, values, status, rng) -> None:
    op, rev = users["operator"], users["reviewer"]
    digest = hashlib.sha256(f"seed:{fname}:{ts.isoformat()}".encode()).hexdigest()
    doc = Document(organization_id=org.id, uploaded_by=op.id, filename=fname, content_type="application/pdf",
                   size_bytes=rng.randint(38_000, 240_000), sha256=digest, storage_key="seeded-no-file",
                   detected_type=doc_type, is_seeded=True, created_at=ts,
                   status={"completed": "processed"}.get(status, status))
    db.add(doc)
    db.flush()
    duration = rng.randint(2_400, 9_800) + (rng.randint(60_000, 3_600_000) if status != "failed" and rng.random() < 0.45 else 0)
    needs_approval = duration > 60_000 or status in ("rejected", "needs_correction")
    wf = Workflow(document_id=doc.id, started_by=op.id, status=status, current_stage="audit", document_type=doc_type,
                  validation_status={"completed": "passed", "needs_correction": "failed", "rejected": "warning", "failed": None}[status],
                  requires_approval=needs_approval, priority=rng.choice(["normal", "normal", "high"]), is_seeded=True,
                  created_at=ts, completed_at=ts + timedelta(milliseconds=duration), duration_ms=duration,
                  error="Extraction failed: PDF has no readable text layer (scanned image)." if status == "failed" else None,
                  execution_result={"outcome": status, "seeded": True})
    db.add(wf)
    db.flush()
    t = ts
    for agent, base in (("extractor", 1800), ("validator", 160), ("action_planner", 90)):
        if status == "failed" and agent != "extractor":
            break
        d = int(base * rng.uniform(0.6, 1.8))
        db.add(AgentExecution(workflow_id=wf.id, agent=agent, status="failed" if status == "failed" else "completed",
                              started_at=t, finished_at=t + timedelta(milliseconds=d), duration_ms=d,
                              engine="seeded", explanation="Seeded history (illustrative)."))
        t += timedelta(milliseconds=d)
    if status != "failed":
        for name, value in values.items():
            db.add(ExtractedField(workflow_id=wf.id, name=name, label=name.replace("_", " ").title(), value=value,
                                  confidence=round(rng.uniform(0.86, 0.99), 2), status="ok"))
        db.add(ActionPlan(workflow_id=wf.id, step=1, action="seeded", title="Historical action", department="Administration",
                          priority="normal", impact="low", requires_approval=needs_approval, reasoning="Seeded history",
                          status="executed" if status == "completed" else "skipped"))
    if needs_approval and status != "failed":
        decided = ts + timedelta(milliseconds=duration - 1500)
        db.add(Approval(workflow_id=wf.id, status={"completed": "approved", "rejected": "rejected"}.get(status, "correction_requested"),
                        reasons=["Seeded history"], reviewer_id=rev.id, reviewer_name=rev.full_name,
                        created_at=t, decided_at=decided))
    db.commit()
    payload = {"seeded": True, "document_type": doc_type}
    audit_service.append_event(db, event_type="WORKFLOW_STARTED", description=f"[seeded] Workflow started for '{fname}'.",
                               actor=op.full_name, user_id=op.id, workflow_id=wf.id, payload=payload, timestamp=ts)
    end_type = {"completed": "WORKFLOW_COMPLETED", "needs_correction": "CORRECTION_REQUESTED",
                "rejected": "WORKFLOW_REJECTED", "failed": "WORKFLOW_FAILED"}[status]
    if needs_approval and status != "failed":
        audit_service.append_event(db, event_type="APPROVAL_DECISION", description=f"[seeded] {rev.full_name} recorded a decision.",
                                   actor=rev.full_name, user_id=rev.id, agent="human_approval", workflow_id=wf.id,
                                   payload=payload, timestamp=wf.completed_at - timedelta(seconds=1))
    audit_service.append_event(db, event_type=end_type, description=f"[seeded] Workflow closed with outcome '{status}'.",
                               actor="Audit Service", agent="audit", workflow_id=wf.id, payload=payload, timestamp=wf.completed_at)
