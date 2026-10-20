
"""Поиск источников по тестовым новостям."""

from app.contracts import ClientProfile, SourceRef
from app.news.parser import load_sample_news


def retrieve_sources(
    query: str,
    client: ClientProfile | None = None,
    limit: int = 5,
) -> list[SourceRef]:
    """Находит тестовые новости по совпадениям слов с запросом.

    Это простой лексический поиск для прототипа, не векторный RAG.
    Параметр client зарезервирован для последующей персонализации.
    """
    if not query.strip() or limit < 1:
        return []

    query_words = {
        word.casefold().strip(".,!?;:()«»\"'")
        for word in query.split()
        if len(word.strip(".,!?;:()«»\"'")) >= 3
    }

    if not query_words:
        return []

    matches: list[tuple[int, SourceRef]] = []

    for news in load_sample_news():
        searchable_text = (
            f"{news.title} {news.text} {news.topic or ''}"
        ).casefold()

        score = sum(
            1 for word in query_words if word in searchable_text
        )

        if score:
            matches.append(
                (
                    score,
                    SourceRef(
                        source_id=news.news_id,
                        source_type="news",
                        title=news.title,
                        url=news.source_url,
                        excerpt=news.text[:500],
                    ),
                )
            )

    matches.sort(key=lambda item: item[0], reverse=True)
    return [source for _, source in matches[:limit]]
