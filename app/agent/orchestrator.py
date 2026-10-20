
from dataclasses import dataclass

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
        question = question.strip()
        if not question:
            return AskResult(
                answer="Пожалуйста, напишите вопрос.",
                status="invalid_request",
            )

        answer = self.llm.generate(
            system_prompt=(
                "Ты помощник по бизнес-новостям. "
                "Не выдумывай факты и явно обозначай ограничения."
            ),
            user_prompt=question,
        )

        return AskResult(answer=answer)
