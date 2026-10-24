
"""LLM Gateway: единая точка обращения к языковой модели."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GatewayError(Exception):
    """Базовая ошибка LLM Gateway."""


class GatewayTimeoutError(GatewayError):
    """LLM не ответила за отведённое время."""


class GatewayConnectionError(GatewayError):
    """Не удалось подключиться к LLM."""


class GatewayResponseError(GatewayError):
    """Провайдер вернул HTTP-ошибку или ошибку API."""


class GatewayInvalidResponseError(GatewayError):
    """Ответ пустой, некорректный или не соответствует ожидаемой схеме."""


class LLMGateway:
    """Клиент LLM с явными режимами production и mock.

    Переменная LLM_MODE принимает значения:
    - production — реальный HTTP-запрос;
    - mock — локальный ответ для разработки и тестов.

    Автоматического перехода в mock при ошибке конфигурации нет.
    """

    def __init__(self) -> None:
        self.mode = os.getenv("LLM_MODE", "production").strip().lower()
        self.base_url = os.getenv("LLM_BASE_URL", "").strip()
        self.api_key = os.getenv("LLM_API_KEY", "").strip()
        self.model = os.getenv("LLM_MODEL", "").strip()

        try:
            self.timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
            self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2000"))
        except ValueError as exc:
            raise ValueError(
                "LLM_TIMEOUT_SECONDS и LLM_MAX_TOKENS должны быть числами."
            ) from exc

        if self.timeout <= 0:
            raise ValueError("LLM_TIMEOUT_SECONDS должен быть больше нуля.")
        if self.max_tokens <= 0:
            raise ValueError("LLM_MAX_TOKENS должен быть больше нуля.")
        if self.mode not in {"production", "mock"}:
            raise ValueError("LLM_MODE должен быть production или mock.")

        if self.mode == "production":
            if not self.base_url:
                raise ValueError("В production необходимо задать LLM_BASE_URL.")
            if not self.model:
                raise ValueError("В production необходимо задать LLM_MODEL.")
            if not self.base_url.startswith(("http://", "https://")):
                raise ValueError("LLM_BASE_URL должен начинаться с http:// или https://.")

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Генерирует JSON-объект и проверяет его формат."""

        if self.mode == "mock":
            result: dict[str, Any] = {
                "mock": True,
                "message": "Ответ создан в mock-режиме.",
            }
            return self._validate_result(result, response_schema)

        if not system_prompt.strip() or not user_prompt.strip():
            raise ValueError("system_prompt и user_prompt не должны быть пустыми.")

        raw_response = await asyncio.to_thread(
            self._request,
            system_prompt,
            user_prompt,
        )

        if not raw_response or not raw_response.strip():
            raise GatewayInvalidResponseError("Провайдер вернул пустой ответ.")

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise GatewayInvalidResponseError(
                "Ответ провайдера не является корректным JSON."
            ) from exc

        if not isinstance(result, dict):
            raise GatewayInvalidResponseError(
                "Ожидался JSON-объект верхнего уровня."
            )

        return self._validate_result(result, response_schema)

    def _request(self, system_prompt: str, user_prompt: str) -> str:
        """Выполняет HTTP-запрос. Формат совместим с Chat Completions API."""

        if not self.base_url or not self.model:
            raise GatewayResponseError(
                "Не заданы LLM_BASE_URL или LLM_MODEL."
            )

        endpoint = self.base_url.rstrip("/")
        if not endpoint.endswith("/chat/completions"):
            endpoint += "/chat/completions"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except TimeoutError as exc:
            raise GatewayTimeoutError("Истекло время ожидания ответа LLM.") from exc
        except HTTPError as exc:
            if exc.code in {408, 504}:
                raise GatewayTimeoutError(
                    f"Провайдер вернул HTTP {exc.code}."
                ) from exc
            raise GatewayResponseError(
                f"Провайдер вернул HTTP {exc.code}."
            ) from exc
        except (URLError, OSError) as exc:
            if isinstance(exc, URLError) and isinstance(exc.reason, TimeoutError):
                raise GatewayTimeoutError(
                    "Истекло время ожидания ответа LLM."
                ) from exc
            raise GatewayConnectionError(
                "Не удалось подключиться к провайдеру LLM."
            ) from exc

        try:
            envelope = json.loads(body)
            content = envelope["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise GatewayInvalidResponseError(
                "Ответ API не соответствует формату Chat Completions."
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise GatewayInvalidResponseError(
                "Провайдер вернул пустое содержимое."
            )

        return content

    @staticmethod
    def _validate_result(
        result: dict[str, Any],
        response_schema: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Проверяет JSON Schema, если она передана вызывающим кодом."""

        if response_schema is None:
            return result

        try:
            from jsonschema import validate
            from jsonschema.exceptions import ValidationError, SchemaError

            validate(instance=result, schema=response_schema)
        except ImportError as exc:
            raise GatewayInvalidResponseError(
                "Для проверки response_schema установи пакет jsonschema."
            ) from exc
        except (ValidationError, SchemaError) as exc:
            raise GatewayInvalidResponseError(
                "Ответ не соответствует response_schema."
            ) from exc

        return result


# Удобный публичный интерфейс для кода агента.
_default_gateway: LLMGateway | None = None


async def generate_json(
    system_prompt: str,
    user_prompt: str,
    response_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Вызывает настроенный Gateway."""

    global _default_gateway
    if _default_gateway is None:
        _default_gateway = LLMGateway()

    return await _default_gateway.generate_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=response_schema,
    )
