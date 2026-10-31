"""Append-only, SHA-256 hash-chained audit log.

current_hash = SHA256(previous_hash + canonical_event_data)

The first event links to GENESIS_HASH. Any edit to a stored row (or a deleted/reordered row)
changes the recomputed hash and is reported by `verify_chain`.
"""

import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone

from sqlalchemy import event as sa_event
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditEvent

GENESIS_HASH = "0" * 64
_append_lock = threading.Lock()


class AuditImmutableError(RuntimeError):
    pass


@sa_event.listens_for(AuditEvent, "before_update")
def _block_update(mapper, connection, target):  # pragma: no cover - exercised in tests via raise
    raise AuditImmutableError("Audit events are append-only and cannot be modified")


@sa_event.listens_for(AuditEvent, "before_delete")
def _block_delete(mapper, connection, target):
    raise AuditImmutableError("Audit events are append-only and cannot be deleted")


def _iso(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat(timespec="microseconds")


def canonical_event_data(ev: AuditEvent | dict) -> str:
    """Deterministic JSON of the fields covered by the hash (sorted keys, no whitespace)."""
    get = ev.get if isinstance(ev, dict) else lambda k: getattr(ev, k)
    data = {
        "id": get("id"),
        "sequence": get("sequence"),
        "workflow_id": get("workflow_id"),
        "timestamp": _iso(get("timestamp")),
        "user_id": get("user_id"),
        "actor": get("actor"),
        "agent": get("agent"),
        "event_type": get("event_type"),
        "description": get("description"),
        "payload": get("payload") or {},
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def compute_hash(previous_hash: str, canonical: str) -> str:
    return hashlib.sha256((previous_hash + canonical).encode("utf-8")).hexdigest()


def append_event(
    db: Session,
    *,
    event_type: str,
    description: str,
    actor: str,
    workflow_id: str | None = None,
    user_id: str | None = None,
    agent: str | None = None,
    payload: dict | None = None,
    timestamp: datetime | None = None,
    commit: bool = True,
) -> AuditEvent:
    """Append one event to the chain. Serialized so sequence numbers and links never fork."""
    with _append_lock:
        last = db.execute(select(AuditEvent).order_by(AuditEvent.sequence.desc()).limit(1)).scalar_one_or_none()
        prev_hash = last.hash if last else GENESIS_HASH
        seq = (last.sequence + 1) if last else 1
        ts = timestamp or datetime.now(timezone.utc)
        if last and _iso(ts) < _iso(last.timestamp):
            ts = last.timestamp  # keep chain chronologically monotonic
        ev = AuditEvent(
            id=str(uuid.uuid4()),
            sequence=seq,
            workflow_id=workflow_id,
            timestamp=ts,
            user_id=user_id,
            actor=actor,
            agent=agent,
            event_type=event_type,
            description=description,
            payload=payload or {},
            previous_hash=prev_hash,
        )
        ev.hash = compute_hash(prev_hash, canonical_event_data(ev))
        db.add(ev)
        db.flush()
        _after_append(db, ev)  # anchor row (if any) commits atomically with the event
        if commit:
            db.commit()
    return ev


def _after_append(db: Session, ev: AuditEvent) -> None:
    # Imported lazily: blockchain layer depends on audit, not the other way round.
    from app.blockchain.transaction_service import maybe_queue_anchor

    maybe_queue_anchor(db, ev)


def verify_chain(rows: list[AuditEvent] | list[dict], tamper: dict | None = None) -> dict:
    """Recompute every link. `tamper` = {"event_id": ..., "field": ..., "value": ...} simulates an
    edit on an in-memory copy only (used by the demo; the database is never modified)."""
    prev = GENESIS_HASH
    checked = 0
    broken = []
    for row in rows:
        data = row if isinstance(row, dict) else {c: getattr(row, c) for c in (
            "id", "sequence", "workflow_id", "timestamp", "user_id", "actor", "agent",
            "event_type", "description", "payload", "previous_hash", "hash")}
        data = dict(data)
        if tamper and data["id"] == tamper.get("event_id"):
            data[tamper.get("field", "description")] = tamper.get("value")
        expected_hash = compute_hash(prev, canonical_event_data(data))
        problems = []
        if data["previous_hash"] != prev:
            problems.append("previous_hash does not match the preceding event's hash")
        if data["hash"] != expected_hash:
            problems.append("stored hash does not match recomputed SHA-256 of the event data")
        if problems:
            broken.append({
                "event_id": data["id"],
                "sequence": data["sequence"],
                "problems": problems,
                "stored_hash": data["hash"],
                "recomputed_hash": expected_hash,
            })
        prev = data["hash"]
        checked += 1
    return {
        "valid": not broken,
        "checked": checked,
        "broken": broken,
        "genesis_hash": GENESIS_HASH,
        "head_hash": prev if checked else GENESIS_HASH,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "simulated_tamper": bool(tamper),
    }


def all_events(db: Session) -> list[AuditEvent]:
    return list(db.execute(select(AuditEvent).order_by(AuditEvent.sequence)).scalars())


def verify_single(db: Session, event: AuditEvent) -> dict:
    """Verify the chain prefix up to and including `event` (its hash commits to all earlier events)."""
    rows = list(db.execute(
        select(AuditEvent).where(AuditEvent.sequence <= event.sequence).order_by(AuditEvent.sequence)
    ).scalars())
    return verify_chain(rows)


def count_events(db: Session) -> int:
    return db.scalar(select(func.count(AuditEvent.id))) or 0
