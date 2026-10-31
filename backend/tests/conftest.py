import os
import tempfile
import time
from pathlib import Path

import pytest

_tmp = Path(tempfile.mkdtemp(prefix="actionloop-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["STORAGE_DIR"] = str(_tmp / "storage")
os.environ["DEMO_STEP_DELAY_MS"] = "0"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["MST_RELAYER_PRIVATE_KEY"] = ""
os.environ["AUDIT_REGISTRY_ADDRESS"] = ""
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-123"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PASSWORD = "ActionLoop@2026"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def login(client, email):
    r = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def reviewer(client):
    return login(client, "reviewer@actionloop.demo")


@pytest.fixture(scope="session")
def operator(client):
    return login(client, "operator@actionloop.demo")


@pytest.fixture(scope="session")
def viewer(client):
    return login(client, "viewer@actionloop.demo")


def sample_doc(client, headers, filename):
    docs = client.get("/api/documents", headers=headers).json()
    return next(d for d in docs if d["filename"] == filename)


def wait_for(client, headers, wf_id, statuses=("awaiting_approval", "completed", "failed", "needs_correction", "rejected"), timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        wf = client.get(f"/api/workflows/{wf_id}", headers=headers).json()
        if wf["status"] in statuses:
            return wf
        time.sleep(0.1)
    raise AssertionError(f"workflow {wf_id} stuck in {wf['status']}")


def run_sample(client, headers, filename):
    doc = sample_doc(client, headers, filename)
    r = client.post("/api/workflows/start", json={"document_id": doc["id"]}, headers=headers)
    assert r.status_code == 202, r.text
    return wait_for(client, headers, r.json()["id"])
