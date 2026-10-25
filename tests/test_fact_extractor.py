from app.contracts import NewsItem

def make_news() -> NewsItem:
    return NewsItem(
        news_id="news-001",
        title="Компания объявила об инвестициях",
        text="Компания объявила об инвестициях в новый завод.",
        publisher="Тестовый источник",
        source_url="https://example.com/news-001",
    )


import json

from app.news.fact_extractor import extract_news_facts


class FakeLLMGateway:
    def __init__(self, response: str):
        self.response = response
        self.last_user_prompt = ""

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> str:
        self.last_user_prompt = user_prompt
        return self.response


def test_extract_news_facts_parses_llm_json():
    news = make_news()
    gateway = FakeLLMGateway(
        json.dumps(
            {
                "facts": [
                    {
                        "text": "Компания инвестирует в новый завод.",
                        "confidence": 0.95,
                    },
                    {
                        "text": "Компания инвестирует в новый завод.",
                        "confidence": 0.8,
                    },
                ],
            },
            ensure_ascii=False,
        )
    )

    facts = extract_news_facts(news, gateway)

    assert len(facts) == 1
    assert facts[0].text == "Компания инвестирует в новый завод."
    assert facts[0].confidence == 0.95
    assert facts[0].source_id == "news:news-001"
    assert json.loads(gateway.last_user_prompt)["title"] == news.title


def test_extract_news_facts_returns_empty_on_invalid_json():
    facts = extract_news_facts(
        make_news(),
        FakeLLMGateway("это не JSON"),
    )

    assert facts == []


def test_extract_news_facts_ignores_invalid_entries():
    gateway = FakeLLMGateway(
        json.dumps(
            {
                "facts": [
                    {"text": "Компания открыла завод.", "confidence": 0.9},
                    {"text": "Факт с неверной уверенностью", "confidence": 4},
                    {"text": "   ", "confidence": 0.7},
                    "не объект",
                ],
            },
            ensure_ascii=False,
        )
    )

    facts = extract_news_facts(make_news(), gateway)

    assert len(facts) == 2
    assert facts[0].confidence == 0.9
    assert facts[1].confidence is None


def test_extract_news_facts_handles_gateway_error():
    class BrokenGateway:
        def generate(
            self,
            *,
            system_prompt: str,
            user_prompt: str,
            max_tokens: int | None = None,
        ) -> str:
            raise RuntimeError("provider unavailable")

    assert extract_news_facts(make_news(), BrokenGateway()) == []
