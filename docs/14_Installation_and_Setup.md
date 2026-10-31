# 14 · Installation and Setup

## Prerequisites

- Python 3.12+ (tested 3.14), Node.js 20+ (Hardhat 2.28 works on Node 20)
- Optional: Docker Desktop (PostgreSQL stack), BridgeKey browser extension

## Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set JWT_SECRET
uvicorn app.main:app --reload --port 8000
```

First start creates `backend/actionloop.db` (SQLite), seeds demo data and copies the sample documents from `samples/`. To reset: stop the server and delete `backend/actionloop.db` and `backend/storage/`.

To use PostgreSQL without Docker set `DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/actionloop`.

## Frontend

```bash
cd frontend
npm install
cp .env.example .env.local    # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                   # or: npm run build && npm start (faster for demos)
```

## Smart contract

```bash
cd contracts
npm install
cp .env.example .env          # DEPLOYER_PRIVATE_KEY = TESTNET key only
npx hardhat test
npm run deploy:testnet        # writes deployments/mstTestnet.json
node scripts/export-abi.js    # only if the contract changed
```

Restart the backend after deploying: it reads `contracts/deployments/mstTestnet.json` (or `AUDIT_REGISTRY_ADDRESS`) and moves `not_configured` anchors back into the queue.

## Docker

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

Services: `db` (Postgres 16), `backend` (:8000), `frontend` (:3000). The compose file mounts `samples/` and `contracts/deployments/` into the backend.

## Live AI mode

Set `ANTHROPIC_API_KEY` in `backend/.env`. The DEMO MODE badge disappears and the Extractor uses Claude for PDFs and images.
