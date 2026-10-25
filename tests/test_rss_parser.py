
from datetime import datetime, timezone
from unittest.mock import patch

import feedparser

from app.news.rss_parser import fetch_rss_news


def make_feed(*entries):
    """Создаёт RSS-ответ для тестов без реального интернета."""
    return feedparser.FeedParserDict(
        entries=[
            feedparser.FeedParserDict(entry)
            for entry in entries
        ],
        bozo=False,
    )


@patch("app.news.rss_parser._fetch_feed")
def test_fetch_rss_news_converts_entry_to_news_item(mock_fetch_feed):
    mock_fetch_feed.return_value = make_feed(
        {
            "title": "ЦБ изменил ключевую ставку",
            "link": "https://example.com/news/1",
            "summary": "<p>Банк России объявил решение.</p>",
            "published": "Wed, 21 Oct 2026 10:00:00 GMT",
        }
    )

    news = fetch_rss_news({"Тестовый источник": "https://example.com/rss"})

    assert len(news) == 1
    assert news[0].title == "ЦБ изменил ключевую ставку"
    assert news[0].publisher == "Тестовый источник"
    assert news[0].text == "Банк России объявил решение."
    assert str(news[0].source_url) == "https://example.com/news/1"
    assert news[0].published_at == datetime(
        2026, 10, 21, 10, 0, tzinfo=timezone.utc
    )


@patch("app.news.rss_parser._fetch_feed")
def test_fetch_rss_news_removes_duplicate_urls(mock_fetch_feed):
    mock_fetch_feed.return_value = make_feed(
        {
            "title": "Новость",
            "link": "https://example.com/news/1",
            "summary": "Текст",
        },
        {
            "title": "Другая версия новости",
            "link": "https://example.com/news/1/",
            "summary": "Другой текст",
        },
    )

    news = fetch_rss_news({"Источник": "https://example.com/rss"})

    assert len(news) == 1


@patch("app.news.rss_parser._fetch_feed")
def test_fetch_rss_news_removes_duplicate_titles(mock_fetch_feed):
    mock_fetch_feed.side_effect = [
        make_feed(
            {
                "title": "ЦБ изменил ставку!",
                "link": "https://example.com/news/1",
            }
        ),
        make_feed(
            {
                "title": "ЦБ изменил ставку",
                "link": "https://example.org/news/2",
            }
        ),
    ]

    news = fetch_rss_news(
        {
            "Источник 1": "https://example.com/rss",
            "Источник 2": "https://example.org/rss",
        }
    )

    assert len(news) == 1


@patch("app.news.rss_parser._fetch_feed")
def test_fetch_rss_news_skips_entries_without_title_or_link(mock_fetch_feed):
    mock_fetch_feed.return_value = make_feed(
        {"title": "", "link": "https://example.com/news/1"},
        {"title": "Нет ссылки", "link": ""},
    )

    news = fetch_rss_news({"Источник": "https://example.com/rss"})

    assert news == []


def test_fetch_rss_news_rejects_invalid_limit():
    try:
        fetch_rss_news(
            {"Источник": "https://example.com/rss"},
            limit_per_source=0,
        )
    except ValueError as exc:
        assert "не меньше 1" in str(exc)
    else:
        raise AssertionError("Ожидалась ошибка ValueError")


@patch("app.news.rss_parser._fetch_feed")
def test_fetch_rss_news_continues_when_one_source_raises(mock_fetch_feed):
    mock_fetch_feed.side_effect = [
        RuntimeError("RSS source unavailable"),
        make_feed(
            {
                "title": "Вторая лента работает",
                "link": "https://example.com/news/2",
                "summary": "Текст новости",
            }
        ),
    ]

    news = fetch_rss_news(
        {
            "Недоступный источник": "https://broken.example/rss",
            "Рабочий источник": "https://working.example/rss",
        }
    )

    assert len(news) == 1
    assert news[0].title == "Вторая лента работает"
    assert news[0].publisher == "Рабочий источник"


@patch("app.news.rss_parser._fetch_feed")
def test_fetch_rss_news_returns_empty_list_for_empty_feed(mock_fetch_feed):
    mock_fetch_feed.return_value = make_feed()

    news = fetch_rss_news({"Пустой источник": "https://example.com/rss"})

    assert news == []
