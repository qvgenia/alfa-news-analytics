
from fastapi import APIRouter, HTTPException

from app.contracts import (
    AskRequest,
    AskResponse,
    ClientProfile,
    RankedNewsItem,
)
from app.insight_orchestrator import InsightOrchestrator


router = APIRouter(prefix="/insights", tags=["Insights"])


# Временное хранилище для демонстрации.
# В полноценной интеграции данные должны поступать
# из существующих сервисов новостей и профилей.
_profiles: dict[str, ClientProfile] = {}
_ranked_news: dict[str, RankedNewsItem] = {}

_orchestrator = InsightOrchestrator()


def register_profile(profile: ClientProfile) -> None:
    """Регистрирует профиль для демонстрационного вызова."""
    _profiles[profile.client_id] = profile


def register_ranked_news(item: RankedNewsItem) -> None:
    """Регистрирует ранжированную новость для демонстрации."""
    _ranked_news[item.news.news_id] = item


@router.post("/generate", response_model=AskResponse)
async def generate_insight(request: AskRequest) -> AskResponse:
    """Формирует Insight по новости для конкретного клиента."""

    profile = _profiles.get(request.client_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Профиль клиента не найден.",
        )

    if request.news_id:
        item = _ranked_news.get(request.news_id)
        if item is None:
            raise HTTPException(
                status_code=404,
                detail="Ранжированная новость не найдена.",
            )
        if item.relevance.client_id != request.client_id:
            raise HTTPException(
                status_code=403,
                detail="Новость не предназначена для указанного клиента.",
            )
    else:
        candidates = [
            candidate
            for candidate in _ranked_news.values()
            if candidate.relevance.client_id == request.client_id
        ]
        if not candidates:
            raise HTTPException(
                status_code=404,
                detail="Для клиента нет ранжированных новостей.",
            )
        item = max(candidates, key=lambda candidate: candidate.relevance.score)

    try:
        insight = await _orchestrator.create_insight(
            ranked_news=item,
            profile=profile,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Не удалось сформировать Insight.",
        ) from exc

    return AskResponse(
        client_id=request.client_id,
        news_id=item.news.news_id,
        answer=insight.why_it_matters,
        insight=insight,
        source_refs=insight.source_refs,
        limitations=insight.limitations,
    )
