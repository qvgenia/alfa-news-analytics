
"""Детерминированная оценка релевантности новостей."""

from app.contracts import (
    ClientProfile,
    MatchedFeature,
    NewsItem,
    RankedNewsItem,
    RelevanceScore,
    SourceRef,
)

INDUSTRY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "финансы": (
        "финансов",
        "денежно-кредит",
        "ключев",
        "процентн",
        "инфляц",
        "ликвидност",
        "репо",
        "валют",
        "кредит",
        "облигац",
        "ценн бумаг",
        "банковск",
    ),
    "разработка компьютерного программного обеспечения": (
        "программного обеспеч",
        "разработк программ",
        "разработк по",
        "информационн технолог",
        "ит-компан",
        "айти-компан",
        "разработчик программ",
        "программный продукт",
        "программная платформа",
        "кибербезопасност",
    ),
    "разработка программного обеспечения": (
        "программного обеспеч",
        "разработк программ",
        "разработк по",
        "информационн технолог",
        "ит-компан",
        "айти-компан",
        "разработчик программ",
        "программный продукт",
        "программная платформа",
        "кибербезопасност",
    ),
    "ремонт машин и оборудования": (
        "оборудован",
        "ремонт",
        "машиностро",
        "станк",
        "запчаст",
        "техобслуживан",
        "промышленн предприят",
        "производственн лини",
        "инструмент",
        "механическ",
        "инженер",
        "металлург",
    ),
    "оптовая торговля": (
        "оптов торговл",
        "оптов постав",
        "оптов закуп",
        "оптов продав",
        "оптовик",
    ),
}

FEATURE_LABELS: dict[str, str] = {
    "industry_name": "отрасль",
    "industry_code": "код отрасли",
    "region": "регион",
    "products": "банковский продукт",
}

POINTS_PER_FEATURE = 25.0
COUNTERPARTY_INDUSTRY_POINTS = 25.0
COUNTERPARTY_REGION_POINTS = 10.0
MAX_SCORE = 100.0


def _find_match(searchable_text: str, value: str) -> str | None:
    """Ищет буквальное совпадение или известный тематический термин."""
    normalized_value = value.strip().casefold()

    if not normalized_value:
        return None

    if normalized_value in searchable_text:
        return value.strip()

    if normalized_value == "москва":
        for form in ("москве", "москвой", "москвы"):
            if form in searchable_text:
                return "Москва"

    for keyword in INDUSTRY_KEYWORDS.get(normalized_value, ()):
        if keyword in searchable_text:
            return keyword

    return None


def _industry_key(code: str | None, name: str | None) -> str | None:
    """Возвращает ключ отрасли; код имеет приоритет над названием."""
    if code and code.strip():
        return f"code:{code.strip().casefold()}"

    if name and name.strip():
        return f"name:{name.strip().casefold()}"

    return None


def _counterparty_matches(
    searchable_text: str,
    client: ClientProfile,
    matched_industries: set[str],
) -> tuple[list[MatchedFeature], float]:
    """Считает уникальные сигналы отрасли и региона контрагентов."""
    features: list[MatchedFeature] = []
    matched_regions: set[str] = set()
    score = 0.0

    for counterparty in client.top_counterparties:
        industry_value = (
            counterparty.industry_code
            if counterparty.industry_code
            and counterparty.industry_code.strip()
            else counterparty.industry_name
        )

        industry_match = (
            _find_match(searchable_text, industry_value)
            if industry_value
            else None
        )
        key = _industry_key(
            counterparty.industry_code,
            counterparty.industry_name,
        )

        if industry_match and key and key not in matched_industries:
            matched_industries.add(key)
            score += COUNTERPARTY_INDUSTRY_POINTS
            features.append(
                MatchedFeature(
                    feature="counterparty",
                    profile_field="top_counterparties",
                    matched=True,
                    reason=(
                        "Подтверждено совпадение с отраслью контрагента: "
                        f"«{industry_match}» (+25)."
                    ),
                )
            )

        if counterparty.region:
            region_match = _find_match(
                searchable_text,
                counterparty.region,
            )
            region_key = counterparty.region.strip().casefold()

            if region_match and region_key not in matched_regions:
                matched_regions.add(region_key)
                score += COUNTERPARTY_REGION_POINTS
                features.append(
                    MatchedFeature(
                        feature="counterparty",
                        profile_field="top_counterparties",
                        matched=True,
                        reason=(
                            "Подтверждено совпадение региона контрагента: "
                            f"«{region_match}» (+10)."
                        ),
                    )
                )

    return features, score


def rank_news(
    news_items: list[NewsItem],
    client: ClientProfile,
) -> list[RankedNewsItem]:
    """Ранжирует новости по совпадениям с профилем клиента.

    Каждый совпавший признак профиля даёт 25 баллов.
    Отрасль контрагента даёт ещё 25 баллов, если её сигнал
    ещё не был учтён. Регион контрагента даёт 10 баллов.
    Максимум — 100. Это эвристика, а не прогноз финансового эффекта.
    """
    ranked: list[RankedNewsItem] = []
    profile_features: list[tuple[str, str]] = []

    # Проверяем код и название отрасли отдельно.
    if client.industry_code and client.industry_code.strip():
        profile_features.append(("industry_code", client.industry_code))

    if client.industry_name and client.industry_name.strip():
        profile_features.append(("industry_name", client.industry_name))

    if client.region and client.region.strip():
        profile_features.append(("region", client.region))

    for product in client.products:
        if product.strip():
            profile_features.append(("products", product))

    for news in news_items:
        searchable_text = (
            f"{news.title} {news.text} {news.topic or ''}"
        ).casefold()

        matched_features: list[MatchedFeature] = []
        matched_industries: set[str] = set()

        for profile_field, value in profile_features:
            matched_term = _find_match(searchable_text, value)

            if not matched_term:
                continue

            # Не начисляем дважды за одну и ту же отрасль,
            # если совпали и код, и название профиля.
            if profile_field in ("industry_code", "industry_name"):
                industry_key = _industry_key(
                    client.industry_code,
                    client.industry_name,
                )
                if industry_key and industry_key in matched_industries:
                    continue
                if industry_key:
                    matched_industries.add(industry_key)

            matched_features.append(
                MatchedFeature(
                    feature=profile_field,
                    profile_field=profile_field,
                    matched=True,
                    reason=(
                        "Найдено совпадение по признаку "
                        f"«{FEATURE_LABELS[profile_field]}»: "
                        f"«{matched_term}»."
                    ),
                )
            )

        counterparty_features, counterparty_score = _counterparty_matches(
            searchable_text,
            client,
            matched_industries,
        )
        matched_features.extend(counterparty_features)

        profile_feature_count = (
            len(matched_features) - len(counterparty_features)
        )
        profile_score = POINTS_PER_FEATURE * profile_feature_count
        score = min(MAX_SCORE, profile_score + counterparty_score)

        source_ref = SourceRef(
            source_id=f"news:{news.news_id}",
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
                        f"найдено подтверждённых совпадений — "
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
