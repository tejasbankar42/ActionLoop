from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

MST_NETWORKS = {
    "testnet": {
        "name": "MST Testnet",
        "rpc_url": "https://testnetrpc.mstblockchain.com",
        "chain_id": 91562037,
        "symbol": "tMSTC",
        "explorer": "https://testnet.mstscan.com",
    },
    "mainnet": {
        "name": "MST Mainnet",
        "rpc_url": "https://mariorpc.mstblockchain.com",
        "chain_id": 4646,
        "symbol": "MSTC",
        "explorer": "https://mstscan.com",
    },
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    app_name: str = "ActionLoop"
    environment: str = "development"
    # PostgreSQL in Docker/production; SQLite fallback keeps local dev zero-setup.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'actionloop.db').as_posix()}"
    jwt_secret: str = "dev-only-insecure-jwt-secret-change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    storage_dir: Path = BACKEND_DIR / "storage"
    max_upload_mb: int = 10
    seed_on_startup: bool = True

    # AI provider. Empty key => DEMO MODE (deterministic parsers, no paid API).
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5-5"
    low_confidence_threshold: float = 0.75
    demo_step_delay_ms: int = 600

    # MST Blockchain
    mst_network: str = "testnet"
    mst_rpc_url: str = ""
    mst_chain_id: int = 0
    mst_explorer_url: str = ""
    audit_registry_address: str = ""
    # Backend relayer key for automatic anchoring. Lives only in backend/.env.
    mst_relayer_private_key: str = Field(default="", repr=False)
    blockchain_auto_anchor: bool = True
    anchor_event_types: str = "APPROVAL_DECISION,WORKFLOW_COMPLETED,WORKFLOW_REJECTED,VALIDATION_BLOCKED"
    anchor_receipt_timeout_s: int = 90

    @property
    def demo_mode(self) -> bool:
        return not self.anthropic_api_key

    @property
    def network(self) -> dict:
        base = dict(MST_NETWORKS.get(self.mst_network, MST_NETWORKS["testnet"]))
        if self.mst_rpc_url:
            base["rpc_url"] = self.mst_rpc_url
        if self.mst_chain_id:
            base["chain_id"] = self.mst_chain_id
        if self.mst_explorer_url:
            base["explorer"] = self.mst_explorer_url.rstrip("/")
        base["key"] = self.mst_network
        return base

    @property
    def anchor_types(self) -> set[str]:
        return {t.strip() for t in self.anchor_event_types.split(",") if t.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
