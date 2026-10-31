from conftest import run_sample, sample_doc, wait_for


def test_login_rejects_bad_password(client):
    r = client.post("/api/auth/login", json={"email": "reviewer@actionloop.demo", "password": "wrong"})
    assert r.status_code == 401


def test_endpoints_require_auth(client):
    assert client.get("/api/documents").status_code == 401
    assert client.get("/api/documents", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401


def test_viewer_cannot_upload_or_decide(client, viewer):
    r = client.post("/api/documents/upload", files={"file": ("a.pdf", b"%PDF-1.4 x", "application/pdf")}, headers=viewer)
    assert r.status_code == 403
    r = client.post("/api/approvals/x/decision", json={"decision": "approve"}, headers=viewer)
    assert r.status_code == 403


def test_upload_validates_type_size_and_content(client, operator):
    r = client.post("/api/documents/upload", files={"file": ("x.exe", b"MZ...", "application/octet-stream")}, headers=operator)
    assert r.status_code == 415
    r = client.post("/api/documents/upload", files={"file": ("fake.pdf", b"not a pdf", "application/pdf")}, headers=operator)
    assert r.status_code == 415
    r = client.post("/api/documents/upload", files={"file": ("big.pdf", b"%PDF" + b"0" * (11 * 1024 * 1024), "application/pdf")},
                    headers=operator)
    assert r.status_code == 413


def test_upload_pdf_then_fetch(client, operator):
    from app.utils.sample_docs import SAMPLES_DIR

    data = (SAMPLES_DIR / "F_clinic_registration.pdf").read_bytes()
    r = client.post("/api/documents/upload", files={"file": ("clinic.pdf", data, "application/pdf")}, headers=operator)
    assert r.status_code == 201
    doc = r.json()
    assert len(doc["sha256"]) == 64
    assert client.get(f"/api/documents/{doc['id']}/file", headers=operator).content == data


def test_error_for_unknown_resources(client, reviewer):
    assert client.get("/api/workflows/does-not-exist", headers=reviewer).status_code == 404
    assert client.post("/api/workflows/start", json={"document_id": "nope"}, headers=reviewer).status_code == 404
    assert client.post("/api/workflows/start", json={}, headers=reviewer).status_code == 422


def test_scenario_a_success_after_approval(client, reviewer):
    wf = run_sample(client, reviewer, "A_invoice_pune_techsupplies.pdf")
    assert wf["status"] == "awaiting_approval"
    assert wf["document_type"] == "invoice" and wf["validation_status"] == "passed"
    assert any("high-impact" in r for r in wf["approval_reasons"])
    approval = wf["approvals"][0]
    r = client.post(f"/api/approvals/{approval['id']}/decision", json={"decision": "approve", "comment": "OK"}, headers=reviewer)
    assert r.status_code == 200
    done = wait_for(client, reviewer, wf["id"], ("completed",))
    assert done["execution_result"]["outcome"] == "completed"
    assert all(a["status"] == "executed" for a in done["actions"])
    # a decided approval cannot be decided twice
    r = client.post(f"/api/approvals/{approval['id']}/decision", json={"decision": "approve"}, headers=reviewer)
    assert r.status_code == 409


def test_scenario_b_missing_field_requests_correction(client, reviewer):
    wf = run_sample(client, reviewer, "B_admission_form_missing_field.pdf")
    failed = [v for v in wf["validations"] if v["status"] == "failed"]
    assert any(v["field"] == "guardian_name" for v in failed)
    assert wf["actions"][0]["action"] == "request_correction"


def test_scenario_c_duplicate_blocked(client, reviewer):
    wf = run_sample(client, reviewer, "C_invoice_duplicate.pdf")
    dup = [v for v in wf["validations"] if v["rule_type"] == "duplicate"]
    assert dup and dup[0]["status"] == "failed"
    assert wf["actions"][0]["action"] == "block_duplicate"
    assert not any(a["action"] == "payment_review" for a in wf["actions"])


def test_scenario_d_low_confidence_then_corrected(client, reviewer):
    wf = run_sample(client, reviewer, "D_fee_receipt_unclear_amount.pdf")
    uncertain = {f["name"] for f in wf["fields"] if f["status"] == "uncertain"}
    assert {"amount_paid", "payment_date"} <= uncertain
    assert next(f for f in wf["fields"] if f["name"] == "amount_paid")["value"] is None  # never invented
    approval = wf["approvals"][0]
    r = client.post(f"/api/approvals/{approval['id']}/decision",
                    json={"decision": "approve", "comment": "Verified against counterfoil",
                          "corrections": {"amount_paid": "42500.00", "payment_date": "2026-10-12"}}, headers=reviewer)
    assert r.status_code == 200
    done = wait_for(client, reviewer, wf["id"], ("completed", "needs_correction"))
    assert done["status"] == "completed"
    assert next(f for f in done["fields"] if f["name"] == "amount_paid")["status"] == "corrected"


def test_scenario_e_complaint_routed(client, reviewer):
    wf = run_sample(client, reviewer, "E_complaint_email_hostel_leak.pdf")
    fields = {f["name"]: f["value"] for f in wf["fields"]}
    assert fields["complaint_category"] == "Facilities & Maintenance"
    assert fields["urgency"] == "high"
    assert wf["actions"][0]["department"] == "Estate & Maintenance Office"


def test_rejection_closes_without_executing(client, reviewer, operator):
    # Re-upload invoice A so it gets its own workflow
    from app.utils.sample_docs import SAMPLES_DIR

    data = (SAMPLES_DIR / "A_invoice_pune_techsupplies.pdf").read_bytes()
    doc = client.post("/api/documents/upload", files={"file": ("a2.pdf", data, "application/pdf")}, headers=operator).json()
    start = client.post("/api/workflows/start", json={"document_id": doc["id"]}, headers=operator).json()
    wf = wait_for(client, operator, start["id"])
    # the first A run completed, so this upload is now a duplicate and must be blocked
    assert any(v["rule_type"] == "duplicate" and v["status"] == "failed" for v in wf["validations"])
    approval = wf["approvals"][0]
    r = client.post(f"/api/approvals/{approval['id']}/decision", json={"decision": "reject"}, headers=reviewer)
    assert r.status_code == 422  # comment required
    r = client.post(f"/api/approvals/{approval['id']}/decision", json={"decision": "reject", "comment": "Duplicate"},
                    headers=reviewer)
    assert r.status_code == 200
    done = wait_for(client, reviewer, wf["id"], ("rejected",))
    assert all(a["status"] == "skipped" for a in done["actions"])


def test_duplicate_workflow_submission_blocked(client, operator):
    doc = sample_doc(client, operator, "G_invoice_photo.png")
    first = client.post("/api/workflows/start", json={"document_id": doc["id"]}, headers=operator)
    second = client.post("/api/workflows/start", json={"document_id": doc["id"]}, headers=operator)
    assert first.status_code == 202
    assert second.status_code == 409


def test_image_in_demo_mode_is_not_faked(client, operator):
    doc = sample_doc(client, operator, "G_invoice_photo.png")
    wf = wait_for(client, operator, doc["latest_workflow"]["id"] if doc["latest_workflow"] else
                  client.get(f"/api/documents/{doc['id']}", headers=operator).json()["workflows"][-1]["id"])
    assert wf["fields"] == []
    assert wf["approval_reasons"] == ["Unclassified document"]


def test_audit_chain_valid_and_events_recorded(client, reviewer):
    r = client.post("/api/audit/verify", json={}, headers=reviewer).json()
    assert r["valid"] is True and r["checked"] > 10
    events = client.get("/api/audit/events", headers=reviewer).json()["events"]
    types = {e["event_type"] for e in events}
    assert {"WORKFLOW_STARTED", "EXTRACTION_COMPLETED", "VALIDATION_COMPLETED", "PLAN_CREATED",
            "APPROVAL_REQUESTED", "APPROVAL_DECISION", "WORKFLOW_COMPLETED"} <= types


def test_simulated_tamper_is_detected_without_changing_db(client, reviewer):
    events = client.get("/api/audit/events", headers=reviewer).json()["events"]
    target = events[5]["id"]
    r = client.post("/api/audit/verify", json={"simulate_tamper_event_id": target}, headers=reviewer).json()
    assert r["valid"] is False and r["broken"][0]["event_id"] == target
    assert client.post("/api/audit/verify", json={}, headers=reviewer).json()["valid"] is True


def test_analytics_reflect_workflows(client, reviewer):
    o = client.get("/api/analytics/overview", headers=reviewer).json()
    assert o["totals"]["live_workflows"] >= 5
    assert o["totals"]["pending_approvals"] >= 1
    r = client.get("/api/analytics/reports", headers=reviewer).json()
    assert r["extraction_accuracy"]["available"] is True
    assert client.get("/api/analytics/reports?from=2026-10-10&to=2026-10-01", headers=reviewer).status_code == 422
    csv_resp = client.get("/api/analytics/reports.csv", headers=reviewer)
    assert csv_resp.status_code == 200 and csv_resp.text.startswith("date,documents")


def test_blockchain_reports_not_configured_honestly(client, reviewer):
    status = client.get("/api/blockchain/status", headers=reviewer).json()
    assert status["contract_address"] is None or status["contract_code_present"] in (True, False)
    anchors = client.get("/api/blockchain/anchors", headers=reviewer).json()
    assert all(a["status"] in ("not_configured", "queued") for a in anchors)
    assert all(a["tx_hash"] is None for a in anchors)
