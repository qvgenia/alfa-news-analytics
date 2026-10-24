
from typing import Any, Protocol

from app.config import settings


class LLMGatewayError(RuntimeError):
    """Ошибка при обращении к языковой модели."""


class LLMGateway(Protocol):
    """Единый интерфейс для провайдеров языковых моделей."""

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> str:
        """Возвращает текстовый ответ модели."""
        ...


class MockLLMGateway:
    """Заглушка для разработки без API-ключа и платных запросов."""

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> str:
        del system_prompt, max_tokens
        return (
            "Тестовый ответ LLM Gateway. "
            f"Получен запрос длиной {len(user_prompt)} символов."
        )


def get_llm_gateway() -> LLMGateway:
    """Возвращает доступный шлюз для работы с LLM."""
    if not settings.llm_provider or not settings.llm_api_key:
        return MockLLMGateway()

    raise LLMGatewayError(
        "Провайдер LLM ещё не подключён. "
        "Реализацию добавим после выбора API."
    )
