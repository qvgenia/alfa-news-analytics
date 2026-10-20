
"""Единая точка получения ранжированных новостей для агента."""

from app.contracts import ClientProfile, RankedNewsItem
from app.news.parser import load_sample_news, load_snapshot_news
from app.ranking.ranker import rank_news


def news_fetch_tool(
    client: ClientProfile,
    limit: int = 10,
    use_snapshot: bool = False,
) -> list[RankedNewsItem]:
    """Возвращает ранжированные новости для клиента.

    По умолчанию используются тестовые новости.
    Если use_snapshot=True, используются новости из локального RSS-снапшота.
    """
    if limit < 1:
        return []

    news_items = (
        load_snapshot_news() if use_snapshot else load_sample_news()
    )

    ranked_items = rank_news(news_items, client)
    return ranked_items[:limit]
