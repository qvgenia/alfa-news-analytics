
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.clients.service import get_client_profile
from app.db.base import Base
from app.db.models import ClientProfileModel, CounterpartyModel


def make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_get_client_profile_returns_counterparties():
    db = make_session()
    try:
        profile = ClientProfileModel(
            client_id="TEST_CLIENT",
            industry_code="62.01",
            industry_name="Разработка ПО",
            region="Москва",
            city="Москва",
            revenue_rub=Decimal("18000000000"),
            products=["RKO", "LOA"],
            fts_countries=["Китай", "Казахстан"],
            related_entities=["TEST_ENTITY_1"],
            group_id="GROUP_1",
        )

        profile.counterparties.append(
            CounterpartyModel(
                counterparty_client_id="TEST_CP",
                industry_code="46.90",
                industry_name="Оптовая торговля",
                region="Москва",
                direction="outgoing",
                pay_amt=Decimal("1000"),
                pay_cnt=2,
            )
        )

        db.add(profile)
        db.commit()

        result = get_client_profile("TEST_CLIENT", db)

        assert result is not None
        assert result.client_id == "TEST_CLIENT"
        assert result.industry_code == "62.01"
        assert result.industry_name == "Разработка ПО"
        assert result.region == "Москва"
        assert result.city == "Москва"
        assert result.revenue_rub == Decimal("18000000000")
        assert result.products == ["RKO", "LOA"]
        assert result.group_ids == ["GROUP_1"]
        assert result.fts_countries == ["Китай", "Казахстан"]
        assert result.related_entities == ["TEST_ENTITY_1"]

        assert len(result.top_counterparties) == 1

        counterparty = result.top_counterparties[0]
        assert counterparty.client_id == "TEST_CP"
        assert counterparty.industry_code == "46.90"
        assert counterparty.industry_name == "Оптовая торговля"
        assert counterparty.region == "Москва"
        assert counterparty.direction == "outgoing"
        assert counterparty.pay_amt == Decimal("1000")
        assert counterparty.pay_cnt == 2

    finally:
        db.close()


def test_get_client_profile_returns_none_for_unknown_client():
    db = make_session()
    try:
        result = get_client_profile("UNKNOWN", db)
        assert result is None
    finally:
        db.close()
