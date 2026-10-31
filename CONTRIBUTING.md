# Contributing to ActionLoop

## Workflow

1. Branch from `main`: `git checkout -b feat/<short-name>`.
2. Keep backend, frontend and contract changes in focused commits.
3. Run the checks below before opening a pull request.

## Checks

```bash
cd backend && .venv/Scripts/python -m pytest
cd contracts && npx hardhat test
cd frontend && npx tsc --noEmit && npm run lint
```

If you change the contract, re-export the ABI so backend and frontend stay in sync:

```bash
cd contracts && npx hardhat compile && node scripts/export-abi.js
```

## Conventions

- Python: type hints, small modules, deterministic logic in `agents/validator.py` and `agents/action_planner.py`.
- Never let model output decide validity or approval.
- Audit events are append-only. Add new event types with `audit_service.append_event`; never update rows.
- Secrets only in `.env` files (git-ignored). Never commit private keys, API keys or JWT secrets.
- UI: use the design tokens in `frontend/src/app/globals.css`; reserve green/amber/red for status.
- Don't label simulated behaviour as real. External actions are simulated and must say so.

## Mainnet

Mainnet deployment uses real funds and requires typing `yes, deploy to mainnet` in the deploy script. Never automate it.
