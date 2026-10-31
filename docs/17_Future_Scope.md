# 17 · Future Scope

- **Real execution connectors** — Tally/ERP payables, college SIS, email/WhatsApp notifications (replacing simulated execution).
- **OCR fallback** for scanned PDFs/images when no vision model is configured.
- **Merkle-batched anchoring** — anchor one Merkle root per N events to cut gas, with per-event inclusion proofs.
- **Public verification portal** — let a vendor or student verify their own record hash without logging in.
- **Multi-tenant RBAC** with per-organization rule sets and SSO.
- **Object storage adapter** (S3/GCS) — interface already exists (`ObjectStorage`).
- **Alembic migrations** and a Postgres-backed LangGraph checkpointer.
- **KMS/HSM-held relayer key** and multisig ownership of the registry.
- **Active learning** — reviewer corrections feed an evaluation set for extraction prompts.
- **Analytics** — SLA tracking per department, reviewer workload balancing.
