import os

os.environ.setdefault("POSTGRES_PASSWORD", "test_password")

from fastapi.testclient import TestClient

from app.contracts import ClientProfile
from app.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_feed_returns_ranked_news(monkeypatch):
    profile = ClientProfile(client_id="TEST_CLIENT")

    def fake_get_client_profile(client_id, db):
        assert client_id == "TEST_CLIENT"
        return profile

    expected_news = []

    def fake_get_ranked_news_feed(client, limit_per_source):
        assert client is profile
        assert limit_per_source == 20
        return expected_news

    def fake_get_db():
        yield object()

    monkeypatch.setattr("app.main.get_client_profile", fake_get_client_profile)
    monkeypatch.setattr("app.main.get_ranked_news_feed", fake_get_ranked_news_feed)
    monkeypatch.setattr("app.main.get_db", fake_get_db)

    response = client.get(
        "/feed",
        params={
            "client_id": "TEST_CLIENT",
            "limit_per_source": 20,
        },
    )

    assert response.status_code == 200
    assert response.json() == []


def test_feed_returns_404_for_unknown_client(monkeypatch):
    def fake_get_client_profile(client_id, db):
        return None

    def fake_get_db():
        yield object()

    monkeypatch.setattr("app.main.get_client_profile", fake_get_client_profile)
    monkeypatch.setattr("app.main.get_db", fake_get_db)

    response = client.get(
        "/feed",
        params={"client_id": "UNKNOWN"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Профиль клиента 'UNKNOWN' не найден"
