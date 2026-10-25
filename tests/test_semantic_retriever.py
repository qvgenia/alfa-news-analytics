from typing import Any

import numpy as np

from app.rag.semantic_retriever import SemanticRetriever


def make_retriever(chunks: list[dict[str, Any]]) -> SemanticRetriever:
    retriever = SemanticRetriever.__new__(SemanticRetriever)
    retriever.chunks = chunks
    return retriever


def test_search_returns_empty_for_invalid_input() -> None:
    retriever = make_retriever([{"document": "a.pdf", "page": 1, "text": "text"}])

    assert retriever.search("", top_k=5) == []
    assert retriever.search("query", top_k=0) == []


def test_search_returns_empty_when_no_chunks() -> None:
    retriever = make_retriever([])
    retriever.embeddings = np.empty((0, 3))

    class FakeModel:
        def encode(self, *args: Any, **kwargs: Any) -> np.ndarray:
            return np.array([1.0, 0.0, 0.0])

    retriever.model = FakeModel()

    assert retriever.search("query") == []


def test_search_ranks_by_similarity_and_preserves_chunk_data() -> None:
    chunks = [
        {"document": "a.pdf", "page": 1, "text": "first"},
        {"document": "b.pdf", "page": 2, "text": "second"},
        {"document": "c.pdf", "page": 3, "text": "third"},
    ]
    retriever = make_retriever(chunks)
    retriever.embeddings = np.array([
        [0.0, 1.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
    ])

    class FakeModel:
        def encode(self, *args: Any, **kwargs: Any) -> np.ndarray:
            return np.array([1.0, 0.0, 0.0])

    retriever.model = FakeModel()

    results = retriever.search("query", top_k=2)

    assert [result["document"] for result in results] == ["b.pdf", "a.pdf"]
    assert results[0]["text"] == "second"
    assert results[0]["score"] == 1.0
    assert len(results) == 2


def test_search_does_not_mutate_original_chunks() -> None:
    chunks = [{"document": "a.pdf", "page": 1, "text": "first"}]
    retriever = make_retriever(chunks)
    retriever.embeddings = np.array([[1.0, 0.0]])

    class FakeModel:
        def encode(self, *args: Any, **kwargs: Any) -> np.ndarray:
            return np.array([1.0, 0.0])

    retriever.model = FakeModel()

    retriever.search("query")

    assert "score" not in chunks[0]
