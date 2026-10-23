from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.clients.service import get_client_profile
from app.contracts import RankedNewsItem
from app.db.session import get_db
from app.news.news_feed import get_ranked_news_feed

app = FastAPI(
    title="Alfa News Analytics",
    description="Персонализированная новостная аналитика для бизнеса",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Проверяет, что сервер запущен."""
    return {"status": "ok"}


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
