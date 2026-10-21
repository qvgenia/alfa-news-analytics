
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ClientProfileModel(Base):
    """Профиль клиента банка для персонализации новостей."""

    __tablename__ = "client_profiles"

    client_id: Mapped[str] = mapped_column(String(100), primary_key=True)

    industry_code: Mapped[str | None] = mapped_column(String(50))
    industry_name: Mapped[str | None] = mapped_column(String(255))
    region: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(255))

    revenue_rub: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True
    )

    group_id: Mapped[str | None] = mapped_column(String(100))

    # Списки кодов продуктов, стран и связанных компаний.
    products: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    fts_countries: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    related_entities: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    counterparties: Mapped[list["CounterpartyModel"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CounterpartyModel(Base):
    """Обезличенный контрагент клиента и параметры платежей."""

    __tablename__ = "client_counterparties"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    owner_client_id: Mapped[str] = mapped_column(
        ForeignKey("client_profiles.client_id", ondelete="CASCADE"),
        nullable=False,
    )
    counterparty_client_id: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    industry_code: Mapped[str | None] = mapped_column(String(50))
    industry_name: Mapped[str | None] = mapped_column(String(255))
    region: Mapped[str | None] = mapped_column(String(255))

    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    pay_amt: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    pay_cnt: Mapped[int | None] = mapped_column(nullable=True)

    owner: Mapped["ClientProfileModel"] = relationship(
        back_populates="counterparties"
    )

    __table_args__ = (
        Index("ix_client_counterparties_owner", "owner_client_id"),
        Index(
            "ix_client_counterparties_counterparty",
            "counterparty_client_id",
        ),
    )