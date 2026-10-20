
from app.contracts import ClientProfile
from app.tools.news_fetch import news_fetch_tool


def test_news_fetch_returns_ranked_items():
    client = ClientProfile(
        client_id="demo-client",
        industry_name="логистика",
        region="Москва",
    )

    items = news_fetch_tool(client)

    assert len(items) == 3
    assert all(
        item.relevance.client_id == "demo-client"
        for item in items
    )
    assert all(
        item.news.news_id == item.relevance.news_id
        for item in items
    )


def test_news_fetch_sorts_by_relevance():
    client = ClientProfile(
        client_id="demo-client",
        industry_name="логистика",
    )

    items = news_fetch_tool(client)
    scores = [item.relevance.score for item in items]

    assert scores == sorted(scores, reverse=True)
    assert items[0].news.news_id == "demo-002"


def test_news_fetch_respects_limit():
    client = ClientProfile(client_id="demo-client")

    assert len(news_fetch_tool(client, limit=1)) == 1
    assert news_fetch_tool(client, limit=0) == []
