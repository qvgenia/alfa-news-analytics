# app/contracts.py
# иточник правды по моделям данных проекта.
# Менять только через Pull Request с согласия A, B и C.

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


#Профиль клиента (владелец: роль A)

class ClientProfile(ContractModel):
    client_id: str
    industry_code: str | None = None
    industry_name: str | None = None
    region: str | None = None
    revenue_rub: Decimal | None = Field(default=None, ge=0)
    products: list[str] = Field(default_factory=list)
    group_ids: list[str] = Field(default_factory=list)


#Источники и новости (владелец: роль B) -
class SourceRef(ContractModel):
    source_id: str
    source_type: Literal["news", "bank_analytics", "other"]
    title: str
    url: HttpUrl | None = None
    page: int | None = Field(default=None, ge=1)
    chunk_id: str | None = None
    excerpt: str | None = None


class NewsFact(ContractModel):
    fact_id: str
    text: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_id: str


class NewsItem(ContractModel):
    news_id: str
    title: str
    text: str
    publisher: str
    source_url: HttpUrl
    published_at: datetime | None = None  # у части RSS даты нет
    topic: str | None = None
    facts: list[NewsFact] = Field(default_factory=list)


class MatchedFeature(ContractModel):
    feature: str
    profile_field: str | None = None
    matched: bool
    reason: str


class RelevanceScore(ContractModel):
    news_id: str
    client_id: str
    score: float = Field(ge=0, le=100)
    matched_features: list[MatchedFeature] = Field(default_factory=list)
    rationale: str
    source_refs: list[SourceRef] = Field(default_factory=list)


class RankedNewsItem(ContractModel):
    news: NewsItem
    relevance: RelevanceScore


# Интерпретация (владелец:роль C) 

class Insight(ContractModel):
    insight_id: str | None = None
    news_id: str
    client_id: str

    # 1. Что произошло (только подтверждённые факты)
    what_happened: str
    facts: list[str] = Field(default_factory=list)

    # 2.Важно для этой компании
    why_it_matters: str

    # 3.(риски и возможности)
    potential_consequences: list[str] = Field(default_factory=list)

    # 4. Какие действия могут быть релевантны
    suggested_actions: list[str] = Field(default_factory=list)

    # 5. Позиция банка (только если найден источник) и вывод AI отдельно
    bank_view: str | None = None
    bank_view_available: bool = False
    ai_inference: str | None = None

    # 6. На чём основан вывод
    reasoning_basis: list[str] = Field(default_factory=list)

    limitations: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)


class AskRequest(ContractModel):
    client_id: str
    question: str = Field(min_length=1, max_length=2000)
    news_id: str | None = None
