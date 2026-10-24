
from dataclasses import dataclass


@dataclass
class InterpretedQuestion:
    original_question: str
    normalized_question: str
    needs_news: bool


def interpret_question(question: str) -> InterpretedQuestion:
    """Подготавливает вопрос для дальнейшей обработки агентом."""
    normalized = " ".join(question.split())

    news_keywords = (
        "новост",
        "событи",
        "рын",
        "отрасл",
        "компани",
        "контрагент",
        "санкци",
        "закон",
        "регулирован",
    )

    lowered = normalized.casefold()
    needs_news = any(keyword in lowered for keyword in news_keywords)

    return InterpretedQuestion(
        original_question=question,
        normalized_question=normalized,
        needs_news=needs_news,
    )
