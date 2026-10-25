"""Hybrid retrieval combining lexical and semantic rankings with RRF."""

from __future__ import annotations

from typing import Any

from app.rag.retriever import search_chunks
from app.rag.semantic_retriever import SemanticRetriever


class HybridRetriever:
    """Fuse lexical and semantic search rankings at the document-page level."""

    def __init__(
        self,
        chunks: list[dict[str, Any]],
        semantic_retriever: SemanticRetriever | None = None,
        rrf_k: int = 60,
    ) -> None:
        self.chunks = chunks
        self.semantic_retriever = semantic_retriever or SemanticRetriever(chunks)
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        top_k: int = 5,
        candidate_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Return unique pages ranked by fused lexical and semantic scores."""
        if top_k <= 0 or candidate_k <= 0 or not query.strip():
            return []

        lexical_results = search_chunks(
            query, self.chunks, top_k=candidate_k
        )
        semantic_results = self.semantic_retriever.search(
            query, top_k=candidate_k
        )

        scores: dict[tuple[Any, Any], float] = {}
        representatives: dict[tuple[Any, Any], dict[str, Any]] = {}

        for ranked_results in (lexical_results, semantic_results):
            seen_pages: set[tuple[Any, Any]] = set()

            for rank, chunk in enumerate(ranked_results, start=1):
                page_key = (chunk.get("document"), chunk.get("page"))

                # Each page contributes at most once per ranking.
                if page_key in seen_pages:
                    continue
                seen_pages.add(page_key)

                scores[page_key] = scores.get(page_key, 0.0) + (
                    1.0 / (self.rrf_k + rank)
                )
                representatives.setdefault(page_key, dict(chunk))

        ranked_pages = sorted(
            scores,
            key=lambda page: scores[page],
            reverse=True,
        )

        results = []
        for page_key in ranked_pages[:top_k]:
            result = representatives[page_key]
            result["score"] = scores[page_key]
            results.append(result)

        return results
