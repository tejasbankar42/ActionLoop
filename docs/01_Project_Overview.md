# 01 · Project Overview

**ActionLoop** — *From Documents to Decisions. Automatically.*
Category: AI-powered multi-agent workflow automation · Team Granted (Aditya Shelke, Tejas Bankar, Siddhika Hanumante), NMIET Pune · MST Blockchain Buildathon 2.0.

ActionLoop ingests administrative documents (invoices, fee receipts, admission forms, clinic registrations, complaint emails), extracts structured data, validates it against configurable rules and the database, plans next actions, routes sensitive or uncertain cases to a human reviewer, and records every step in a tamper-evident audit trail whose key events are anchored on MST Blockchain.

## What is implemented

| Area | Status |
|---|---|
| Upload, preview, type/size/content validation | Implemented |
| Extractor (Claude vision in live mode; deterministic PDF parser in DEMO MODE) | Implemented (live mode requires `ANTHROPIC_API_KEY`; not exercised in our test runs) |
| Validator (45 seeded rules, duplicate detection) | Implemented, tested |
| Action Planner + approval policy | Implemented, tested |
| LangGraph orchestration + persistent approval checkpoint | Implemented, tested |
| Approval center with corrections | Implemented, tested |
| SHA-256 hash-chained append-only audit + verification + tamper simulation | Implemented, tested |
| MST audit registry contract | Implemented, 10 Hardhat tests |
| Backend relayer anchoring + receipt/`isAnchored` verification | Implemented, verified end-to-end on a local EVM |
| BridgeKey wallet connect / network switch / sign anchor | Implemented (standard EIP-1193/6963); not tested with the real BridgeKey extension in our environment |
| MST Testnet deployment | See [18_MST_Blockchain_Integration.md](18_MST_Blockchain_Integration.md) for current status |
| Action execution | **Simulated** and labelled as such |
