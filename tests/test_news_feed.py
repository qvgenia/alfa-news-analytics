from unittest.mock import patch

from app.contracts import ClientProfile
from app.news.news_feed import get_ranked_news_feed


@patch("app.news.news_feed.rank_news")
@patch("app.news.news_feed.news_fetch_tool")
def test_get_ranked_news_feed_fetches_and_ranks_news(
    mock_fetch,
    mock_rank,
):
    client = ClientProfile(client_id="test-client")
    news_items = [object()]
    ranked_items = [object()]

    mock_fetch.return_value = news_items
    mock_rank.return_value = ranked_items

    result = get_ranked_news_feed(client, limit_per_source=10)

    mock_fetch.assert_called_once_with(limit_per_source=10)
    mock_rank.assert_called_once_with(news_items, client)
    assert result is ranked_items


@patch("app.news.news_feed.rank_news")
@patch("app.news.news_feed.news_fetch_tool")
def test_get_ranked_news_feed_returns_empty_result(
    mock_fetch,
    mock_rank,
):
    client = ClientProfile(client_id="test-client")
    mock_fetch.return_value = []
    mock_rank.return_value = []

    result = get_ranked_news_feed(client)

    mock_fetch.assert_called_once_with(limit_per_source=50)
    mock_rank.assert_called_once_with([], client)
    assert result == []
