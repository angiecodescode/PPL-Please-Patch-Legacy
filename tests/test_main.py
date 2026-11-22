from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import database
import main


def _fake_refactor_payload(refactored_code: str = "print('Hello Python 3')") -> dict:
    """Reusable structured AI payload for offline FastAPI tests."""
    return {
        "detected_language": "Python",
        "detected_framework": "Standard Library",
        "refactored_code": refactored_code,
        "summary": "Migrated Python 2 print statements to Python 3.",
        "changes_made": ["Replaced Python 2 print syntax with print()."],
        "dependency_migrations": ["Python 2 syntax -> Python 3.12+"],
        "breaking_changes_and_risks": ["Verify Python 3 runtime is installed."],
        "verification_steps": ["python -m py_compile snippet.py"],
        "confidence_score": 94,
    }


@pytest.fixture(autouse=True)
def isolated_test_env(tmp_path, monkeypatch):
    """Isolate SQLite, rate-limiter state, and API keys for each test."""
    test_db = tmp_path / "test_refactoring_history.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.init_db()

    with main._rate_limit_lock:
        main._rate_limit_hits.clear()

    monkeypatch.setenv("GEMINI_API_KEY", "test-fake-gemini-key")
    monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setattr(main, "RATE_LIMIT_MAX", 20)


def test_home_and_health_endpoints():
    with TestClient(main.app) as client:
        home_resp = client.get("/")
        assert home_resp.status_code == 200
        assert "PPL: Please Patch Legacy" in home_resp.text

        health_resp = client.get("/api/health")
        assert health_resp.status_code == 200
        body = health_resp.json()
        assert body["status"] == "ok"
        assert body["model"] == "gemini-4-hydrogen"
        assert body["api_key_configured"] is True
        assert body["database"] == "sqlite"


def test_rejects_empty_code_cleanly():
    with TestClient(main.app) as client:
        resp = client.post(
            "/api/refactor",
            json={"code": "   ", "filename": "empty.py"},
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()


def test_retries_503_then_succeeds_and_updates_history_analytics(monkeypatch):
    calls = {"count": 0}

    def fake_gemini_sync(*, api_key, model_name, code, filename, mode, target_stack, custom_instructions):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("503 UNAVAILABLE: This model is currently experiencing high demand.")
        return _fake_refactor_payload()

    monkeypatch.setattr(main, "_call_gemini_sync", fake_gemini_sync)
    monkeypatch.setattr(main.time, "sleep", lambda _: None)

    with TestClient(main.app) as client:
        resp = client.post(
            "/api/refactor",
            json={
                "code": "print 'hello'",
                "filename": "legacy.py",
                "mode": "full_autonomous",
                "target_stack": "Python 3.12+",
            },
        )
        assert resp.status_code == 200
        record = resp.json()["record"]
        assert calls["count"] == 2
        assert record["model_used"] == "gemini-4-hydrogen"
        assert record["confidence_score"] == 94

        history_resp = client.get("/api/history")
        assert history_resp.status_code == 200
        assert history_resp.json()["count"] == 1

        analytics_resp = client.get("/api/analytics")
        assert analytics_resp.status_code == 200
        assert analytics_resp.json()["analytics"]["total_runs"] == 1

        del_resp = client.delete(f"/api/history/{record['id']}")
        assert del_resp.status_code == 200


def test_falls_back_to_flash_when_primary_stays_503(monkeypatch):
    seen_models = []

    def fake_gemini_sync(*, api_key, model_name, code, filename, mode, target_stack, custom_instructions):
        seen_models.append(model_name)
        if model_name == "gemini-4-hydrogen":
            raise RuntimeError("503 UNAVAILABLE: model overloaded")
        return _fake_refactor_payload("print('fallback succeeded')")

    monkeypatch.setattr(main, "_call_gemini_sync", fake_gemini_sync)
    monkeypatch.setattr(main.time, "sleep", lambda _: None)

    with TestClient(main.app) as client:
        resp = client.post(
            "/api/refactor",
            json={"code": "print 'hi'", "filename": "app.py"},
        )
        assert resp.status_code == 200
        record = resp.json()["record"]
        assert "gemini-4-hydrogen" in seen_models
        assert record["model_used"] == main.GEMINI_FALLBACK_MODEL
        assert record["refactored_code"] == "print('fallback succeeded')"


def test_upload_endpoint_and_github_ssrf_guard(monkeypatch):
    monkeypatch.setattr(
        main,
        "_call_gemini_sync",
        lambda **kwargs: _fake_refactor_payload("fastapi>=0.115.0\n"),
    )

    with TestClient(main.app) as client:
        upload_resp = client.post(
            "/api/refactor/upload",
            files={"file": ("requirements.txt", b"Flask==0.12.2\n", "text/plain")},
            data={"mode": "migrate_dependencies", "target_stack": "Latest FastAPI"},
        )
        assert upload_resp.status_code == 200
        assert upload_resp.json()["record"]["filename"] == "requirements.txt"

        bad_github_resp = client.post(
            "/api/github/inspect",
            json={"url": "https://example.com/secret"},
        )
        assert bad_github_resp.status_code == 400


def test_rate_limiter_protects_public_endpoint(monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT_MAX", 2)
    monkeypatch.setattr(
        main,
        "_call_gemini_sync",
        lambda **kwargs: _fake_refactor_payload(),
    )

    with TestClient(main.app) as client:
        assert client.post("/api/refactor", json={"code": "x = 1", "filename": "a.py"}).status_code == 200
        assert client.post("/api/refactor", json={"code": "x = 2", "filename": "b.py"}).status_code == 200
        third = client.post("/api/refactor", json={"code": "x = 3", "filename": "c.py"})
        assert third.status_code == 429