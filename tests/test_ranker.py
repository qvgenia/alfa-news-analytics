
from app.contracts import ClientProfile, NewsItem
from app.ranking.ranker import rank_news


def make_news(
    news_id: str,
    title: str,
    text: str = "",
    topic: str | None = None,
) -> NewsItem:
    return NewsItem(
        news_id=news_id,
        title=title,
        text=text,
        publisher="Тестовый источник",
        source_url=f"https://example.com/{news_id}",
        topic=topic,
    )


def test_financial_news_gets_higher_score_for_financial_client():
    client = ClientProfile(
        client_id="finance-client",
        industry_name="финансы",
    )
    news = [
        make_news(
            "finance-001",
            "Параметры аукционов РЕПО в рублях",
        ),
        make_news(
            "other-001",
            "Изменения в логистике и грузоперевозках",
        ),
    ]

    ranked = rank_news(news, client)

    assert ranked[0].news.news_id == "finance-001"
    assert ranked[0].relevance.score > ranked[1].relevance.score


def test_unmatched_news_keeps_base_score():
    client = ClientProfile(
        client_id="finance-client",
        industry_name="финансы",
    )
    news = [
        make_news(
            "other-001",
            "Изменения в логистике и грузоперевозках",
        ),
    ]

    ranked = rank_news(news, client)

    assert ranked[0].relevance.score == 20.0
    assert ranked[0].relevance.matched_features == []


def test_rank_news_sorts_by_score_descending():
    client = ClientProfile(
        client_id="finance-client",
        industry_name="финансы",
    )
    news = [
        make_news("other-001", "Новости о логистике"),
        make_news("finance-001", "Аукционы РЕПО в рублях"),
    ]

    ranked = rank_news(news, client)
    scores = [item.relevance.score for item in ranked]

    assert scores == sorted(scores, reverse=True)


def test_financial_topic_can_match_without_keyword_in_title():
    client = ClientProfile(
        client_id="finance-client",
        industry_name="финансы",
    )
    news = [
        make_news(
            "finance-001",
            "Новая информация",
            topic="банковская ликвидность",
        ),
    ]

    ranked = rank_news(news, client)

    assert ranked[0].relevance.score == 45.0
    assert len(ranked[0].relevance.matched_features) == 1
