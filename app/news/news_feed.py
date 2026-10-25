
"""Подготовка персонализированной новостной ленты."""

from app.contracts import ClientProfile, RankedNewsItem
from app.news.fact_extractor import extract_news_facts
from app.news.news_fetch_tool import news_fetch_tool
from app.ranking.ranker import rank_news


def get_ranked_news_feed(
    client: ClientProfile,
    limit_per_source: int = 50,
    facts_limit: int = 10,
) -> list[RankedNewsItem]:
    """Получает, ранжирует новости и извлекает факты для верхних результатов."""
    if facts_limit < 0:
        raise ValueError("facts_limit не может быть отрицательным")

    news_items = news_fetch_tool(limit_per_source=limit_per_source)
    ranked_items = rank_news(news_items, client)
    if not any(hasattr(item, "news") for item in ranked_items):
        return ranked_items

    enriched_items: list[RankedNewsItem] = []

    
    for index, item in enumerate(ranked_items):
        # Поддерживаем сторонние заглушки и прежний контракт тестов.
        news = getattr(item, "news", None)
        if news is None:
            enriched_items.append(item)
            continue

        if index >= facts_limit:
            enriched_items.append(item)
            continue

        try:
            facts = extract_news_facts(news)
        except Exception:
            facts = []

        enriched_news = news.model_copy(update={"facts": facts})
        enriched_items.append(
            item.model_copy(update={"news": enriched_news})
        )


    return enriched_items
