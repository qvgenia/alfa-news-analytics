from app.agent.orchestrator import AgentOrchestrator


class FakeLLM:
    def __init__(self):
        self.system_prompt = ""
        self.user_prompt = ""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return "Тестовый ответ"


class FakeSearchService:
    def __init__(self, results):
        self.results = results
        self.query = None
        self.top_k = None

    def search(self, query: str, top_k: int = 5):
        self.query = query
        self.top_k = top_k
        return self.results


def test_ask_includes_pdf_context(monkeypatch):
    from app.agent import orchestrator

    search_service = FakeSearchService(
        [
            {
                "document": "Бонд_Бриф_14092026.pdf",
                "page": 3,
                "text": "Чистый долг компании составляет 100 млн рублей.",
                "score": 0.95,
            }
        ]
    )
    llm = FakeLLM()

    monkeypatch.setattr(
        orchestrator, "get_search_service", lambda: search_service
    )

    result = AgentOrchestrator(llm=llm).ask(
        "Каким был чистый долг компании?"
    )

    assert result.status == "ok"
    assert result.answer == "Тестовый ответ"
    assert search_service.top_k == 5
    assert "Бонд_Бриф_14092026.pdf" in llm.user_prompt
    assert "Страница: 3" in llm.user_prompt
    assert "100 млн рублей" in llm.user_prompt
    assert "Каким был чистый долг компании?" in llm.user_prompt


def test_ask_handles_empty_search_results(monkeypatch):
    from app.agent import orchestrator

    search_service = FakeSearchService([])
    llm = FakeLLM()

    monkeypatch.setattr(
        orchestrator, "get_search_service", lambda: search_service
    )

    result = AgentOrchestrator(llm=llm).ask(
        "Какие показатели есть в отчёте?"
    )

    assert result.status == "ok"
    assert result.answer == "Тестовый ответ"
    assert "не нашёл подходящих фрагментов" in llm.user_prompt
    assert "Какие показатели есть в отчёте?" in llm.user_prompt


def test_ask_rejects_empty_question():
    llm = FakeLLM()

    result = AgentOrchestrator(llm=llm).ask("   ")

    assert result.status == "invalid_request"
    assert result.answer == "Пожалуйста, напишите вопрос."
    assert llm.user_prompt == ""
