from datetime import datetime, timezone
from decimal import Decimal

from app.contracts import (
    ClientProfile,
    Counterparty,
    MatchedFeature,
    NewsFact,
    NewsItem,
    RankedNewsItem,
    RelevanceScore,
    SourceRef,
)

DEMO_CLIENT_ID = "DEMO_TECH_001"
DEMO_NEWS_ID = "demo-news-001"


def build_demo_profile() -> ClientProfile:
    """Демо-профиль IT-компании из Москвы (тестовые данные)."""
    return ClientProfile(
        client_id=DEMO_CLIENT_ID,
        industry_code="62.01",
        industry_name="Разработка компьютерного программного обеспечения",
        region="Москва",
        city="Москва",
        revenue_rub=Decimal("150000000"),
        products=["RKO", "LOA"],
        group_ids=[],
        fts_countries=[],
        top_counterparties=[
            Counterparty(
                client_id="DEMO_CP_001",
                direction="outgoing",
                pay_amt=Decimal("5000000"),
                pay_cnt=12,
            )
        ],
        related_entities=[],
    )


def build_demo_ranked_news() -> RankedNewsItem:
    """Демо-новость с обоснованным совпадением с профилем (тестовые данные)."""
    source_id = f"news:{DEMO_NEWS_ID}"
    url = "https://example.com/demo-news-001"

    source = SourceRef(
        source_id=source_id,
        source_type="news",
        title="Демо-новость об изменении ключевой ставки",
        url=url,
    )

    news = NewsItem(
        news_id=DEMO_NEWS_ID,
        title="Демо: изменение ключевой ставки Банка России",
        text=(
            "Тестовая новость для демонстрации. Банк России изменил "
            "ключевую ставку, что влияет на стоимость кредитов для бизнеса."
        ),
        publisher="Demo Publisher",
        source_url=url,
        published_at=datetime(2026, 10, 24, 9, 0, tzinfo=timezone.utc),
        topic="ключевая ставка",
        facts=[
            NewsFact(
                fact_id="demo-fact-001",
                text="Изменение ключевой ставки влияет на стоимость кредитов.",
                confidence=0.8,
                source_id=source_id,
            )
        ],
    )

    relevance = RelevanceScore(
        news_id=DEMO_NEWS_ID,
        client_id=DEMO_CLIENT_ID,
        score=72.0,
        matched_features=[
            MatchedFeature(
                feature="product_loa",
                profile_field="products",
                matched=True,
                reason="У клиента есть кредитный продукт LOA, ставка влияет на его стоимость.",
            )
        ],
        rationale="Новость о ставке связана с кредитным продуктом клиента (демо-оценка).",
        source_refs=[source],
    )

    return RankedNewsItem(news=news, relevance=relevance)
