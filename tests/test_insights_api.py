from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

DEMO_CLIENT = "DEMO_TECH_001"


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_insight_success():
    r = client.post(
        "/insights/generate",
        json={"client_id": DEMO_CLIENT, "question": "Почему новость важна?"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["client_id"] == DEMO_CLIENT
    assert body["insight"]["news_id"] == "demo-news-001"
    assert body["source_refs"]
    assert body["limitations"]


def test_unknown_client_returns_404():
    r = client.post(
        "/insights/generate",
        json={"client_id": "NO_SUCH_CLIENT", "question": "Вопрос"},
    )
    assert r.status_code == 404


def test_unknown_news_returns_404():
    r = client.post(
        "/insights/generate",
        json={
            "client_id": DEMO_CLIENT,
            "question": "Вопрос",
            "news_id": "no-such-news",
        },
    )
    assert r.status_code == 404


def test_empty_question_returns_422():
    r = client.post(
        "/insights/generate",
        json={"client_id": DEMO_CLIENT, "question": ""},
    )
    assert r.status_code == 422
