import csv
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.clients.importer import import_payments, import_profiles
from app.db.base import Base
from app.db.models import ClientProfileModel, CounterpartyModel


def make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )()
    return engine, session


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


PROFILE_FIELDS = [
    "SYNTHETIC_U",
    "MAINOKVED_CODE",
    "MAINOKVED_NAME",
    "REGION",
    "CITY",
    "REVENUE_COMPANY",
    "GROUP_ID",
    "CL_PRODUCT_RKO_MARK",
    "FTS_COUNTRY_NAME",
]


def profile_row(client_id, revenue="1200", region="Москва"):
    return {
        "SYNTHETIC_U": client_id,
        "MAINOKVED_CODE": "62.01",
        "MAINOKVED_NAME": "Разработка ПО",
        "REGION": region,
        "CITY": "Москва",
        "REVENUE_COMPANY": revenue,
        "GROUP_ID": "GROUP_1",
        "CL_PRODUCT_RKO_MARK": "1",
        "FTS_COUNTRY_NAME": "Китай",
    }


PAYMENT_FIELDS = ["BENEFICIARY", "PAYER", "PAY_AMT", "PAY_CNT"]


def test_import_profiles_updates_existing_profile(tmp_path):
    engine, db = make_session()
    path = tmp_path / "profiles.csv"
    try:
        write_csv(path, PROFILE_FIELDS, [profile_row("CLIENT_1")])
        result = import_profiles(db, path)

        assert result == {"imported": 1, "rejected": 0}
        profile = db.get(ClientProfileModel, "CLIENT_1")
        assert profile is not None
        assert profile.revenue_rub == Decimal("1200")
        assert profile.products == ["RKO"]
        assert profile.fts_countries == ["Китай"]

        write_csv(
            path,
            PROFILE_FIELDS,
            [profile_row("CLIENT_1", revenue="2500", region="Татарстан")],
        )
        import_profiles(db, path)
        db.expire_all()

        profiles = db.scalars(select(ClientProfileModel)).all()
        assert len(profiles) == 1
        assert profiles[0].revenue_rub == Decimal("2500")
        assert profiles[0].region == "Татарстан"
    finally:
        db.close()
        engine.dispose()


def test_import_payments_aggregates_and_keeps_manual_links(tmp_path):
    engine, db = make_session()
    path = tmp_path / "payments.csv"
    try:
        db.add_all([
            ClientProfileModel(client_id="CLIENT_A", industry_code="62.01"),
            ClientProfileModel(
                client_id="CLIENT_B",
                industry_code="46.90",
                industry_name="Торговля",
                region="Москва",
            ),
        ])
        db.flush()
        db.add(CounterpartyModel(
            owner_client_id="CLIENT_A",
            counterparty_client_id="MANUAL_CP",
            direction="incoming",
            source="manual",
            pay_amt=Decimal("7"),
            pay_cnt=1,
        ))
        db.commit()

        write_csv(path, PAYMENT_FIELDS, [
            {
                "BENEFICIARY": "CLIENT_A",
                "PAYER": "CLIENT_B",
                "PAY_AMT": "10",
                "PAY_CNT": "2",
            },
            {
                "BENEFICIARY": "CLIENT_A",
                "PAYER": "CLIENT_B",
                "PAY_AMT": "15",
                "PAY_CNT": "3",
            },
        ])

        result = import_payments(db, path, chunksize=1)

        assert result == {
            "rows_read": 2,
            "counterparty_links": 2,
            "rejected": 0,
        }

        links = db.scalars(select(CounterpartyModel)).all()
        manual = [link for link in links if link.source == "manual"]
        imported = [link for link in links if link.source == "payments_csv"]

        assert len(manual) == 1
        assert manual[0].counterparty_client_id == "MANUAL_CP"
        assert len(imported) == 2

        incoming = next(link for link in imported if link.direction == "incoming")
        outgoing = next(link for link in imported if link.direction == "outgoing")
        assert incoming.owner_client_id == "CLIENT_A"
        assert incoming.pay_amt == Decimal("25")
        assert incoming.pay_cnt == 5
        assert incoming.industry_code == "46.90"
        assert incoming.region == "Москва"
        assert outgoing.owner_client_id == "CLIENT_B"
        assert outgoing.pay_amt == Decimal("25")
        assert outgoing.pay_cnt == 5
    finally:
        db.close()
        engine.dispose()


def test_reimport_payments_replaces_only_imported_links(tmp_path):
    engine, db = make_session()
    path = tmp_path / "payments.csv"
    try:
        db.add(ClientProfileModel(client_id="CLIENT_A"))
        db.commit()

        db.add(CounterpartyModel(
            owner_client_id="CLIENT_A",
            counterparty_client_id="MANUAL_CP",
            direction="incoming",
            source="manual",
            pay_amt=Decimal("9"),
            pay_cnt=1,
        ))
        db.commit()

        write_csv(path, PAYMENT_FIELDS, [{
            "BENEFICIARY": "CLIENT_A",
            "PAYER": "UNKNOWN_CP",
            "PAY_AMT": "12",
            "PAY_CNT": "2",
        }])

        import_payments(db, path)
        import_payments(db, path)

        links = db.scalars(select(CounterpartyModel)).all()
        manual = [link for link in links if link.source == "manual"]
        imported = [link for link in links if link.source == "payments_csv"]

        assert len(manual) == 1
        assert manual[0].pay_amt == Decimal("9")
        assert len(imported) == 1
        assert imported[0].counterparty_client_id == "UNKNOWN_CP"
        assert imported[0].industry_code is None
        assert imported[0].industry_name is None
        assert imported[0].region is None
    finally:
        db.close()
        engine.dispose()


def test_import_profiles_rejects_missing_client_id(tmp_path):
    engine, db = make_session()
    path = tmp_path / "profiles.csv"
    try:
        write_csv(path, PROFILE_FIELDS, [profile_row(" ")])
        result = import_profiles(db, path)

        assert result == {"imported": 0, "rejected": 1}
        assert db.scalars(select(ClientProfileModel)).all() == []
    finally:
        db.close()
        engine.dispose()
