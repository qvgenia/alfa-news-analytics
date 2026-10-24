"""Semantic retrieval for RAG chunks using sentence-transformers."""

from __future__ import annotations

from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL_NAME = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)


class SemanticRetriever:
    """Encode chunks once and rank them by cosine similarity to a query."""

    def __init__(
        self,
        chunks: list[dict[str, Any]],
        model_name: str = DEFAULT_MODEL_NAME,
    ) -> None:
        self.chunks = chunks
        self.model = SentenceTransformer(model_name)

        texts = [str(chunk.get("text", "")) for chunk in chunks]
        self.embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Return the top matching chunks with their cosine similarity."""
        if top_k <= 0 or not query.strip() or not self.chunks:
            return []

        query_embedding = self.model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        scores = self.embeddings @ query_embedding
        ranked_indices = np.argsort(-scores, kind="stable")[:top_k]

        results = []
        for index in ranked_indices:
            result = dict(self.chunks[int(index)])
            result["score"] = float(scores[index])
            results.append(result)

        return results
