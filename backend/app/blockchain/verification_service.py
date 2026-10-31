"""Two independent checks shown side by side in the UI:

OFF-CHAIN AUDIT     the stored hash chain recomputes correctly up to this event
ON-CHAIN VERIFICATION  the contract on MST Blockchain reports this exact hash as anchored,
                       with the same workflow-id hash and event type
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.blockchain import contract_service as cs
from app.blockchain import mst_client
from app.blockchain.network_config import (
    contract_address,
    deployment_record,
    explorer_address,
    explorer_tx,
    load_abi,
    network,
)
from app.core.config import get_settings
from app.models import AuditEvent, BlockchainAnchor
from app.services import audit_service


def network_status() -> dict:
    net = network()
    s = get_settings()
    out = {
        "network": net,
        "contract_address": contract_address(),
        "contract_explorer_url": explorer_address(contract_address()),
        "abi_loaded": bool(load_abi()),
        "deployment": deployment_record(),
        "relayer_address": mst_client.relayer_address(),
        "relayer_configured": bool(s.mst_relayer_private_key),
        "auto_anchor": s.blockchain_auto_anchor,
        "anchor_event_types": sorted(s.anchor_types),
        "rpc_reachable": False,
        "chain_id_matches": False,
        "contract_code_present": False,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        w3 = mst_client.get_provider().web3
        chain_id = w3.eth.chain_id
        out["rpc_reachable"] = True
        out["rpc_chain_id"] = chain_id
        out["chain_id_matches"] = chain_id == net["chain_id"]
        out["latest_block"] = w3.eth.block_number
        if out["relayer_address"]:
            out["relayer_balance_wei"] = str(w3.eth.get_balance(out["relayer_address"]))
        if contract_address():
            code = w3.eth.get_code(contract_address())
            out["contract_code_present"] = len(code) > 0
            if out["contract_code_present"] and out["abi_loaded"]:
                out["contract"] = cs.contract_summary()
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"[:500]
    return out


def verify_event(db: Session, ev: AuditEvent) -> dict:
    off = audit_service.verify_single(db, ev)
    offchain = {
        "valid": off["valid"],
        "checked_events": off["checked"],
        "broken": off["broken"],
        "event_hash": ev.hash,
        "previous_hash": ev.previous_hash,
    }
    anchor = db.execute(select(BlockchainAnchor).where(
        BlockchainAnchor.audit_event_id == ev.id,
        BlockchainAnchor.chain_id == network()["chain_id"],
    )).scalar_one_or_none()

    onchain = {
        "status": "not_anchored",
        "message": "This event has not been submitted to MST Blockchain.",
        "anchor": anchor_dict(anchor) if anchor else None,
        "record": None,
    }
    if not cs.is_configured():
        onchain.update(status="not_configured",
                       message="No ActionLoop audit registry is configured for this network.")
        return {"event_id": ev.id, "offchain": offchain, "onchain": onchain}
    try:
        rec = cs.get_record(ev.hash)
    except Exception as exc:
        onchain.update(status="unavailable", message=f"Could not reach MST RPC: {exc}"[:300])
        return {"event_id": ev.id, "offchain": offchain, "onchain": onchain}

    if rec is None:
        if anchor and anchor.status == "submitted":
            onchain.update(status="pending", message="Transaction submitted; waiting for confirmation.")
        elif anchor and anchor.status == "failed":
            onchain.update(status="failed", message=anchor.last_error or "Anchoring failed.")
        elif anchor:
            onchain.update(status="queued", message="Queued for anchoring; not yet on-chain.")
        return {"event_id": ev.id, "offchain": offchain, "onchain": onchain}

    expected_wf = cs.workflow_id_hash(ev.workflow_id)
    matches = rec["workflow_id_hash"].lower() == expected_wf.lower() and rec["event_type"] == ev.event_type
    onchain.update(
        status="verified" if matches else "mismatch",
        message=("Hash found in the MST audit registry with matching workflow and event type."
                 if matches else "Hash is on-chain but its metadata does not match this event."),
        record=rec,
    )
    return {"event_id": ev.id, "offchain": offchain, "onchain": onchain}


def anchor_dict(a: BlockchainAnchor) -> dict:
    return {
        "id": a.id,
        "audit_event_id": a.audit_event_id,
        "workflow_id": a.workflow_id,
        "event_hash": a.event_hash,
        "workflow_id_hash": a.workflow_id_hash,
        "event_type": a.event_type,
        "network": a.network,
        "chain_id": a.chain_id,
        "contract_address": a.contract_address,
        "status": a.status,
        "submitted_via": a.submitted_via,
        "submitter_address": a.submitter_address,
        "tx_hash": a.tx_hash,
        "tx_explorer_url": explorer_tx(a.tx_hash) if a.status in ("submitted", "confirmed", "failed") else None,
        "block_number": a.block_number,
        "gas_used": a.gas_used,
        "attempts": a.attempts,
        "last_error": a.last_error,
        "onchain_verified_at": a.onchain_verified_at.isoformat() if a.onchain_verified_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
