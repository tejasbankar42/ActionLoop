# 16 · Hackathon Demo Guide (≈ 5 minutes)

**Before judges arrive:** backend and frontend running (`npm run build && npm start` for a snappy UI), signed in as `reviewer@actionloop.demo`, BridgeKey unlocked on MST Testnet, a fresh database (delete `backend/actionloop.db` + `backend/storage/` and restart).

1. **Landing (30 s)** — headline, animated agent flow, two-layer proof section. Click *Launch Dashboard*.
2. **Dashboard (20 s)** — point out seeded history is labelled; 0 pending approvals.
3. **Scenario A — success (60 s)** — Documents → `A_invoice…` → *Start processing*. Stages tick live. *Open in Studio*: nodes light up; click Extractor (fields + 96%), Validator (11 checks passed), Planner (payment review needs approval).
4. **Approve (30 s)** — Approvals → reason "Payment release is a high-impact action" → *Approve*. Workflow completes.
5. **On-chain proof (60 s)** — MST Blockchain page: the `APPROVAL_DECISION` and `WORKFLOW_COMPLETED` anchors flip from queued → confirmed. Click the tx hash → MSTScan. Paste the event hash into *Verify any event hash*: backend **and** direct browser RPC both say anchored.
6. **Scenario C — duplicate (30 s)** — process `C_invoice_duplicate.pdf`; validator blocks it, citing the invoice processed on 4 Sep 2026.
7. **Scenario D — low confidence (40 s)** — process `D_fee_receipt…`; amount/date unreadable (41%). In Approvals, type `42500.00` and `2026-10-12`, approve with corrections → re-validated → completed.
8. **Tamper detection (30 s)** — Audit → *Verify entire chain* (valid) → *Simulate tampering* (broken link shown; DB untouched). Open an anchored event: OFF-CHAIN valid + ON-CHAIN present.
9. **Optional — wallet signing** — Audit → open any non-anchored event → *Queue for MST anchoring* → *Sign with BridgeKey* → pending → confirmed with MSTScan link. (Admin must first authorize the wallet on the Blockchain page.)

Talking points: deterministic validation (LLM can't approve itself), persistent approval checkpoint, only hashes on-chain, success shown only after receipt + `isAnchored`.
