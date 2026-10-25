
"""Semantic retrieval with persistent PostgreSQL embedding storage."""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import select

from app.db.models import ReportChunkModel
from app.db.session import SessionLocal


DEFAULT_MODEL_NAME = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
EMBEDDING_DIMENSION = 384


class SemanticRetriever:
    """Rank chunks by cosine similarity and reuse persisted embeddings."""

    def __init__(
        self,
        chunks: list[dict[str, Any]],
        model_name: str = DEFAULT_MODEL_NAME,
    ) -> None:
        self.chunks = chunks
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

        self.embeddings = self._load_or_create_embeddings()

    @staticmethod
    def _content_hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _identity(chunk: dict[str, Any]) -> tuple[str, int, int]:
        return (
            str(chunk["document"]),
            int(chunk["page"]),
            int(chunk["chunk_index"]),
        )

    def _load_or_create_embeddings(self) -> np.ndarray:
        if not self.chunks:
            return np.empty((0, EMBEDDING_DIMENSION), dtype=np.float32)

        identities = [self._identity(chunk) for chunk in self.chunks]
        texts = [str(chunk.get("text", "")) for chunk in self.chunks]
        hashes = [self._content_hash(text) for text in texts]

        with SessionLocal() as session:
            rows = session.scalars(
                select(ReportChunkModel)
            ).all()

            stored = {
                (
                    row.document,
                    row.page,
                    row.chunk_index,
                ): row
                for row in rows
            }

            embeddings: list[list[float] | None] = [None] * len(self.chunks)
            pending_indices: list[int] = []

            for index, identity in enumerate(identities):
                row = stored.get(identity)

                if (
                    row is not None
                    and row.content_hash == hashes[index]
                    and row.model_name == self.model_name
                ):
                    embeddings[index] = list(row.embedding)
                else:
                    pending_indices.append(index)

            if pending_indices:
                pending_texts = [texts[i] for i in pending_indices]
                encoded = self.model.encode(
                    pending_texts,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )

                for offset, index in enumerate(pending_indices):
                    identity = identities[index]
                    vector = encoded[offset].astype(float).tolist()
                    embeddings[index] = vector

                    row = stored.get(identity)

                    if row is None:
                        row = ReportChunkModel(
                            document=identity[0],
                            page=identity[1],
                            chunk_index=identity[2],
                            text=texts[index],
                            content_hash=hashes[index],
                            model_name=self.model_name,
                            embedding=vector,
                        )
                        session.add(row)
                        stored[identity] = row
                    else:
                        row.text = texts[index]
                        row.content_hash = hashes[index]
                        row.model_name = self.model_name
                        row.embedding = vector

            session.commit()

        return np.asarray(embeddings, dtype=np.float32)

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
