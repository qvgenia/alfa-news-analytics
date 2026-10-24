
"""Лексический поиск по текстовым фрагментам RAG."""

import re
from collections import Counter
from typing import TypedDict


class TextChunk(TypedDict):
    document: str
    page: int
    text: str
    chunk_index: int


def tokenize(text: str) -> list[str]:
    """Извлекает слова в нижнем регистре."""
    return re.findall(r"\w+", text.lower())


def search_chunks(
    query: str,
    chunks: list[TextChunk],
    top_k: int = 5,
) -> list[TextChunk]:
    """Возвращает наиболее релевантные фрагменты по совпадению слов."""
    if top_k < 1:
        raise ValueError("top_k должен быть больше нуля")

    query_terms = set(tokenize(query))
    if not query_terms:
        return []

    scored: list[tuple[int, int, TextChunk]] = []

    for position, chunk in enumerate(chunks):
        chunk_terms = Counter(tokenize(chunk["text"]))
        score = sum(chunk_terms[term] for term in query_terms)

        if score > 0:
            scored.append((score, position, chunk))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [chunk for _, _, chunk in scored[:top_k]]
