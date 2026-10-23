
"""Получение новостей из RSS и удаление дубликатов."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import urlsplit, urlunsplit

import feedparser

from app.contracts import NewsItem


# Для первого прототипа используем два RSS-источника.
# Перед демонстрацией проверь доступность лент.
RSS_SOURCES: dict[str, str] = {
    "РБК": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
    "Коммерсантъ": "https://www.kommersant.ru/RSS/news.xml",
}


def _clean_text(value: str | None) -> str:
    """Удаляет HTML-разметку и лишние пробелы."""
    if not value:
        return ""

    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def _normalize_url(url: str) -> str:
    """Убирает фрагмент и стандартные tracking-параметры URL."""
    parts = urlsplit(url.strip())
    tracking_prefixes = ("utm_",)
    tracking_names = {"fbclid", "gclid", "yclid"}

    query_items = []
    for item in parts.query.split("&"):
        if not item:
            continue

        key = item.split("=", 1)[0].lower()
        if key in tracking_names or key.startswith(tracking_prefixes):
            continue
        query_items.append(item)

    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            "&".join(query_items),
            "",
        )
    )


def _parse_date(entry: object) -> datetime | None:
    """Преобразует дату RSS в datetime с часовым поясом."""
    for field in ("published", "updated"):
        value = getattr(entry, field, None)
        if not value:
            continue

        try:
            result = parsedate_to_datetime(value)
            if result.tzinfo is None:
                result = result.replace(tzinfo=timezone.utc)
            return result
        except (TypeError, ValueError, OverflowError):
            continue

    return None


def _stable_news_id(url: str, title: str) -> str:
    """Создаёт стабильный ID, если источник не предоставляет свой ID."""
    identity = _normalize_url(url) or title.casefold()
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def fetch_rss_news(
    sources: dict[str, str] | None = None,
    limit_per_source: int = 50,
) -> list[NewsItem]:
    """Загружает RSS-ленты и возвращает уникальные новости."""
    if limit_per_source < 1:
        raise ValueError("limit_per_source должен быть не меньше 1")

    sources = sources or RSS_SOURCES
    news_by_url: dict[str, NewsItem] = {}
    seen_titles: set[str] = set()

    for publisher, feed_url in sources.items():
        try:
            feed = feedparser.parse(feed_url)
        except Exception:
            # Ошибка одного источника не должна останавливать остальные.
            continue

        for entry in feed.entries[:limit_per_source]:
            title = _clean_text(getattr(entry, "title", None))
            link = _normalize_url(getattr(entry, "link", "") or "")
            summary = _clean_text(
                getattr(entry, "summary", None)
                or getattr(entry, "description", None)
            )

            if not title or not link:
                continue

            normalized_title = re.sub(
                r"\W+", " ", title.casefold()
            ).strip()

            # Пропускаем одинаковые ссылки и одинаковые заголовки.
            if link in news_by_url or normalized_title in seen_titles:
                continue

            published_at = _parse_date(entry)
            news_id = _stable_news_id(link, title)

            news_by_url[link] = NewsItem(
                news_id=news_id,
                title=title,
                text=summary or title,
                publisher=publisher,
                source_url=link,
                published_at=published_at,
            )
            seen_titles.add(normalized_title)

    return sorted(
        news_by_url.values(),
        key=lambda item: item.published_at
        or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
