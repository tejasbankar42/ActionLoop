# 11 · Audit and Blockchain

## Off-chain: append-only hash chain (`app/services/audit_service.py`)

```
canonical_event = JSON(sort_keys, no whitespace) of
  {id, sequence, workflow_id, timestamp(UTC ISO µs), user_id, actor, agent, event_type, description, payload}
current_hash    = SHA256(previous_hash + canonical_event)
previous_hash of event #1 = GENESIS_HASH = "000…000" (64 zeros)
```

- Appends are serialised with a lock; `sequence` and `hash` are unique.
- ORM listeners reject UPDATE/DELETE; PostgreSQL trigger does the same at the database level.
- `POST /api/audit/verify` recomputes every link and reports the first broken event (edited content → hash mismatch; deleted/reordered row → `previous_hash` mismatch).
- **Tamper simulation** (`simulate_tamper_event_id`) alters an in-memory copy of one event to show detection. The database is never modified.

## On-chain: MST anchoring

Event types anchored automatically (configurable `ANCHOR_EVENT_TYPES`): `APPROVAL_DECISION`, `WORKFLOW_COMPLETED`, `WORKFLOW_REJECTED`, `VALIDATION_BLOCKED`. Reviewers can queue any other non-seeded event from the audit page.

Because each event hash commits to all earlier events, anchoring one event also fixes the entire chain prefix up to that point.

| On-chain field | Value |
|---|---|
| `eventHash` (bytes32) | the audit event's chain hash |
| `workflowIdHash` (bytes32) | SHA-256 of the workflow UUID |
| `eventType` (bytes32) | ASCII label, e.g. `APPROVAL_DECISION` |
| `submitter` | authorized account (relayer or reviewer wallet) |
| `anchoredAt`, `blockNumber` | from the block |

Seeded demo history is **never** anchored.

## Two statuses in the UI

- **OFF-CHAIN AUDIT** — the chain recomputes correctly from genesis up to this event.
- **ON-CHAIN VERIFICATION** — `getRecord(eventHash)` on the contract returns a record whose workflow hash and event type match. States: `verified`, `mismatch`, `pending`, `queued`, `failed`, `not_anchored`, `not_configured`, `unavailable`.

The Blockchain page also verifies a hash **directly from the browser** through the public MST RPC (ethers `JsonRpcProvider`), without going through ActionLoop's backend.

Full integration details: [18_MST_Blockchain_Integration.md](18_MST_Blockchain_Integration.md).
