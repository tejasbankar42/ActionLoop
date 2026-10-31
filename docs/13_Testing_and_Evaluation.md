# 13 · Testing and Evaluation

## How to run

```bash
cd backend && .venv/Scripts/python -m pytest
cd contracts && npx hardhat test
cd contracts && npx hardhat node                                          # terminal 1
cd backend && .venv/Scripts/python scripts/e2e_chain_check.py --local     # terminal 2
cd frontend && npx tsc --noEmit
```

## Results (31 Oct 2026, Windows 11, Python 3.14, Node 20)

| Suite | Result |
|---|---|
| Backend pytest (`tests/`) | **28 passed** |
| Hardhat contract tests | **10 passing** |
| End-to-end chain check on a local Hardhat EVM | **PASS** — deployed via MST SDK signer; `APPROVAL_DECISION` and `WORKFLOW_COMPLETED` anchored by the relayer, both receipts verified, `isAnchored` true, off-chain chain valid, re-processing sent no duplicate tx |
| Frontend TypeScript check | **0 errors** |
| Manual browser check | Landing, login, dashboard, documents (upload/start/live stages), studio graph, approvals verified in the in-app browser |

### Backend coverage (by test)

Upload validation (type, magic bytes, size) · auth failures (401) and role checks (403) · 404/422 handling · scenario A approve→complete · scenario B missing field · scenario C duplicate blocked · scenario D unreadable values never invented + approve with corrections → completed · scenario E complaint routing · rejection closes without executing · duplicate workflow submission → 409 · image in DEMO MODE yields no fields · audit chain valid & expected events present · simulated tamper detected without DB change · ORM blocks audit updates · hash formula matches spec · altered/deleted records detected · canonical JSON key-order independence · extraction schema/normalisation · planner requires approval for payments · on-chain encoding helpers · analytics + CSV · blockchain reports `not_configured` honestly (no fake tx hashes).

### Contract coverage

Deployment roles · anchor + event + stored record · duplicate rejection · unauthorized submitter · zero-hash rejection · unknown hash → false · owner-only submitter management · pause · pagination bounds · two-step ownership.

## Not yet verified

- MST Testnet deployment and live testnet anchoring — see [18_MST_Blockchain_Integration.md](18_MST_Blockchain_Integration.md) for current status.
- BridgeKey extension specifically (implemented against EIP-1193/EIP-6963; tested only by code review/typecheck here).
- Live Claude extraction (no API key in the build environment).
- Docker/PostgreSQL run.
