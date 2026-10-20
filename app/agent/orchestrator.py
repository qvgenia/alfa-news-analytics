
from dataclasses import dataclass

from app.agent.interpretation import interpret_question
from app.llm.gateway import LLMGateway, get_llm_gateway


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
            else "Ответь на вопрос пользователя, не выдумывая факты."
        )

        answer = self.llm.generate(
            system_prompt=(
                "Ты помощник по бизнес-новостям. "
                "Не выдумывай факты и явно обозначай ограничения. "
                f"{context_note}"
            ),
            user_prompt=interpreted.normalized_question,
        )

        return AskResult(answer=answer)
