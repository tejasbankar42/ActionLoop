"""End-to-end anchoring check against a real EVM chain.

Local (Hardhat node, `npx hardhat node` in contracts/):
    python scripts/e2e_chain_check.py --local

MST Testnet (uses AUDIT_REGISTRY_ADDRESS / MST_RELAYER_PRIVATE_KEY from backend/.env):
    python scripts/e2e_chain_check.py --testnet

Runs invoice scenario A through the real LangGraph workflow, approves it, then waits until the
relayer's anchor transactions are mined AND the contract confirms the hashes. Prints tx hashes.
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Hardhat's first default dev account. Publicly documented, only valid on a local dev chain.
HARDHAT_DEV_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--local", action="store_true")
    g.add_argument("--testnet", action="store_true")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="actionloop-e2e-"))
    os.environ.update({"DATABASE_URL": f"sqlite:///{(tmp / 'e2e.db').as_posix()}", "STORAGE_DIR": str(tmp / "storage"),
                       "DEMO_STEP_DELAY_MS": "0", "ANTHROPIC_API_KEY": ""})

    if args.local:
        os.environ.update({"MST_NETWORK": "testnet", "MST_RPC_URL": "http://127.0.0.1:8545", "MST_CHAIN_ID": "31337",
                           "MST_EXPLORER_URL": "http://localhost", "MST_RELAYER_PRIVATE_KEY": HARDHAT_DEV_KEY})
        from mst_blockchain_sdk import Provider, Signer

        abi_doc = json.loads((ROOT / "app/blockchain/abi/ActionLoopAuditRegistry.json").read_text())
        signer = Signer(HARDHAT_DEV_KEY, Provider("http://127.0.0.1:8545"))
        tx = signer.deploy(abi_doc["abi"], abi_doc["bytecode"], ["0x0000000000000000000000000000000000000000"])
        receipt = signer.provider.wait_for_transaction(tx)
        os.environ["AUDIT_REGISTRY_ADDRESS"] = receipt["contractAddress"]
        print(f"[local] deployed registry at {receipt['contractAddress']} (tx {tx})")

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        st = c.get("/api/system/status").json()["blockchain"]
        print(f"network={st['network']} chain={st['chain_id']} contract={st['contract_address']} relayer={st['relayer_address']}")
        tok = c.post("/api/auth/login", json={"email": "reviewer@actionloop.demo", "password": "ActionLoop@2026"}).json()
        h = {"Authorization": f"Bearer {tok['access_token']}"}
        doc = next(d for d in c.get("/api/documents", headers=h).json() if d["filename"].startswith("A_invoice"))
        wf_id = c.post("/api/workflows/start", json={"document_id": doc["id"]}, headers=h).json()["id"]
        for _ in range(100):
            wf = c.get(f"/api/workflows/{wf_id}", headers=h).json()
            if wf["status"] == "awaiting_approval":
                break
            time.sleep(0.2)
        c.post(f"/api/approvals/{wf['approvals'][0]['id']}/decision",
               json={"decision": "approve", "comment": "e2e chain check"}, headers=h)
        deadline = time.time() + (60 if args.local else 300)
        while time.time() < deadline:
            anchors = [a for a in c.get("/api/blockchain/anchors", headers=h).json() if a["workflow_id"] == wf_id]
            if len(anchors) >= 2 and all(a["status"] in ("confirmed", "failed") for a in anchors):
                break
            time.sleep(2)
        ok = True
        for a in anchors:
            print(f"  {a['event_type']:<20} {a['status']:<10} tx={a['tx_hash']} block={a['block_number']} err={a['last_error']}")
            v = c.get(f"/api/audit/events/{a['audit_event_id']}/verify", headers=h).json()
            print(f"     off-chain valid={v['offchain']['valid']}  on-chain={v['onchain']['status']}")
            ok &= a["status"] == "confirmed" and v["onchain"]["status"] == "verified" and v["offchain"]["valid"]
        # Idempotency: re-processing a confirmed anchor must not send a second transaction.
        again = c.post(f"/api/blockchain/anchors/{anchors[0]['id']}/process", headers=h).json()
        ok &= again["tx_hash"] == anchors[0]["tx_hash"]
        print("RESULT:", "PASS" if ok else "FAIL")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
