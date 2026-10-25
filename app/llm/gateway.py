
"""Единый шлюз для JSON-аналитики и текстовой генерации LLM."""

import asyncio
import json
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings


class GatewayError(RuntimeError):
    """Базовая ошибка LLM Gateway."""


class GatewayTimeoutError(GatewayError):
    """LLM не ответила за отведённое время."""


class GatewayConnectionError(GatewayError):
    """Не удалось подключиться к LLM."""


class GatewayResponseError(GatewayError):
    """Провайдер вернул HTTP-ошибку или ошибку API."""


class GatewayInvalidResponseError(GatewayError):
    """Ответ пустой или имеет некорректный формат."""


# Совместимость с интерфейсом ассистента.
LLMGatewayError = GatewayError


class TextGateway(Protocol):
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> str:
        ...


class LLMGateway:
    """Шлюз с методами generate() и generate_json()."""

    def __init__(self) -> None:
        self.mode = settings.app_env
        self.base_url = settings.llm_base_url.strip().rstrip("/")
        self.api_key = settings.llm_api_key.strip()
        self.model = settings.llm_model.strip()
        self.timeout = settings.llm_timeout_seconds
        self.max_tokens = settings.llm_max_tokens

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> str:
        """Возвращает текст ответа LLM."""
        result = self._request(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens or self.max_tokens,
            json_mode=False,
        )
        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GatewayInvalidResponseError(
                "В ответе LLM отсутствует текст генерации."
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise GatewayInvalidResponseError("LLM вернула пустой ответ.")
        return content

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Возвращает JSON-объект с необязательной проверкой схемы."""
        if not system_prompt.strip() or not user_prompt.strip():
            raise ValueError("System prompt и user prompt не должны быть пустыми.")

        if not self.api_key and not self.base_url and not self.model:
            result: dict[str, Any] = {
                "mock": True,
                "message": "Ответ создан в mock-режиме.",
            }
            return self._validate_result(result, response_schema)

        content = await asyncio.to_thread(
            self.generate,
            system_prompt=system_prompt,
            user_prompt=(
                user_prompt
                + "\n\nВерни только один корректный JSON-объект без Markdown."
            ),
            max_tokens=self.max_tokens,
        )

        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise GatewayInvalidResponseError(
                "LLM вернула некорректный JSON."
            ) from exc

        if not isinstance(result, dict):
            raise GatewayInvalidResponseError(
                "Ответ LLM должен быть JSON-объектом."
            )
        return self._validate_result(result, response_schema)

    def _request(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        json_mode: bool,
    ) -> dict[str, Any]:
        if not self.base_url or not self.model or not self.api_key:
            raise GatewayError(
                "Для LLM необходимо настроить LLM_BASE_URL, "
                "LLM_MODEL и LLM_API_KEY."
            )

        endpoint = (
            self.base_url
            if self.base_url.endswith("/chat/completions")
            else f"{self.base_url}/chat/completions"
        )
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

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
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in {408, 504}:
                raise GatewayTimeoutError(
                    f"Истекло время ожидания ответа LLM (HTTP {exc.code})."
                ) from exc
            raise GatewayResponseError(
                f"LLM API вернул HTTP {exc.code}."
            ) from exc
        except (TimeoutError, URLError, OSError) as exc:
            if isinstance(exc, TimeoutError) or isinstance(
                getattr(exc, "reason", None), TimeoutError
            ):
                raise GatewayTimeoutError("Истекло время ожидания ответа LLM.") from exc
            raise GatewayConnectionError(
                "Не удалось подключиться к LLM API."
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise GatewayInvalidResponseError(
                "LLM API вернул некорректный JSON."
            ) from exc

        if not isinstance(data, dict):
            raise GatewayInvalidResponseError(
                "Ответ LLM API должен быть JSON-объектом."
            )
        return data

    @staticmethod
    def _validate_result(
        result: dict[str, Any],
        response_schema: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Проверяет обязательные поля и основные JSON-типы."""
        if response_schema is None:
            return result

        required = response_schema.get("required", [])
        properties = response_schema.get("properties", {})

        for field in required:
            if field not in result:
                raise GatewayInvalidResponseError(
                    f"В ответе отсутствует обязательное поле: {field}."
                )

        if response_schema.get("additionalProperties") is False:
            extra_fields = set(result) - set(properties)
            if extra_fields:
                raise GatewayInvalidResponseError(
                    f"Лишние поля в ответе: {', '.join(sorted(extra_fields))}."
                )

        checks = {
            "object": lambda value: isinstance(value, dict),
            "array": lambda value: isinstance(value, list),
            "string": lambda value: isinstance(value, str),
            "integer": lambda value: isinstance(value, int)
            and not isinstance(value, bool),
            "number": lambda value: isinstance(value, (int, float))
            and not isinstance(value, bool),
            "boolean": lambda value: isinstance(value, bool),
            "null": lambda value: value is None,
        }

        for field, definition in properties.items():
            if field not in result:
                continue
            expected = definition.get("type")
            check = checks.get(expected)
            if check and not check(result[field]):
                raise GatewayInvalidResponseError(
                    f"Поле {field} должно иметь тип {expected}."
                )
        return result


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
        return json.dumps({"facts": []}, ensure_ascii=False)


def get_llm_gateway() -> LLMGateway | MockLLMGateway:
    provider = settings.llm_provider.strip().lower()

    # Если провайдер не задан, выбираем подходящий режим автоматически.
    if not provider:
        if settings.llm_base_url.strip() and settings.llm_model.strip():
            provider = "openai-compatible"
        else:
            return MockLLMGateway()

    if provider in {"mock", "test"}:
        return MockLLMGateway()

    if provider in {"openai", "openai-compatible", "openai_compatible"}:
        return LLMGateway()

    raise GatewayError(
        f"Неподдерживаемый LLM_PROVIDER: {provider!r}."
    )
