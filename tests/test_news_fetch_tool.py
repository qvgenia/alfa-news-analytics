from unittest.mock import patch

from app.news.news_fetch_tool import news_fetch_tool


@patch("app.news.news_fetch_tool.fetch_rss_news")
def test_news_fetch_tool_uses_default_limit(mock_fetch):
    mock_fetch.return_value = []

    result = news_fetch_tool()

    mock_fetch.assert_called_once_with(limit_per_source=50)
    assert result == []


@patch("app.news.news_fetch_tool.fetch_rss_news")
def test_news_fetch_tool_passes_custom_limit(mock_fetch):
    expected_news = [object()]
    mock_fetch.return_value = expected_news

    result = news_fetch_tool(limit_per_source=10)

    mock_fetch.assert_called_once_with(limit_per_source=10)
    assert result is expected_news
