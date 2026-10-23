
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts import ClientProfile, Counterparty
from app.db.models import ClientProfileModel, CounterpartyModel


def get_client_profile(
    client_id: str,
    db: Session,
) -> ClientProfile | None:
    """Возвращает профиль клиента вместе с контрагентами."""
    statement = select(ClientProfileModel).where(
        ClientProfileModel.client_id == client_id
    )
    profile = db.scalars(statement).first()

    if profile is None:
        return None

    top_counterparties = [
        Counterparty(
            client_id=item.counterparty_client_id,
            industry_code=item.industry_code,
            industry_name=item.industry_name,
            region=item.region,
            direction=item.direction,
            pay_amt=item.pay_amt,
            pay_cnt=item.pay_cnt,
        )
        for item in profile.counterparties
    ]

    return ClientProfile(
        client_id=profile.client_id,
        industry_code=profile.industry_code,
        industry_name=profile.industry_name,
        region=profile.region,
        city=profile.city,
        revenue_rub=profile.revenue_rub,
        products=profile.products or [],
        group_ids=[profile.group_id] if profile.group_id else [],
        fts_countries=profile.fts_countries or [],
        related_entities=profile.related_entities or [],
        top_counterparties=top_counterparties,
    )


def _apply_profile_data(
    profile: ClientProfileModel,
    data: ClientProfile,
) -> None:
    """Переносит данные контракта в ORM-модель."""
    profile.industry_code = data.industry_code
    profile.industry_name = data.industry_name
    profile.region = data.region
    profile.city = data.city
    profile.revenue_rub = data.revenue_rub
    profile.products = list(data.products)
    profile.fts_countries = list(data.fts_countries)
    profile.related_entities = list(data.related_entities)
    profile.group_id = data.group_ids[0] if data.group_ids else None

    profile.counterparties.clear()
    for item in data.top_counterparties:
        profile.counterparties.append(
            CounterpartyModel(
                counterparty_client_id=item.client_id,
                industry_code=item.industry_code,
                industry_name=item.industry_name,
                region=item.region,
                direction=item.direction,
                pay_amt=item.pay_amt,
                pay_cnt=item.pay_cnt,
            )
        )


def create_client_profile(
    data: ClientProfile,
    db: Session,
) -> ClientProfile:
    """Создаёт профиль клиента вместе с контрагентами."""
    profile = ClientProfileModel(client_id=data.client_id)
    _apply_profile_data(profile, data)

    db.add(profile)
    db.commit()

    return get_client_profile(data.client_id, db)


def update_client_profile(
    client_id: str,
    data: ClientProfile,
    db: Session,
) -> ClientProfile | None:
    """Полностью обновляет существующий профиль клиента."""
    profile = db.get(ClientProfileModel, client_id)
    if profile is None:
        return None

    _apply_profile_data(profile, data)
    db.commit()

    return get_client_profile(client_id, db)
