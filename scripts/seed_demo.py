from decimal import Decimal

from sqlalchemy import select

from app.db.models import ClientProfileModel, CounterpartyModel
from app.db.session import SessionLocal


def seed_demo() -> None:
    profiles = [
        {
            "client_id": "DEMO_TECH_001",
            "industry_code": "62.01",
            "industry_name": "Разработка компьютерного программного обеспечения",
            "region": "Москва",
            "revenue_rub": Decimal("18000000000"),
            "products": ["RKO", "LOA"],
            "fts_countries": [],
            "related_entities": [],
            "group_id": "DEMO_GROUP_001",
            "counterparties": [
                {
                    "counterparty_client_id": "DEMO_CP_001",
                    "industry_code": "62.01",
                    "industry_name": "Разработка программного обеспечения",
                    "region": "Москва",
                    "direction": "outgoing",
                    "pay_amt": Decimal("15000000"),
                    "pay_cnt": 12,
                },
                {
                    "counterparty_client_id": "DEMO_CP_002",
                    "industry_code": "46.90",
                    "industry_name": "Оптовая торговля",
                    "region": "Санкт-Петербург",
                    "direction": "incoming",
                    "pay_amt": Decimal("8000000"),
                    "pay_cnt": 6,
                },
            ],
        },
        {
            "client_id": "DEMO_TRADE_001",
            "industry_code": "46.90",
            "industry_name": "Оптовая торговля",
            "region": "Санкт-Петербург",
            "revenue_rub": Decimal("20000000000"),
            "products": ["RKO", "FACTORING"],
            "fts_countries": ["CN", "TR"],
            "related_entities": [],
            "group_id": "DEMO_GROUP_002",
            "counterparties": [
                {
                    "counterparty_client_id": "DEMO_CP_003",
                    "industry_code": "46.90",
                    "industry_name": "Оптовая торговля",
                    "region": "Санкт-Петербург",
                    "direction": "incoming",
                    "pay_amt": Decimal("25000000"),
                    "pay_cnt": 20,
                },
            ],
        },
    ]

    with SessionLocal() as db:
        for data in profiles:
            counterparties = data.pop("counterparties")

            profile = db.get(ClientProfileModel, data["client_id"])
            if profile is None:
                profile = ClientProfileModel(**data)
                db.add(profile)
            else:
                for key, value in data.items():
                    setattr(profile, key, value)

            profile.counterparties.clear()
            for item in counterparties:
                profile.counterparties.append(CounterpartyModel(**item))

        db.commit()

    print("Демо-профили загружены.")


if __name__ == "__main__":
    seed_demo()