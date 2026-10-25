
import asyncio
import json
import os
import urllib.error
import urllib.request
from typing import Any


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
    """Клиент LLM с явными режимами production и mock."""

    def __init__(self) -> None:
        self.mode = os.getenv("LLM_MODE", "production").strip().lower()
        self.base_url = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
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
                raise ValueError(
                    "LLM_BASE_URL должен начинаться с http:// или https://."
                )
            if not self.api_key:
                raise ValueError("В production необходимо задать LLM_API_KEY.")

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Генерирует JSON-объект и проверяет его формат."""
        if not system_prompt.strip() or not user_prompt.strip():
            raise ValueError("System prompt и user prompt не должны быть пустыми.")

        if self.mode == "mock":
            result: dict[str, Any] = {
                "mock": True,
                "message": "Ответ создан в mock-режиме.",
            }
            return self._validate_result(result, response_schema)

        return await asyncio.to_thread(
            self._generate_json_sync,
            system_prompt,
            user_prompt,
            response_schema,
        )

    def _generate_json_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Выполняет синхронный HTTP-запрос внутри рабочего потока."""
        url = (
            self.base_url
            if self.base_url.endswith("/chat/completions")
            else f"{self.base_url}/chat/completions"
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        user_prompt
                        + "\n\nВерни только один корректный JSON-объект без "
                        "Markdown и дополнительного текста."
                    ),
                },
            ],
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout
            ) as response:
                raw_response = response.read().decode("utf-8")

        except TimeoutError as exc:
            raise GatewayTimeoutError("Истекло время ожидания ответа LLM.") from exc
        except urllib.error.HTTPError as exc:
            if exc.code in {408, 504}:
                raise GatewayTimeoutError(
                    f"LLM вернула HTTP {exc.code}."
                ) from exc
            raise GatewayResponseError(
                f"LLM вернула HTTP {exc.code}."
            ) from exc
        except (urllib.error.URLError, OSError) as exc:
            if isinstance(getattr(exc, "reason", None), TimeoutError):
                raise GatewayTimeoutError(
                    "Истекло время ожидания ответа LLM."
                ) from exc
            raise GatewayConnectionError(
                "Не удалось подключиться к LLM."
            ) from exc

        try:
            provider_data = json.loads(raw_response)
            content = provider_data["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Пустой content.")
            result = json.loads(content)
        except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise GatewayInvalidResponseError(
                "LLM вернула пустой или некорректный JSON."
            ) from exc

        if not isinstance(result, dict):
            raise GatewayInvalidResponseError(
                "Ответ LLM должен быть JSON-объектом."
            )

        return self._validate_result(result, response_schema)

    @staticmethod
    def _validate_result(
        result: dict[str, Any],
        response_schema: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Проверяет тип результата и основные ограничения схемы."""
        if not isinstance(result, dict):
            raise GatewayInvalidResponseError(
                "Ответ должен быть JSON-объектом."
            )

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

        for field, definition in properties.items():
            if field not in result:
                continue

            expected_type = definition.get("type")
            value = result[field]

            type_checks = {
                "object": lambda v: isinstance(v, dict),
                "array": lambda v: isinstance(v, list),
                "string": lambda v: isinstance(v, str),
                "integer": lambda v: isinstance(v, int)
                and not isinstance(v, bool),
                "number": lambda v: isinstance(v, (int, float))
                and not isinstance(v, bool),
                "boolean": lambda v: isinstance(v, bool),
                "null": lambda v: v is None,
            }

            check = type_checks.get(expected_type)
            if check is not None and not check(value):
                raise GatewayInvalidResponseError(
                    f"Поле {field} должно иметь тип {expected_type}."
                )

        return result
