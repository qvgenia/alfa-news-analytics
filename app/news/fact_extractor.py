
"""Извлечение и нормализация фактов из новостей."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from typing import Any

from app.contracts import NewsFact, NewsItem
from app.llm.gateway import LLMGateway


def build_news_facts(
    news: NewsItem,
    candidates: Iterable[tuple[str, float | None]],
) -> list[NewsFact]:
    """Преобразует пары (текст факта, уверенность) в NewsFact."""
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


def extract_news_facts(
    news: NewsItem,
    gateway: LLMGateway | None = None,
) -> list[NewsFact]:
    """Извлекает факты через LLM; при ошибке возвращает пустой список."""
    gateway = gateway or LLMGateway()

    system_prompt = """
Ты извлекаешь проверяемые факты из новостных публикаций.
Используй только информацию из заголовка и текста новости.
Не добавляй предположения, выводы или сведения из внешних источников.
Верни только корректный JSON без Markdown в формате:
{
  "facts": [
    {"text": "Краткий факт", "confidence": 0.95}
  ]
}
confidence — число от 0 до 1. Если фактов нет, верни {"facts": []}.
""".strip()

    user_prompt = json.dumps(
        {
            "title": news.title,
            "publisher": news.publisher,
            "text": news.text,
        },
        ensure_ascii=False,
    )

    try:
        response = gateway.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        payload: Any = json.loads(response)

        if not isinstance(payload, dict):
            return []

        candidates = payload.get("facts")
        if not isinstance(candidates, list):
            return []

        normalized: list[tuple[str, float | None]] = []

        for item in candidates:
            if not isinstance(item, dict):
                continue

            text = item.get("text")
            confidence = item.get("confidence")

            if not isinstance(text, str) or not text.strip():
                continue

            if isinstance(confidence, bool) or not isinstance(
                confidence, (int, float)
            ):
                confidence = None
            elif not 0 <= confidence <= 1:
                confidence = None
            else:
                confidence = float(confidence)

            normalized.append((text, confidence))

        return build_news_facts(news, normalized)

    except Exception:
        # Ошибка провайдера или некорректный ответ не ломают обработку новостей.
        return []
