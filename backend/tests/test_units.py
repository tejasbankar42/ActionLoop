from datetime import datetime, timezone

import pytest

from app.agents.action_planner import run_planner
from app.agents.extractor import classify, demo_extract, normalize_amount, normalize_date
from app.blockchain import contract_service as cs
from app.services.audit_service import GENESIS_HASH, canonical_event_data, compute_hash, verify_chain


def _event(i, prev, **kw):
    ev = {"id": f"e{i}", "sequence": i, "workflow_id": "wf", "timestamp": datetime(2026, 10, 1, 10, i, tzinfo=timezone.utc),
          "user_id": None, "actor": "tester", "agent": None, "event_type": "X", "description": f"event {i}",
          "payload": {"n": i}, "previous_hash": prev}
    ev.update(kw)
    ev["hash"] = compute_hash(prev, canonical_event_data(ev))
    return ev


def _chain(n=4):
    rows, prev = [], GENESIS_HASH
    for i in range(1, n + 1):
        ev = _event(i, prev)
        rows.append(ev)
        prev = ev["hash"]
    return rows


def test_hash_formula_matches_spec():
    import hashlib

    ev = _event(1, GENESIS_HASH)
    assert ev["hash"] == hashlib.sha256((GENESIS_HASH + canonical_event_data(ev)).encode()).hexdigest()


def test_valid_chain_verifies():
    r = verify_chain(_chain())
    assert r["valid"] and r["checked"] == 4


def test_altered_record_detected():
    rows = _chain()
    rows[1] = dict(rows[1], description="altered")
    r = verify_chain(rows)
    assert not r["valid"] and r["broken"][0]["event_id"] == "e2"


def test_deleted_record_detected():
    rows = _chain()
    del rows[1]
    r = verify_chain(rows)
    assert not r["valid"] and r["broken"][0]["event_id"] == "e3"


def test_canonical_json_is_key_order_independent():
    a = _event(1, GENESIS_HASH, payload={"a": 1, "b": 2})
    b = _event(1, GENESIS_HASH, payload={"b": 2, "a": 1})
    assert a["hash"] == b["hash"]


def test_orm_blocks_audit_update(client):
    from app.database.session import SessionLocal
    from app.models import AuditEvent
    from app.services.audit_service import AuditImmutableError

    with SessionLocal() as db:
        ev = db.query(AuditEvent).first()
        ev.description = "tampered"
        with pytest.raises(AuditImmutableError):
            db.commit()
        db.rollback()


def test_extraction_schema_and_normalisation():
    text = "TAX INVOICE\nInvoice No: INV-1\nInvoice Date: 02/09/2026\nVendor: Acme\nGSTIN: 27AAKFS5521M1Z2\nTotal Amount: INR 1,200.50"
    dtype, conf, _ = classify(text)
    assert dtype == "invoice" and 0 < conf <= 1
    fields = {f["name"]: f for f in demo_extract(text, dtype)}
    for f in fields.values():
        assert set(f) >= {"name", "label", "value", "confidence", "status", "note", "required"}
    assert fields["invoice_date"]["value"] == "2026-09-02"
    assert fields["total_amount"]["value"] == "1200.50"
    assert fields["due_date"]["status"] == "missing" and fields["due_date"]["value"] is None
    assert normalize_amount("Rs. 4,500.00") == "4500.00"
    assert normalize_date("31-12-2026") == "2026-12-31"


def test_unreadable_values_not_invented():
    fields = {f["name"]: f for f in demo_extract("FEE RECEIPT\nAmount Paid: Rs. 4?,500.00", "fee_receipt")}
    assert fields["amount_paid"]["value"] is None and fields["amount_paid"]["status"] == "uncertain"


def test_planner_requires_approval_for_payments():
    fields = [{"name": "total_amount", "label": "Total", "value": "1000.00", "status": "ok", "confidence": 0.96},
              {"name": "vendor_name", "label": "Vendor", "value": "Acme", "status": "ok", "confidence": 0.96}]
    plan = run_planner("invoice", fields, {"status": "passed", "results": [], "duplicate": None})
    assert plan["requires_approval"]
    assert any(a["action"] == "payment_review" and a["requires_approval"] for a in plan["actions"])


def test_onchain_encoding_helpers():
    assert cs.workflow_id_hash("abc").startswith("0x") and len(cs.workflow_id_hash("abc")) == 66
    assert cs.event_type_from_bytes32(cs.event_type_bytes32("APPROVAL_DECISION")) == "APPROVAL_DECISION"
    assert cs.to_bytes32_hex("ab" * 32) == "0x" + "ab" * 32
    with pytest.raises(ValueError):
        cs.to_bytes32_hex("abcd")
