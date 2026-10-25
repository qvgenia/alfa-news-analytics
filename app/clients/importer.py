
"""Repeatable CSV import for client profiles and payment counterparties."""

import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import ClientProfileModel, CounterpartyModel


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _revenue(value: str | None) -> Decimal | None:
    value = _clean(value)
    if not value or value == "1000":
        return None
    try:
        amount = Decimal(value.replace(" ", "").replace(",", "."))
        return amount if amount >= 0 else None
    except InvalidOperation:
        return None


def import_profiles(db: Session, csv_path: str | Path) -> dict[str, int]:
    """Upsert profiles from df_Uid_data_hack.csv."""
    imported = rejected = 0
    required = {"SYNTHETIC_U", "MAINOKVED_CODE", "MAINOKVED_NAME",
                "REGION", "CITY", "REVENUE_COMPANY", "GROUP_ID"}

    with open(csv_path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"CSV must contain columns: {sorted(required)}")

        for row in reader:
            client_id = _clean(row.get("SYNTHETIC_U"))
            if not client_id:
                rejected += 1
                continue

            products = [
                column.removeprefix("CL_PRODUCT_").removesuffix("_MARK")
                for column, value in row.items()
                if column.startswith("CL_PRODUCT_")
                and column.endswith("_MARK")
                and _clean(value) in {"1", "1.0", "true", "True"}
            ]
            fts_countries = []
            country = _clean(row.get("FTS_COUNTRY_NAME"))
            if country:
                fts_countries.append(country)

            values = {
                "client_id": client_id,
                "industry_code": _clean(row.get("MAINOKVED_CODE")),
                "industry_name": _clean(row.get("MAINOKVED_NAME")),
                "region": _clean(row.get("REGION")),
                "city": _clean(row.get("CITY")),
                "revenue_rub": _revenue(row.get("REVENUE_COMPANY")),
                "group_id": _clean(row.get("GROUP_ID")),
                "products": products,
                "fts_countries": fts_countries,
                "related_entities": [],
            }

            stmt = insert(ClientProfileModel).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=[ClientProfileModel.client_id],
                set_={key: value for key, value in values.items()
                      if key != "client_id"},
            )
            db.execute(stmt)
            imported += 1

    db.commit()
    return {"imported": imported, "rejected": rejected}


def import_payments(
    db: Session,
    csv_path: str | Path,
    chunksize: int = 50_000,
) -> dict[str, int]:
    """Aggregate payment rows by owner, counterparty and direction."""
    # Owner -> (counterparty, direction) -> [total amount, total count]
    totals: dict[tuple[str, str, str], list[Decimal | int]] = defaultdict(
        lambda: [Decimal("0"), 0]
    )
    rejected = rows = 0

    # Keep only IDs that exist as client profiles.
    client_ids = set(db.scalars(select(ClientProfileModel.client_id)).all())

    with open(csv_path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        required = {"BENEFICIARY", "PAYER", "PAY_AMT", "PAY_CNT"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"CSV must contain columns: {sorted(required)}")

        for row in reader:
            rows += 1
            beneficiary = _clean(row.get("BENEFICIARY"))
            payer = _clean(row.get("PAYER"))
            if not beneficiary or not payer:
                rejected += 1
                continue

            try:
                amount = Decimal((row.get("PAY_AMT") or "0").strip().replace(",", "."))
                count = int(Decimal((row.get("PAY_CNT") or "0").strip()))
                if amount < 0 or count < 0:
                    raise ValueError("Negative payment value")
            except (InvalidOperation, ValueError):
                rejected += 1
                continue

            # Beneficiary receives money: incoming to beneficiary.
            if beneficiary in client_ids and payer != beneficiary:
                key = (beneficiary, payer, "incoming")
                totals[key][0] += amount
                totals[key][1] += count

            # Payer sends money: outgoing from payer.
            if payer in client_ids and beneficiary != payer:
                key = (payer, beneficiary, "outgoing")
                totals[key][0] += amount
                totals[key][1] += count

    # Replace previously imported payment links for repeatable imports.
    # Profiles not in the input are not modified.
    db.execute(
    delete(CounterpartyModel).where(
        CounterpartyModel.source == "payments_csv"
        )
    )
    db.flush()

    # Fill counterparties with industry data only when their profile exists.
    profile_map = {
        profile.client_id: profile
        for profile in db.scalars(select(ClientProfileModel)).all()
    }

    inserted = 0
    batch = []
    for (owner_id, counterparty_id, direction), (amount, count) in totals.items():
        counterparty = profile_map.get(counterparty_id)
        batch.append({
            "owner_client_id": owner_id,
            "counterparty_client_id": counterparty_id,
            "direction": direction,
            "source": "payments_csv",
            "pay_amt": amount,
            "pay_cnt": count,
            "industry_code": counterparty.industry_code if counterparty else None,
            "industry_name": counterparty.industry_name if counterparty else None,
            "region": counterparty.region if counterparty else None,
        })

        if len(batch) >= chunksize:
            db.execute(insert(CounterpartyModel), batch)
            inserted += len(batch)
            batch.clear()

    if batch:
        db.execute(insert(CounterpartyModel), batch)
        inserted += len(batch)

    db.commit()
    return {
        "rows_read": rows,
        "counterparty_links": inserted,
        "rejected": rejected,
    }
