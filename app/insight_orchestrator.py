
from app.contracts import (
    ClientProfile,
    Insight,
    RankedNewsItem,
    SourceRef,
)
from app.llm.interpretation import InsightInterpreter


class InsightOrchestrator:
    """Координирует создание Insight для конкретного клиента."""

    def __init__(
        self,
        interpreter: InsightInterpreter | None = None,
    ) -> None:
        self.interpreter = interpreter or InsightInterpreter()

    async def create_insight(
        self,
        ranked_news: RankedNewsItem,
        profile: ClientProfile,
        bank_view: str | None = None,
        bank_sources: list[SourceRef] | None = None,
    ) -> Insight:
        """Проверяет входные данные и запускает интерпретацию новости."""

        if ranked_news.relevance.client_id != profile.client_id:
            raise ValueError(
                "Клиент в результате ранжирования не совпадает с профилем."
            )

        if ranked_news.news.news_id != ranked_news.relevance.news_id:
            raise ValueError(
                "Новость не совпадает с результатом ранжирования."
            )

        return await self.interpreter.interpret(
            ranked_news=ranked_news,
            profile=profile,
            bank_view=bank_view,
            bank_sources=bank_sources,
        )
