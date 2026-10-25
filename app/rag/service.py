
"""Сервис поиска по PDF-отчётам."""

from pathlib import Path
from typing import Any

from app.rag.chunker import chunk_pages
from app.rag.pdf_loader import load_reports
from app.rag.semantic_retriever import SemanticRetriever


class ReportSearchService:
    """Загружает отчёты и ищет релевантные фрагменты."""

    def __init__(self, reports_dir: str | Path = "data/reports") -> None:
        pages = load_reports(reports_dir)
        self.chunks = chunk_pages(pages)
        self.retriever = SemanticRetriever(self.chunks)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Возвращает фрагменты отчётов по релевантности."""
        if not query.strip() or top_k <= 0:
            return []

        return self.retriever.search(query, top_k=top_k)
