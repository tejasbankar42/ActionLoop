import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes import agents, analytics, approvals, audit, auth, blockchain, documents, settings, workflows
from app.blockchain.transaction_service import AnchorWorker, requeue_unconfigured
from app.core.config import get_settings
from app.database.seed import seed
from app.database.session import Base, SessionLocal, engine
from app.services.audit_service import AuditImmutableError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("actionloop")

POSTGRES_AUDIT_GUARD = """
CREATE OR REPLACE FUNCTION actionloop_block_audit_mutation() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'audit_events is append-only'; END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events;
CREATE TRIGGER audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events
FOR EACH ROW EXECUTE FUNCTION actionloop_block_audit_mutation();
"""


def init_db() -> None:
    import app.models  # noqa: F401 - register tables

    Base.metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text(POSTGRES_AUDIT_GUARD))


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    s.storage_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    if s.seed_on_startup:
        with SessionLocal() as db:
            seed(db)
            requeue_unconfigured(db)
    worker = AnchorWorker()
    worker.start()
    log.info("ActionLoop started (demo_mode=%s, db=%s, network=%s)", s.demo_mode, engine.dialect.name, s.network["name"])
    yield
    worker.stop()


app = FastAPI(
    title="ActionLoop API",
    version="1.0.0",
    description="AI-powered multi-agent workflow automation with human approval, a SHA-256 hash-chained audit "
                "log and MST Blockchain anchoring. Authenticate via POST /api/auth/login and use the bearer token.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
for r in (auth, documents, workflows, agents, approvals, audit, analytics, blockchain, settings):
    app.include_router(r.router)


@app.exception_handler(AuditImmutableError)
async def audit_immutable(_: Request, exc: AuditImmutableError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok"}
