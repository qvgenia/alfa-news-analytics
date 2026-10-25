import asyncio
import json
import logging
import os
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.contracts import (
    AskRequest,
    AskResponse,
    ClientProfile,
    RankedNewsItem,
)
from app.insight_orchestrator import InsightOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["Insights"])


# Демо-данные, зарегистрированные при запуске (см. app/main.py).
_profiles: dict[str, ClientProfile] = {}
_ranked_news: dict[str, RankedNewsItem] = {}

# Профили из JSON-файла (необязательно, вместо базы данных).
PROFILES_FILE = Path(__file__).parent / "demo" / "profiles.json"

FEED_TIMEOUT_SECONDS = 45.0
FEED_CACHE_TTL_SECONDS = 300.0
_feed_cache: dict[str, tuple[float, list[RankedNewsItem]]] = {}

_orchestrator = InsightOrchestrator()


def register_profile(profile: ClientProfile) -> None:
    """Регистрирует профиль для демонстрационного вызова."""
    _profiles[profile.client_id] = profile


def register_ranked_news(item: RankedNewsItem) -> None:
    """Регистрирует ранжированную новость для демонстрации."""
    _ranked_news[item.news.news_id] = item


def _profile_from_file(client_id: str) -> ClientProfile | None:
    """Ищет профиль клиента в app/demo/profiles.json, если файл есть."""
    if not PROFILES_FILE.exists():
        return None
    try:
        raw = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.exception("Не удалось прочитать %s", PROFILES_FILE)
        return None

    items = raw if isinstance(raw, list) else [raw]
    for item in items:
        if isinstance(item, dict) and item.get("client_id") == client_id:
            try:
                return ClientProfile.model_validate(item)
            except ValueError:
                logger.exception("Профиль %s не прошёл проверку", client_id)
                return None
    return None


async def _load_live_feed(profile: ClientProfile) -> list[RankedNewsItem]:
    """Получает ранжированную ленту Ники (с кэшем и тайм-аутом)."""
    cached = _feed_cache.get(profile.client_id)
    now = time.monotonic()
    if cached and now - cached[0] < FEED_CACHE_TTL_SECONDS:
        return cached[1]

    # Импорт внутри функции: если модуля нет в ветке, приложение не падает.
    from app.news.news_feed import get_ranked_news_feed

    feed = await asyncio.wait_for(
        asyncio.to_thread(get_ranked_news_feed, profile),
        timeout=FEED_TIMEOUT_SECONDS,
    )
    _feed_cache[profile.client_id] = (now, feed)
    return feed


async def _select_news(
    request: AskRequest,
    profile: ClientProfile,
    notes: list[str],
) -> RankedNewsItem:
    """Выбирает новость: из живой ленты, а при её недоступности — демо."""
    use_live = os.getenv("NEWS_SOURCE", "live").strip().lower() != "demo"

    live: list[RankedNewsItem] = []
    live_failed = False
    if use_live:
        try:
            live = await _load_live_feed(profile)
        except Exception:
            live_failed = True
            logger.exception("Не удалось получить новостную ленту")

    demo = [
        candidate
        for candidate in _ranked_news.values()
        if candidate.relevance.client_id == profile.client_id
    ]

    if request.news_id:
        item = next(
            (c for c in live if c.news.news_id == request.news_id),
            None,
        )
        if item is None:
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
            notes.append("Использована демонстрационная новость.")
        return item

    relevant_live = [
        c
        for c in live
        if c.relevance.client_id == request.client_id
        and c.relevance.score > 0
    ]
    if relevant_live:
        return max(relevant_live, key=lambda c: c.relevance.score)

    if demo:
        if live_failed:
            notes.append(
                "Новостная лента недоступна: использована "
                "демонстрационная новость."
            )
        elif use_live:
            notes.append(
                "В новостной ленте нет новостей с ненулевой релевантностью "
                "для этого клиента: использована демонстрационная новость."
            )
        else:
            notes.append("Использована демонстрационная новость.")
        return max(demo, key=lambda c: c.relevance.score)

    if live_failed:
        raise HTTPException(
            status_code=503,
            detail="Новостная лента недоступна.",
        )
    raise HTTPException(
        status_code=404,
        detail="Для клиента нет релевантных новостей.",
    )


@router.post("/generate", response_model=AskResponse)
async def generate_insight(request: AskRequest) -> AskResponse:
    """Формирует Insight по новости для конкретного клиента."""
    notes: list[str] = []

    profile = _profiles.get(request.client_id)
    if profile is not None:
        notes.append("Профиль клиента демонстрационный.")
    else:
        profile = _profile_from_file(request.client_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Профиль клиента не найден.",
        )

    item = await _select_news(request, profile, notes)

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
        logger.exception("Не удалось сформировать Insight")
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
        limitations=insight.limitations + notes,
    )
