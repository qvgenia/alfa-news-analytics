
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app

from pydantic import ValidationError
from app.contracts import ClientProfile
import pytest


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def override_get_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def profile_payload(client_id="TEST_API_CLIENT"):
    return {
        "client_id": client_id,
        "industry_code": "62.01",
        "industry_name": "Разработка ПО",
        "region": "Москва",
        "city": "Москва",
        "revenue_rub": "150000000",
        "products": ["RKO", "LOAN"],
        "group_ids": ["GROUP_001"],
        "fts_countries": ["Россия"],
        "top_counterparties": [
            {
                "client_id": "COUNTERPARTY_001",
                "direction": "outgoing",
                "pay_amt": "2500000",
                "pay_cnt": 12,
                "industry_code": "62.01",
                "industry_name": "ИТ",
                "region": "Москва",
            }
        ],
        "related_entities": ["ИТ", "цифровизация"],
    }


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module():
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_create_client_profile():
    response = client.post("/clients", json=profile_payload())

    assert response.status_code == 201
    assert response.json()["client_id"] == "TEST_API_CLIENT"
    assert response.json()["top_counterparties"][0]["client_id"] == "COUNTERPARTY_001"


def test_get_client_profile():
    client.post("/clients", json=profile_payload())

    response = client.get("/clients/TEST_API_CLIENT")

    assert response.status_code == 200
    assert response.json()["industry_code"] == "62.01"
    assert response.json()["products"] == ["RKO", "LOAN"]


def test_update_client_profile():
    client.post("/clients", json=profile_payload())

    updated = profile_payload()
    updated["industry_name"] = "Обновлённая отрасль"
    updated["revenue_rub"] = "200000000"

    response = client.put("/clients/TEST_API_CLIENT", json=updated)

    assert response.status_code == 200
    assert response.json()["industry_name"] == "Обновлённая отрасль"
    assert Decimal(response.json()["revenue_rub"]) == Decimal("200000000")


def test_get_unknown_client_returns_404():
    response = client.get("/clients/UNKNOWN_API_CLIENT")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Профиль клиента 'UNKNOWN_API_CLIENT' не найден"
    )


def test_create_duplicate_client_returns_409():
    payload = profile_payload()
    client.post("/clients", json=payload)

    response = client.post("/clients", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Профиль клиента 'TEST_API_CLIENT' уже существует"
    )


def test_update_unknown_client_returns_404():
    response = client.put(
        "/clients/UNKNOWN_API_CLIENT",
        json=profile_payload("UNKNOWN_API_CLIENT"),
    )

    assert response.status_code == 404


def test_update_client_id_mismatch_returns_422():
    response = client.put(
        "/clients/URL_CLIENT",
        json=profile_payload("BODY_CLIENT"),
    )

    assert response.status_code == 422

def test_update_client_profile_replaces_counterparties():
    client.post("/clients", json=profile_payload())

    updated = profile_payload()
    updated["top_counterparties"] = [
        {
            "client_id": "COUNTERPARTY_002",
            "direction": "incoming",
            "pay_amt": "500000",
            "pay_cnt": 3,
            "industry_code": "46.90",
            "industry_name": "Торговля",
            "region": "Санкт-Петербург",
        }
    ]

    response = client.put("/clients/TEST_API_CLIENT", json=updated)

    assert response.status_code == 200
    counterparties = response.json()["top_counterparties"]
    assert len(counterparties) == 1
    assert counterparties[0]["client_id"] == "COUNTERPARTY_002"


def test_update_client_profile_clears_optional_lists():
    client.post("/clients", json=profile_payload())

    updated = profile_payload()
    updated["products"] = []
    updated["fts_countries"] = []
    updated["related_entities"] = []
    updated["top_counterparties"] = []

    response = client.put("/clients/TEST_API_CLIENT", json=updated)

    assert response.status_code == 200
    result = response.json()
    assert result["products"] == []
    assert result["fts_countries"] == []
    assert result["related_entities"] == []
    assert result["top_counterparties"] == []

def test_client_profile_allows_zero_or_one_group():
    assert ClientProfile(client_id="client-1", group_ids=[]).group_ids == []
    assert ClientProfile(
        client_id="client-2",
        group_ids=["GROUP_001"],
    ).group_ids == ["GROUP_001"]


def test_client_profile_rejects_multiple_groups():
    with pytest.raises(ValidationError):
        ClientProfile(
            client_id="client-3",
            group_ids=["GROUP_001", "GROUP_002"],
        )