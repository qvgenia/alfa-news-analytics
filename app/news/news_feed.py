"""Подготовка персонализированной новостной ленты."""

from app.contracts import ClientProfile, RankedNewsItem
from app.news.news_fetch_tool import news_fetch_tool
from app.ranking.ranker import rank_news


def get_ranked_news_feed(
    client: ClientProfile,
    limit_per_source: int = 50,
) -> list[RankedNewsItem]:
    """Получает новости и ранжирует их для переданного профиля клиента."""
    news_items = news_fetch_tool(limit_per_source=limit_per_source)
    return rank_news(news_items, client)
