
"""Начальная детерминированная оценка релевантности новостей."""

from app.contracts import (
    ClientProfile,
    MatchedFeature,
    NewsItem,
    RankedNewsItem,
    RelevanceScore,
    SourceRef,
)


# Простые тематические подсказки для отраслевого ранжирования.
# Это эвристика, а не экспертная оценка влияния новости.
INDUSTRY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "финансы": (
        "финансов",
        "денежно-кредит",
        "ключев",
        "процентн",
        "ставк",
        "инфляц",
        "ликвидност",
        "репо",
        "валют",
        "кредит",
        "облигац",
        "ценн бумаг",
        "банковск",
    ),
}


def _find_match(searchable_text: str, value: str) -> str | None:
    """Ищет буквальное совпадение или тематический термин."""
    normalized_value = value.strip().casefold()
    if not normalized_value:
        return None

    if normalized_value in searchable_text:
        return value.strip()

    keywords = INDUSTRY_KEYWORDS.get(normalized_value, ())
    for keyword in keywords:
        if keyword in searchable_text:
            return keyword

    return None


def rank_news(
    news_items: list[NewsItem],
    client: ClientProfile,
) -> list[RankedNewsItem]:
    """Оценивает новости по совпадениям с полями профиля клиента.

    Это базовая эвристика, а не прогноз финансового эффекта.
    """
    ranked: list[RankedNewsItem] = []
    profile_features: list[tuple[str, str, str]] = []

    if client.industry_name:
        profile_features.append(
            ("industry_name", "отрасль", client.industry_name)
        )
    if client.industry_code:
        profile_features.append(
            ("industry_code", "код отрасли", client.industry_code)
        )
    if client.region:
        profile_features.append(("region", "регион", client.region))

    for product in client.products:
        if product.strip():
            profile_features.append(
                ("products", "банковский продукт", product)
            )

    for news in news_items:
        searchable_text = (
            f"{news.title} {news.text} {news.topic or ''}"
        ).casefold()
        matched_features: list[MatchedFeature] = []

        for profile_field, feature, value in profile_features:
            matched_term = _find_match(searchable_text, value)

            if matched_term:
                matched_features.append(
                    MatchedFeature(
                        feature=feature,
                        profile_field=profile_field,
                        matched=True,
                        reason=(
                            "Найдено совпадение с профилем клиента: "
                            f"«{matched_term}»."
                        ),
                    )
                )

        score = min(100.0, 20.0 + 25.0 * len(matched_features))

        source_ref = SourceRef(
            source_id=news.news_id,
            source_type="news",
            title=news.title,
            url=news.source_url,
            excerpt=news.text[:500],
        )

        ranked.append(
            RankedNewsItem(
                news=news,
                relevance=RelevanceScore(
                    news_id=news.news_id,
                    client_id=client.client_id,
                    score=score,
                    matched_features=matched_features,
                    rationale=(
                        "Начальная эвристическая оценка: "
                        f"найдено совпадений с профилем — "
                        f"{len(matched_features)}. "
                        "Это не прогноз финансового эффекта."
                    ),
                    source_refs=[source_ref],
                ),
            )
        )

    return sorted(
        ranked,
        key=lambda item: item.relevance.score,
        reverse=True,
    )
