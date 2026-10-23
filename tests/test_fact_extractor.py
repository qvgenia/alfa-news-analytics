from app.contracts import NewsItem
from app.news.fact_extractor import build_news_facts


def make_news() -> NewsItem:
    return NewsItem(
        news_id="news-001",
        title="Компания объявила об инвестициях",
        text="Компания объявила об инвестициях в новый завод.",
        publisher="Тестовый источник",
        source_url="https://example.com/news-001",
    )


def test_build_news_facts_sets_source_id_and_confidence():
    news = make_news()

    facts = build_news_facts(
        news,
        [("Компания инвестирует в новый завод.", 0.95)],
    )

    assert len(facts) == 1
    assert facts[0].text == "Компания инвестирует в новый завод."
    assert facts[0].confidence == 0.95
    assert facts[0].source_id == "news:news-001"


def test_build_news_facts_skips_empty_text_and_duplicates():
    news = make_news()

    facts = build_news_facts(
        news,
        [
            (" Компания открыла завод. ", 0.9),
            ("компания открыла завод.", 0.8),
            ("   ", 0.7),
        ],
    )

    assert len(facts) == 1
    assert facts[0].text == "Компания открыла завод."


def test_fact_id_is_stable():
    news = make_news()
    candidates = [("Компания открыла завод.", 0.9)]

    first = build_news_facts(news, candidates)
    second = build_news_facts(news, candidates)

    assert first[0].fact_id == second[0].fact_id


def test_empty_candidates_return_empty_list():
    assert build_news_facts(make_news(), []) == []
