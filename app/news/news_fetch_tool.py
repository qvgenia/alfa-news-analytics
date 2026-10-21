"""Инструмент получения новостей из RSS."""

from app.contracts import NewsItem
from app.news.rss_parser import fetch_rss_news


def news_fetch_tool(
    limit_per_source: int = 50,
) -> list[NewsItem]:
    """Получает свежие новости из настроенных RSS-источников."""
    return fetch_rss_news(limit_per_source=limit_per_source)
