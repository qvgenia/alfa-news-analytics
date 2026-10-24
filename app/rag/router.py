
"""API поиска по PDF-отчётам."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.rag.service import ReportSearchService

router = APIRouter(prefix="/reports", tags=["reports"])

_search_service: ReportSearchService | None = None


def set_search_service(service: ReportSearchService) -> None:
    """Устанавливает подготовленный поисковый индекс."""
    global _search_service
    _search_service = service


def get_search_service() -> ReportSearchService | None:
    """Возвращает текущий сервис поиска по PDF."""
    return _search_service


class ReportSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)


class ReportSearchResult(BaseModel):
    document: str
    page: int
    text: str
    score: float


class ReportSearchResponse(BaseModel):
    query: str
    results: list[ReportSearchResult]


@router.post("/search", response_model=ReportSearchResponse)
def search_reports(request: ReportSearchRequest) -> dict[str, Any]:
    """Ищет подходящие фрагменты в PDF-отчётах."""
    if _search_service is None:
        raise HTTPException(
            status_code=503,
            detail="Индекс отчётов ещё не загружен",
        )

    results = _search_service.search(request.query, request.top_k)

    return {"query": request.query, "results": results}
