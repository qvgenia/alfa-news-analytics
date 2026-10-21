from app.contracts import ClientProfile, Counterparty, NewsItem
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
    assert ranked[0].relevance.score == 25.0
    assert ranked[1].relevance.score == 0.0


def test_unmatched_news_gets_zero_score():
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

    assert ranked[0].relevance.score == 0.0
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

    assert ranked[0].relevance.score == 25.0
    assert len(ranked[0].relevance.matched_features) == 1
    assert ranked[0].relevance.matched_features[0].feature == "industry_name"


def test_source_ref_uses_news_prefix():
    client = ClientProfile(
        client_id="finance-client",
        industry_name="финансы",
    )
    news = make_news("finance-001", "Аукционы РЕПО в рублях")

    ranked = rank_news([news], client)

    assert ranked[0].relevance.source_refs[0].source_id == "news:finance-001"


def test_matched_feature_has_machine_readable_code():
    client = ClientProfile(
        client_id="client-001",
        region="Москва",
    )
    news = make_news(
        "news-001",
        "Новые проекты в Москве",
    )

    ranked = rank_news([news], client)
    feature = ranked[0].relevance.matched_features[0]

    assert feature.feature == "region"
    assert feature.profile_field == "region"
    assert "Москва" in feature.reason


def test_empty_client_profile_gives_zero_score():
    client = ClientProfile(client_id="client-002")
    news = make_news(
        "news-002",
        "Изменения на рынке",
    )

    ranked = rank_news([news], client)

    assert ranked[0].relevance.score == 0.0
    assert ranked[0].relevance.matched_features == []


def test_multiple_matched_features_increase_score():
    client = ClientProfile(
        client_id="client-003",
        industry_name="финансы",
        region="Москва",
    )
    news = make_news(
        "news-003",
        "Банковская ликвидность в Москве",
    )

    ranked = rank_news([news], client)

    assert ranked[0].relevance.score == 50.0
    assert len(ranked[0].relevance.matched_features) == 2


def test_score_does_not_exceed_100():
    client = ClientProfile(
        client_id="client-004",
        industry_name="финансы",
        industry_code="123",
        region="Москва",
        products=["РКО", "LOA", "DEP"],
    )
    news = make_news(
        "news-004",
        "Банковская ликвидность в Москве, код 123, "
        "продукты РКО LOA DEP",
    )

    ranked = rank_news([news], client)

    assert ranked[0].relevance.score == 100.0
    assert len(ranked[0].relevance.matched_features) == 5


def test_counterparty_industry_and_region_score_35():
    client = ClientProfile(
        client_id="client-cp-001",
        top_counterparties=[
            Counterparty(
                client_id="counterparty-001",
                direction="incoming",
                industry_name="финансы",
                region="Москва",
            )
        ],
    )
    news = make_news(
        "news-cp-001",
        "Банковская ликвидность в Москве",
    )

    ranked = rank_news([news], client)[0]

    assert ranked.relevance.score == 35.0
    assert len(ranked.relevance.matched_features) == 2
    assert all(
        feature.feature == "counterparty"
        for feature in ranked.relevance.matched_features
    )


def test_counterparty_region_without_industry_match_scores_10():
    client = ClientProfile(
        client_id="client-cp-002",
        top_counterparties=[
            Counterparty(
                client_id="counterparty-002",
                direction="outgoing",
                industry_name="строительство",
                region="Москва",
            )
        ],
    )
    news = make_news(
        "news-cp-002",
        "Новые проекты в Москве",
    )

    ranked = rank_news([news], client)[0]

    assert ranked.relevance.score == 10.0
    assert len(ranked.relevance.matched_features) == 1
    assert ranked.relevance.matched_features[0].feature == "counterparty"


def test_same_client_and_counterparty_industry_count_only_once():
    client = ClientProfile(
        client_id="client-cp-006",
        industry_name="финансы",
        top_counterparties=[
            Counterparty(
                client_id="counterparty-006",
                direction="incoming",
                industry_name="финансы",
            )
        ],
    )
    news = make_news(
        "news-cp-006",
        "Банковская ликвидность",
    )

    ranked = rank_news([news], client)[0]

    assert ranked.relevance.score == 25.0
    assert len(ranked.relevance.matched_features) == 1
    assert ranked.relevance.matched_features[0].feature == "industry_name"


def test_counterparty_industry_code_takes_priority_over_name():
    client = ClientProfile(
        client_id="client-cp-007",
        top_counterparties=[
            Counterparty(
                client_id="counterparty-007",
                direction="incoming",
                industry_code="123",
                industry_name="финансы",
            )
        ],
    )
    news = make_news(
        "news-cp-007",
        "Банковская ликвидность",
    )

    ranked = rank_news([news], client)[0]

    assert ranked.relevance.score == 0.0
    assert ranked.relevance.matched_features == []


def test_duplicate_counterparty_industry_and_region_are_not_double_counted():
    client = ClientProfile(
        client_id="client-cp-003",
        top_counterparties=[
            Counterparty(
                client_id="counterparty-003a",
                direction="incoming",
                industry_name="финансы",
                region="Москва",
            ),
            Counterparty(
                client_id="counterparty-003b",
                direction="outgoing",
                industry_name="финансы",
                region="Москва",
            ),
        ],
    )
    news = make_news(
        "news-cp-003",
        "Банковская ликвидность в Москве",
    )

    ranked = rank_news([news], client)[0]

    assert ranked.relevance.score == 35.0
    assert len(ranked.relevance.matched_features) == 2


def test_counterparty_direction_amount_and_count_do_not_add_points():
    client = ClientProfile(
        client_id="client-cp-004",
        top_counterparties=[
            Counterparty(
                client_id="counterparty-004",
                direction="incoming",
                pay_amt=1000000,
                pay_cnt=50,
            )
        ],
    )
    news = make_news("news-cp-004", "Общие экономические новости")

    ranked = rank_news([news], client)[0]

    assert ranked.relevance.score == 0.0
    assert ranked.relevance.matched_features == []


def test_counterparty_score_respects_maximum_100():
    client = ClientProfile(
        client_id="client-cp-005",
        industry_name="финансы",
        region="Москва",
        products=["РКО", "LOA"],
        top_counterparties=[
            Counterparty(
                client_id="counterparty-005",
                direction="incoming",
                industry_name="финансы",
                region="Москва",
            )
        ],
    )
    news = make_news(
        "news-cp-005",
        "Банковская ликвидность в Москве, РКО и LOA",
    )

    ranked = rank_news([news], client)[0]

    assert ranked.relevance.score == 100.0
