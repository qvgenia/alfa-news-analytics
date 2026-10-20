"""Единая точка получения ранжированных новостей для агента."""

from app.contracts import ClientProfile, RankedNewsItem
from app.news.parser import load_sample_news
from app.ranking.ranker import rank_news


def news_fetch_tool(
    client: ClientProfile,
    limit: int = 10,
) -> list[RankedNewsItem]:
    """Возвращает ранжированные тестовые новости для клиента."""
    if limit < 1:
        return []

    news_items = load_sample_news()
    ranked_items = rank_news(news_items, client)

    return ranked_items[:limit]
