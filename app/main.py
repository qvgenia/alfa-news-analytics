
from fastapi import FastAPI

from app.insight_routes import router as insight_router


app = FastAPI(
    title="Alfa News Analytics",
    description="Персонализированная новостная аналитика для бизнеса",
    version="0.1.0",
)

app.include_router(insight_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Проверяет, что сервер запущен."""
    return {"status": "ok"}
