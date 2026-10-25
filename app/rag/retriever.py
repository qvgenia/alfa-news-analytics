
"""Лексический поиск по текстовым фрагментам RAG с TF-IDF."""

import math
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
    """Возвращает наиболее релевантные фрагменты с помощью TF-IDF."""
    if top_k < 1:
        raise ValueError("top_k должен быть больше нуля")

    query_terms = set(tokenize(query))
    if not query_terms or not chunks:
        return []

    tokenized_chunks = [tokenize(chunk["text"]) for chunk in chunks]
    document_count = len(chunks)

    document_frequencies = Counter(
        term
        for terms in tokenized_chunks
        for term in set(terms)
    )

    scored: list[tuple[int, float, int, TextChunk]] = []

    for position, (chunk, terms) in enumerate(zip(chunks, tokenized_chunks)):
        if not terms:
            continue

        term_counts = Counter(terms)
        matched_terms = sum(1 for term in query_terms if term in term_counts)
        score = 0.0

        for term in query_terms:
            frequency = term_counts[term]
            if frequency == 0:
                continue

            tf = frequency / len(terms)
            idf = math.log(
                1 + document_count / document_frequencies[term]
            )
            score += tf * idf

        if matched_terms > 0:
            scored.append((matched_terms, score, position, chunk))

    scored.sort(
    key=lambda item: (
        -item[0],
        -sum(Counter(tokenize(item[3]["text"]))[term] for term in query_terms),
        -item[1],
        item[2],
        )
    )
    return [chunk for _, _, _, chunk in scored[:top_k]]
