# 05 · Technology Stack

| Concern | Choice | Version tested |
|---|---|---|
| Frontend framework | Next.js App Router + TypeScript | 15.5 / TS 5 |
| Styling | Tailwind CSS 4, design tokens in `globals.css`, self-hosted fonts (Plus Jakarta Sans, JetBrains Mono) | 4.x |
| Components | Radix primitives in shadcn/ui style (`components/ui`) | — |
| Motion / icons / charts | Framer Motion, Lucide, Recharts | 14 / 1.x / 3.x |
| Workflow graph | React Flow (`@xyflow/react`) | 12 |
| Wallet / chain | ethers v6 (EIP-1193 BrowserProvider, JsonRpcProvider) | 6.17 |
| API | FastAPI, Pydantic v2, Uvicorn | 0.162 / 2.14 |
| ORM / DB | SQLAlchemy 2, psycopg 3, PostgreSQL 16 (Docker) or SQLite | 2.1 |
| Auth | PyJWT (HS256), bcrypt | — |
| Orchestration | LangGraph | 1.2 |
| LLM | Anthropic Python SDK, model `claude-opus-5-5` (configurable) | 2.3 |
| Documents | pypdf (text layer), Pillow, ReportLab (sample generation) | — |
| Smart contract | Solidity 0.8.24 (optimizer 200, EVM `paris`), Hardhat 2.28, hardhat-toolbox | — |
| Chain client | `mst-sdk-python` 1.0.1 (Provider/Signer) over web3.py 8 + eth-account | — |
| Infra | Docker Compose (postgres, backend, frontend) | — |

`paris` is used as EVM target to avoid relying on the `PUSH0` opcode, since MST's docs don't state Shanghai support.
