from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.agent.routes import router as assistant_router
from app.clients.router import router as clients_router
from app.clients.service import get_client_profile
from app.contracts import RankedNewsItem
from app.db.session import get_db
from app.demo.profile_store import get_demo_profile, load_demo_profiles
from app.demo_data import build_demo_profile, build_demo_ranked_news
from app.insight_routes import (
    register_profile,
    register_ranked_news,
    router as insight_router,
)
from app.news.news_feed import get_ranked_news_feed
from app.rag.router import router as reports_router
from app.rag.router import set_search_service
from app.rag.service import ReportSearchService

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    reports_dir = Path("data/reports")

    if reports_dir.exists() and any(reports_dir.glob("*.pdf")):
        set_search_service(ReportSearchService(reports_dir))

    yield


app = FastAPI(
    title="Alfa News Analytics",
    description="Персонализированная новостная аналитика для бизнеса",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(clients_router)
app.include_router(reports_router)
app.include_router(assistant_router)
app.include_router(insight_router)

# Демо-данные для аналитики новостей.
register_profile(build_demo_profile())
register_ranked_news(build_demo_ranked_news())


@app.get("/health")
def health_check() -> dict[str, str]:
    """Проверяет, что сервер запущен."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    """Возвращает веб-интерфейс аналитики."""
    html_path = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/feed", response_model=list[RankedNewsItem])
def get_news_feed(
    client_id: str,
    limit_per_source: int = 50,
    db: Session = Depends(get_db),
) -> list[RankedNewsItem]:
    """Возвращает персонализированную новостную ленту клиента."""
    client = get_client_profile(client_id, db)

    if client is None:
        raise HTTPException(
            status_code=404,
            detail=f"Профиль клиента '{client_id}' не найден",
        )

    return get_ranked_news_feed(
        client=client,
        limit_per_source=limit_per_source,
    )


@app.get("/demo/profiles")
def get_demo_profiles() -> list[dict[str, str]]:
    """Возвращает список доступных демо-профилей."""
    return [
        {"client_id": client_id}
        for client_id in load_demo_profiles()
    ]


@app.get("/demo/feed", response_model=list[RankedNewsItem])
def get_demo_news_feed(
    client_id: str,
    limit_per_source: int = 50,
) -> list[RankedNewsItem]:
    """Новостная лента на синтетическом профиле без PostgreSQL."""
    client = get_demo_profile(client_id)

    if client is None:
        raise HTTPException(
            status_code=404,
            detail=f"Демо-профиль '{client_id}' не найден",
        )

    return get_ranked_news_feed(
        client=client,
        limit_per_source=limit_per_source,
    )
