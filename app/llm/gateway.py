
"""Единый шлюз для OpenAI-совместимых LLM API."""

import json
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings


class LLMGatewayError(RuntimeError):
    """Ошибка при обращении к языковой модели."""


class LLMGateway(Protocol):
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> str:
        ...


class MockLLMGateway:
    """Заглушка для разработки без API-ключа."""

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


class OpenAICompatibleGateway:
    """Шлюз для API с форматом /chat/completions."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 30,
        default_max_tokens: int = 1200,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.default_max_tokens = default_max_tokens

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> str:
        if not self.base_url or not self.model or not self.api_key:
            raise LLMGatewayError(
                "Для LLM нужны LLM_BASE_URL, LLM_MODEL и LLM_API_KEY."
            )

        if self.base_url.endswith("/chat/completions"):
            endpoint = self.base_url
        else:
            endpoint = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens or self.default_max_tokens,
            "temperature": 0,
        }

        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                result = json.loads(response.read().decode("utf-8"))

        except HTTPError as exc:
            # Не выводим тело ответа: провайдер может вернуть чувствительные данные.
            raise LLMGatewayError(
                f"LLM API вернул HTTP {exc.code}."
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise LLMGatewayError(
                "Не удалось подключиться к LLM API или истекло время ожидания."
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise LLMGatewayError(
                "LLM API вернул некорректный JSON."
            ) from exc

        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMGatewayError(
                "В ответе LLM API отсутствует текст генерации."
            ) from exc

        if not isinstance(content, str):
            raise LLMGatewayError(
                "LLM API вернул ответ неожиданного формата."
            )

        return content


def get_llm_gateway() -> LLMGateway:
    """Создаёт шлюз по настройкам окружения."""
    provider = settings.llm_provider.strip().lower()

    if not provider and not settings.llm_api_key:
        return MockLLMGateway()

    if provider not in {"openai", "openai-compatible", "openai_compatible"}:
        raise LLMGatewayError(
            f"Неподдерживаемый LLM_PROVIDER: {provider!r}. "
            "Используйте openai-compatible для совместимого API."
        )

    if not settings.llm_api_key:
        raise LLMGatewayError("Не задан LLM_API_KEY.")

    if not settings.llm_base_url:
        raise LLMGatewayError("Не задан LLM_BASE_URL.")

    if not settings.llm_model:
        raise LLMGatewayError("Не задан LLM_MODEL.")

    return OpenAICompatibleGateway(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
        default_max_tokens=settings.llm_max_tokens,
    )
