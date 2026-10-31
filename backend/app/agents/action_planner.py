"""Agent 3 - Action Planner. Turns extraction + validation into an ordered, explainable plan and
decides which actions need a human. Deterministic policy so the approval gate cannot be talked
around by model output."""

from app.agents.document_types import CATEGORY_DEPARTMENT, type_label

HIGH_VALUE_INVOICE = 50_000.0


def _a(action, title, department, priority, impact, requires_approval, reasoning):
    return {"action": action, "title": title, "department": department, "priority": priority,
            "impact": impact, "requires_approval": requires_approval, "reasoning": reasoning}


def run_planner(doc_type: str | None, fields: list[dict], validation: dict) -> dict:
    f = {x["name"]: x for x in fields}
    v = lambda n: (f.get(n) or {}).get("value")  # noqa: E731
    vstatus = validation["status"]
    failed = [r for r in validation["results"] if r["status"] == "failed"]
    warnings = [r for r in validation["results"] if r["status"] == "warning"]
    uncertain = [x["label"] for x in fields if x["status"] == "uncertain"]
    duplicate = validation.get("duplicate")
    actions: list[dict] = []
    approval_reasons: list[str] = []

    # ---- blocking outcomes first
    if doc_type is None:
        actions.append(_a("manual_triage", "Route to front office for manual classification", "Administration",
                          "high", "low", True, "The document type could not be identified; no automated action is safe."))
        approval_reasons.append("Unclassified document")
    elif duplicate:
        actions.append(_a("block_duplicate", "Block processing — possible duplicate", "Accounts Department" if doc_type == "invoice" else "Administration",
                          "high", "high", True,
                          f"{duplicate['message']} Paying or recording it again would double-count the transaction."))
        approval_reasons.append("Duplicate record detected — normal execution blocked")
    elif failed:
        unreadable = [r for r in failed if r["details"].get("reason") == "unreadable"]
        hard = [r for r in failed if r not in unreadable]
        if hard:
            missing = ", ".join(r["field"] or r["rule_code"] for r in hard)
            actions.append(_a("request_correction", f"Request correction from submitter ({missing})",
                              "Admissions Office" if doc_type == "admission_form" else "Administration", "high", "medium", True,
                              "Validation failed: " + "; ".join(r["message"] for r in hard)))
            approval_reasons.append("Validation failed — correction required")
        else:
            labels = ", ".join(f[r["field"]]["label"] for r in unreadable if r["field"] in f)
            actions.append(_a("human_verification", f"Verify unreadable fields against the original ({labels})",
                              "Verification Desk", "high", "medium", True,
                              "The source is legible enough to classify but these values could not be read reliably. "
                              "A reviewer must confirm them; nothing is inferred automatically."))
            approval_reasons.append("Unreadable required values — human verification needed")

    if uncertain:
        approval_reasons.append(f"Low-confidence fields need human verification: {', '.join(uncertain)}")

    # ---- type-specific recommendations (only when not blocked)
    blocked = bool(doc_type is None or duplicate or failed)
    if not blocked:
        if doc_type == "invoice":
            amount = float(v("total_amount") or 0)
            high_value = amount >= HIGH_VALUE_INVOICE
            actions.append(_a("payment_review", f"Schedule payment review — {v('vendor_name')} ₹{amount:,.2f}",
                              "Accounts Department", "high" if high_value else "normal", "high", True,
                              "Mandatory fields present and no duplicate found. Releasing money is a high-impact action, "
                              "so a reviewer must approve before the payment is queued."))
            actions.append(_a("record_payable", "Record payable in ledger (simulated)", "Accounts Department", "normal", "medium", False,
                              f"Invoice {v('invoice_number')} due {v('due_date') or 'on receipt'}; recording keeps the payables register current."))
            approval_reasons.append("Payment release is a high-impact action" + (f" (≥ ₹{HIGH_VALUE_INVOICE:,.0f})" if high_value else ""))
        elif doc_type == "fee_receipt":
            actions.append(_a("update_fee_ledger", f"Mark fees received for {v('student_name')} ({v('student_id')})",
                              "Accounts Department", "normal", "medium", False,
                              "Receipt validated: amount, date and student ID are present and well-formed."))
            actions.append(_a("notify_student", "Send fee confirmation to student (simulated)", "Student Section", "low", "low", False,
                              "Students receive written confirmation once fees are reconciled."))
        elif doc_type == "admission_form":
            actions.append(_a("create_applicant_record", f"Create applicant record — {v('applicant_name')}", "Admissions Office",
                              "normal", "medium", False, "All mandatory admission fields passed validation."))
            actions.append(_a("eligibility_review", f"Eligibility review for {v('course_applied')}", "Admissions Committee",
                              "normal", "high", True, f"HSC {v('previous_marks_percent')}% — admission decisions affect a student's future and need committee sign-off."))
            approval_reasons.append("Admission decision requires committee approval")
        elif doc_type == "clinic_registration":
            actions.append(_a("register_patient", f"Register patient {v('patient_name')}", "Front Desk", "normal", "medium", False,
                              "Mandatory registration fields are complete."))
            actions.append(_a("schedule_consultation", f"Schedule consultation — {v('preferred_doctor') or 'next available doctor'}",
                              "OPD Scheduling", "normal", "low", False, f"Reason for visit: {v('visit_reason')}."))
        elif doc_type == "complaint_email":
            category = v("complaint_category") or "General Administration"
            urgency = v("urgency") or "normal"
            dept = CATEGORY_DEPARTMENT.get(category, "Registrar's Office")
            prio = {"high": "urgent", "medium": "high"}.get(urgency, "normal")
            actions.append(_a("create_ticket", f"Open {category} ticket — {v('subject')}", dept, prio,
                              "medium", urgency == "high",
                              f"Classified as {category} with {urgency} urgency from the complaint text; routed to {dept}."))
            actions.append(_a("acknowledge_sender", f"Acknowledge complaint to {v('sender_email')} (simulated)", "Registrar's Office",
                              "normal", "low", False, "Complainants should receive an acknowledgement with a ticket reference."))
            if urgency == "high":
                approval_reasons.append("Urgent complaint — supervisor confirms escalation")

    if vstatus == "warning" and not uncertain and warnings:
        actions.append(_a("review_warnings", "Review validation warnings", "Administration", "low", "low", False,
                          "; ".join(r["message"] for r in warnings)))

    requires_approval = bool(approval_reasons) or any(a["requires_approval"] for a in actions)
    priorities = [a["priority"] for a in actions]
    overall = next((p for p in ("urgent", "high", "normal", "low") if p in priorities), "normal")
    for i, a in enumerate(actions, 1):
        a["step"] = i
    summary = (f"{type_label(doc_type)}: {len(actions)} action(s) planned; "
               + ("human approval required." if requires_approval else "safe to execute automatically."))
    return {"actions": actions, "requires_approval": requires_approval, "approval_reasons": approval_reasons,
            "priority": overall, "blocked": blocked, "summary": summary}
