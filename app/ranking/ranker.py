"""Начальная детерминированная оценка релевантности новостей."""

from app.contracts import (
    ClientProfile,
    MatchedFeature,
    RankedNewsItem,
    RelevanceScore,
    SourceRef,
)
from app.contracts import NewsItem


def rank_news(
    news_items: list[NewsItem],
    client: ClientProfile,
) -> list[RankedNewsItem]:
    """Оценивает новости по совпадениям с доступными полями профиля.

    Это базовый алгоритм для прототипа, а не экспертная оценка влияния.
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
            profile_features.append(("products", "банковский продукт", product))

    for news in news_items:
        searchable_text = f"{news.title} {news.text} {news.topic or ''}".casefold()
        matched_features: list[MatchedFeature] = []

        for profile_field, feature, value in profile_features:
            normalized_value = value.strip().casefold()
            if normalized_value and normalized_value in searchable_text:
                matched_features.append(
                    MatchedFeature(
                        feature=feature,
                        profile_field=profile_field,
                        matched=True,
                        reason=f"В тексте новости найдено совпадение: «{value}».",
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
                        f"найдено совпадений с профилем — {len(matched_features)}. "
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
