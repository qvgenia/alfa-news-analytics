
"""Загрузка тестовых и сохранённых RSS-новостей."""

import hashlib
import json
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
import re

from app.contracts import NewsItem


SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "news_snapshot.json"
)


def load_sample_news() -> list[NewsItem]:
    """Возвращает тестовый набор новостей без сетевых запросов."""
    return [
        NewsItem(
            news_id="demo-001",
            title="ЦБ сохранил ключевую ставку",
            text=(
                "Банк России сохранил ключевую ставку. "
                "Высокая стоимость заёмного финансирования "
                "может влиять на инвестиционные планы компаний."
            ),
            publisher="Тестовый источник",
            source_url="https://example.com/news/interest-rate",
            topic="финансы",
        ),
        NewsItem(
            news_id="demo-002",
            title="Изменения в логистике и грузоперевозках",
            text=(
                "Компании транспортной отрасли оценивают "
                "изменения стоимости перевозок и цепочек поставок."
            ),
            publisher="Тестовый источник",
            source_url="https://example.com/news/logistics",
            topic="логистика",
        ),
        NewsItem(
            news_id="demo-003",
            title="Новые требования к отчётности компаний",
            text=(
                "Обсуждаются изменения требований к отчётности "
                "и соблюдению нормативных правил для бизнеса."
            ),
            publisher="Тестовый источник",
            source_url="https://example.com/news/reporting",
            topic="регулирование",
        ),
    ]


def _clean_html(value: str) -> str:
    """Удаляет HTML-разметку и приводит текст к обычному виду."""
    value = re.sub(r"(?s)<(script|style)\b.*?</\1>", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    return " ".join(value.split())


def _parse_published_at(value: str | None) -> datetime | None:
    """Преобразует дату RSS в datetime."""
    if not value:
        return None

    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None


def load_snapshot_news() -> list[NewsItem]:
    """Загружает новости из локального RSS-снапшота без сетевых запросов."""
    if not SNAPSHOT_PATH.exists():
        return []

    try:
        with SNAPSHOT_PATH.open(encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []

    records = data.get("items", []) if isinstance(data, dict) else []
    if not isinstance(records, list):
        return []

    news: list[NewsItem] = []
    seen_urls: set[str] = set()

    for record in records:
        if not isinstance(record, dict):
            continue

        title = str(record.get("title") or "").strip()
        url = str(record.get("url") or "").strip()

        if not title or not url or url in seen_urls:
            continue

        seen_urls.add(url)

        description = _clean_html(str(record.get("description") or ""))
        text = description or title
        news_id = "cbr-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]

        try:
            item = NewsItem(
                news_id=news_id,
                title=title,
                text=text,
                publisher=str(record.get("publisher") or "Неизвестный источник"),
                source_url=url,
                published_at=_parse_published_at(record.get("published_at")),
            )
        except (TypeError, ValueError):
            # Пропускаем записи, которые не соответствуют контракту NewsItem.
            continue

        news.append(item)

    return news
