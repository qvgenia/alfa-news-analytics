
from dataclasses import dataclass

from app.agent.interpretation import interpret_question
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.rag.router import get_search_service


@dataclass
class AskResult:
    answer: str
    status: str = "ok"


class AgentOrchestrator:
    """Координирует обработку пользовательского вопроса."""

    def __init__(self, llm: LLMGateway | None = None) -> None:
        self.llm = llm or get_llm_gateway()

    def ask(self, question: str) -> AskResult:
        interpreted = interpret_question(question)

        if not interpreted.normalized_question:
            return AskResult(
                answer="Пожалуйста, напишите вопрос.",
                status="invalid_request",
            )

        context_note = (
            "Для ответа могут потребоваться актуальные новости."
            if interpreted.needs_news
            else "Отвечай на вопрос пользователя, не выдумывая факты."
        )

        prompt_parts: list[str] = []

        search_service = get_search_service()
        if search_service is not None:
            results = search_service.search(
                interpreted.normalized_question,
                top_k=5,
            )

            if results:
                prompt_parts.append(
                    "Ниже приведены фрагменты PDF-отчётов. "
                    "Используй их как источник фактов. "
                    "Если информации недостаточно, прямо скажи об этом."
                )

                for item in results:
                    prompt_parts.append(
                        f"Документ: {item['document']}\n"
                        f"Страница: {item['page']}\n"
                        f"Фрагмент: {item['text']}"
                    )
            else:
                prompt_parts.append(
                    "Поиск по PDF-отчётам не нашёл подходящих фрагментов. "
                    "Не утверждай, что ответ подтверждён этими отчётами."
                )

        prompt_parts.append(
            f"Вопрос пользователя: {interpreted.normalized_question}"
        )

        answer = self.llm.generate(
            system_prompt=(
                "Ты помощник по бизнес-аналитике. "
                "Не выдумывай факты и явно обозначай ограничения. "
                f"{context_note}"
            ),
            user_prompt="\n\n".join(prompt_parts),
        )

        return AskResult(answer=answer)
