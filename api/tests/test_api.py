import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def add(client, company="Acme", title="Junior DevOps Engineer", source="LinkedIn"):
    r = client.post("/api/jobs", json={"company": company, "title": title, "source": source})
    assert r.status_code == 201
    return r.json()


def test_health(client):
    assert client.get("/healthz").json()["status"] == "ok"
    assert client.get("/readyz").json()["status"] == "ready"


def test_create_and_list(client):
    job = add(client)
    assert job["status"] == "Applied"
    jobs = client.get("/api/jobs").json()
    assert len(jobs) == 1 and jobs[0]["company"] == "Acme"


def test_validation(client):
    r = client.post("/api/jobs", json={"company": "", "title": "x"})
    assert r.status_code == 422


def test_update_status_and_filter(client):
    job = add(client)
    r = client.patch(f"/api/jobs/{job['id']}", json={"status": "Interview"})
    assert r.json()["status"] == "Interview"
    assert len(client.get("/api/jobs?status_filter=Interview").json()) == 1
    assert len(client.get("/api/jobs?status_filter=Applied").json()) == 0


def test_update_missing_returns_404(client):
    assert client.patch("/api/jobs/999", json={"status": "Offer"}).status_code == 404


def test_delete(client):
    job = add(client)
    assert client.delete(f"/api/jobs/{job['id']}").status_code == 204
    assert client.get("/api/jobs").json() == []


def test_stats(client):
    a = add(client, "A")
    add(client, "B", source="Bayt")
    add(client, "C")
    client.patch(f"/api/jobs/{a['id']}", json={"status": "Interview"})
    s = client.get("/api/stats").json()
    assert s["total"] == 3
    assert s["by_status"]["Interview"] == 1
    assert s["by_source"] == {"LinkedIn": 2, "Bayt": 1}
    assert s["response_rate"] == 33.3
    assert s["interview_rate"] == 33.3


def test_metrics_exposed(client):
    add(client)
    body = client.get("/metrics").text
    assert "jobtrack_jobs_created_total" in body
    assert "http_requests_total" in body
