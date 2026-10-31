# 12 · Security and Reliability

| Control | Implementation |
|---|---|
| Authentication | JWT (HS256, `JWT_SECRET` from env, 12 h expiry) |
| Password storage | bcrypt (cost 10) |
| Authorization | Role ranks viewer < operator < reviewer < admin enforced per endpoint (`require_role`) |
| Tenant isolation | Documents, workflows and approvals filtered by the user's organization |
| Input validation | Pydantic schemas; regex-validated tx hashes and addresses; date-range checks |
| Upload safety | Allow-listed MIME types + extension + magic-byte check, size limit, server-generated storage names, path-traversal guard, `X-Content-Type-Options: nosniff` |
| Secrets | `.env` files git-ignored; `.env.example` templates only; no secrets returned to the browser (`/api/blockchain/config` and `/api/system/status` are secret-free) |
| Audit protection | Append-only (ORM + Postgres trigger), hash chain, on-chain anchors |
| Duplicate submissions | Lock + active-workflow check → 409; duplicate decisions → 409 |
| Duplicate anchoring | Unique (chain, event hash); `isAnchored` pre-check; contract reverts `AlreadyAnchored` |
| Blockchain safety | Chain ID from RPC is checked before every write; success only after receipt + `isAnchored`; mainnet deploy requires typed confirmation |
| Wallet | Keys stay in BridgeKey; the app only requests signatures; backend re-verifies every wallet-submitted tx (target contract, receipt status, emitted log) |
| Errors | Uniform JSON errors; unhandled exceptions logged and returned as 500 without internals |
| Logging | Python logging for workflows, anchoring and unhandled errors; no keys are logged |

### Smart-contract security review

- Access control: `onlyOwner` for submitter management/pause; `onlySubmitter` for anchoring.
- Two-step ownership transfer (prevents transfer to a mistyped address).
- No ETH handling, no external calls, no `delegatecall`/`selfdestruct` → no reentrancy surface.
- Bounded pagination (`MAX_PAGE_SIZE = 100`).
- Custom errors for cheaper reverts; zero-hash rejection; duplicate rejection.
- Not audited by a third party.

### Known limitations

- Demo credentials are public; change them for anything beyond a demo.
- The relayer key lives in `backend/.env` on the server. For production, move it to a KMS/HSM.
- SQLite fallback is for local development only.
