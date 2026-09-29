"""
Integration tests run in CI against a real running instance of the app
(started via Docker in the CI workflow) -- these hit actual HTTP
endpoints, not mocks. Some tests need GROQ_API_KEY to be set as a
repository secret to fully exercise the chat endpoint; the rest
(health check, access control) work without it.
"""
import os
import requests

BASE = os.environ.get("APP_BASE_URL", "http://localhost:8000")


def test_health():
    r = requests.get(f"{BASE}/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_dashboard_blocks_support_agent():
    r = requests.get(f"{BASE}/api/insights",
                      headers={"X-User-Role": "support_agent", "X-User-Name": "ci-test"})
    assert r.status_code == 403


def test_dashboard_allows_ops_manager():
    r = requests.get(f"{BASE}/api/insights",
                      headers={"X-User-Role": "ops_manager", "X-User-Name": "ci-test"})
    assert r.status_code == 200
    body = r.json()
    assert "sla_risk" in body and "clusters" in body and "order_anomalies" in body


def test_chat_rejects_invalid_role():
    # The role field is Pydantic-validated against a fixed set of roles
    # before the request body is even processed, so an unknown role is
    # caught as a 422 schema validation error -- earlier and stricter
    # than a manual 403 check would be.
    r = requests.post(f"{BASE}/api/chat",
        headers={"X-User-Role": "nonexistent_role", "X-User-Name": "ci-test"},
        json={"message": "hello", "session_id": "ci-test-1",
              "user": {"user_id": "ci-test", "role": "nonexistent_role", "name": "ci-test"}})
    assert r.status_code == 422
