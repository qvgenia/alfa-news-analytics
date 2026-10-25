
import os
from openai import OpenAI


def main() -> None:
    api_key = os.getenv("LLM_API_KEY")

    if not api_key:
        print("ОШИБКА: переменная LLM_API_KEY не задана.")
        print("Сначала нужно безопасно настроить переменные окружения.")
        return

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv(
            "LLM_BASE_URL",
            "https://changellenge.up.railway.app/v1",
        ),
        timeout=30.0,
    )

    try:
        response = client.chat.completions.create(
            model=os.getenv(
                "LLM_MODEL",
                "deepseek/deepseek-v4.1-flash",
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Ответь одним предложением на русском: "
                        "зачем бизнесу анализировать новости?"
                    ),
                }
            ],
            max_tokens=100,
        )

        print("ПОДКЛЮЧЕНИЕ УСПЕШНО.")
        print(response.choices[0].message.content)

    except Exception as exc:
        print(f"ОШИБКА ПОДКЛЮЧЕНИЯ: {type(exc).__name__}")
        print("Текст ошибки:", str(exc)[:500])


if __name__ == "__main__":
    main()
