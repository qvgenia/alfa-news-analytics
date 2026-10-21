from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts import ClientProfile, Counterparty
from app.db.models import ClientProfileModel


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
        revenue_rub=profile.revenue_rub,
        products=profile.products or [],
        group_ids=[profile.group_id] if profile.group_id else [],
        top_counterparties=top_counterparties,
    )
