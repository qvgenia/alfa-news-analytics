from fastapi import FastAPI

from app.demo_data import build_demo_profile, build_demo_ranked_news
from dotenv import load_dotenv

load_dotenv()
from app.insight_routes import (
    register_profile,
    register_ranked_news,
    router as insight_router,
)


app = FastAPI(
    title="Alfa News Analytics",
    description="Персонализированная новостная аналитика для бизнеса",
    version="0.1.0",
)

app.include_router(insight_router)

# Демо-данные: временно, пока не подключены сервисы A и B.
register_profile(build_demo_profile())
register_ranked_news(build_demo_ranked_news())


@app.get("/health")
def health_check() -> dict[str, str]:
    """Проверяет, что сервер запущен."""
    return {"status": "ok"}
