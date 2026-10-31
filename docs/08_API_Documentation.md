# 08 · API Documentation

Interactive docs: **http://localhost:8000/docs** (Swagger) · `/redoc`. All endpoints except `/api/auth/login`, `/api/health`, `/api/system/status` and `/api/blockchain/config` require `Authorization: Bearer <token>`.

Roles: `viewer` < `operator` < `reviewer` < `admin`.

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/api/auth/login` | — | `{email,password}` → `{access_token,user}` |
| GET | `/api/auth/me` | any | Current user |
| POST | `/api/documents/upload` | operator | multipart `file`; 415 wrong type/content, 413 too large |
| GET | `/api/documents` | any | List (`include_seeded`, `limit`) |
| GET | `/api/documents/{id}` | any | Detail with workflows |
| GET | `/api/documents/{id}/file` | any | Original file |
| POST | `/api/workflows/start` | operator | `{document_id}` → 202; 409 if already active |
| GET | `/api/workflows` | any | List (`status`, `include_seeded`) |
| GET | `/api/workflows/{id}` | any | Full detail: executions, fields, validations, actions, approvals |
| GET | `/api/workflows/{id}/status` | any | Lightweight status for polling |
| POST | `/api/workflows/{id}/retry` | operator | Retry a failed workflow |
| GET | `/api/workflows/topology` | — | Graph nodes/edges |
| GET | `/api/agents/executions/{workflow_id}` | any | Agent executions |
| GET | `/api/agents/status` | any | Per-agent counters |
| GET | `/api/approvals/pending` | any | Queue (priority ordered) |
| GET | `/api/approvals/history` | any | Decided approvals |
| POST | `/api/approvals/{id}/decision` | reviewer | `{decision: approve\|reject\|request_correction, comment, corrections}`; comment required unless approving; 409 if already decided |
| GET | `/api/audit/events` | any | Search/filter (`search`, `workflow_id`, `event_type`, `agent`, `include_seeded`) |
| POST | `/api/audit/verify` | any | Recompute full chain; `simulate_tamper_event_id` alters an in-memory copy only |
| GET | `/api/audit/events/{id}/verify` | any | Off-chain + on-chain verification for one event |
| GET | `/api/audit/export.csv` | any | CSV export |
| GET | `/api/analytics/overview` | any | Dashboard metrics |
| GET | `/api/analytics/reports?from&to` | any | Report; 422 on bad range |
| GET | `/api/analytics/reports.csv` | any | CSV report |
| GET | `/api/blockchain/config` | — | Network + contract address + ABI (public, no secrets) |
| GET | `/api/blockchain/status` | any | RPC reachability, chain id check, contract code, totals, relayer |
| GET | `/api/blockchain/anchors` | any | Anchors with tx hashes and explorer links |
| POST | `/api/blockchain/events/{event_id}/anchor` | reviewer | Queue any (non-seeded) audit event |
| POST | `/api/blockchain/anchors/{id}/process` | reviewer | Submit / re-check via relayer (idempotent) |
| POST | `/api/blockchain/anchors/{id}/wallet-submission` | reviewer | `{tx_hash}` from BridgeKey; backend re-verifies on-chain |
| GET | `/api/blockchain/verify/{event_hash}` | any | Read contract record |
| GET | `/api/blockchain/submitters/{address}` | any | `isSubmitter` |
| POST | `/api/blockchain/submitters` | admin | Owner-signed `setSubmitter` |
| GET/PATCH | `/api/settings/rules[/{id}]` | any / admin | Validation rules |
| GET | `/api/system/status` | — | DEMO MODE flag and integration status |

Errors are JSON `{"detail": "..."}` with standard status codes (400, 401, 403, 404, 409, 413, 415, 422, 502).
