"""Подготовка извлечённых фактов к общему контракту NewsFact."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

from app.contracts import NewsFact, NewsItem


def build_news_facts(
    news: NewsItem,
    candidates: Iterable[tuple[str, float | None]],
) -> list[NewsFact]:
    """Преобразует результаты извлечения в факты со ссылкой на новость.

    candidates содержит пары (текст факта, уверенность).
    Извлечение фактов языковой моделью выполняется отдельно.
    """
    source_id = f"news:{news.news_id}"
    facts: list[NewsFact] = []
    seen_texts: set[str] = set()

    for text, confidence in candidates:
        cleaned_text = re.sub(r"\s+", " ", text).strip()
        if not cleaned_text:
            continue

        normalized_text = cleaned_text.casefold()
        if normalized_text in seen_texts:
            continue

        fact_id = hashlib.sha256(
            f"{news.news_id}:{normalized_text}".encode("utf-8")
        ).hexdigest()[:16]

        facts.append(
            NewsFact(
                fact_id=fact_id,
                text=cleaned_text,
                confidence=confidence,
                source_id=source_id,
            )
        )
        seen_texts.add(normalized_text)

    return facts
