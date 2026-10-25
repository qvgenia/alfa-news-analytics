from typing import Any
from unittest.mock import patch

from app.rag.hybrid_retriever import HybridRetriever


class FakeSemanticRetriever:
    def __init__(self, results: list[dict[str, Any]]) -> None:
        self.results = results

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        return self.results[:top_k]


def chunk(document: str, page: int, text: str) -> dict[str, Any]:
    return {"document": document, "page": page, "text": text}


def make_retriever(
    lexical: list[dict[str, Any]],
    semantic: list[dict[str, Any]],
) -> HybridRetriever:
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever.chunks = lexical
    retriever.semantic_retriever = FakeSemanticRetriever(semantic)
    retriever.rrf_k = 60
    return retriever


def test_hybrid_returns_unique_pages() -> None:
    lexical = [
        chunk("a.pdf", 1, "lexical chunk 1"),
        chunk("a.pdf", 1, "lexical chunk 2"),
        chunk("b.pdf", 2, "lexical chunk 3"),
    ]
    semantic = [
        chunk("a.pdf", 1, "semantic chunk"),
        chunk("c.pdf", 3, "another semantic chunk"),
    ]
    retriever = make_retriever(lexical, semantic)

    with patch(
        "app.rag.hybrid_retriever.search_chunks",
        return_value=lexical,
    ):
        results = retriever.search("query", top_k=5)

    pages = [(result["document"], result["page"]) for result in results]
    assert len(pages) == len(set(pages))
    assert set(pages) == {("a.pdf", 1), ("b.pdf", 2), ("c.pdf", 3)}


def test_hybrid_favors_page_ranked_well_by_both_methods() -> None:
    lexical = [
        chunk("shared.pdf", 1, "shared lexical"),
        chunk("lexical.pdf", 2, "lexical only"),
    ]
    semantic = [
        chunk("shared.pdf", 1, "shared semantic"),
        chunk("semantic.pdf", 3, "semantic only"),
    ]
    retriever = make_retriever(lexical, semantic)

    with patch(
        "app.rag.hybrid_retriever.search_chunks",
        return_value=lexical,
    ):
        results = retriever.search("query", top_k=3)

    assert len(results) == 3
    assert (results[0]["document"], results[0]["page"]) == ("shared.pdf", 1)
    assert results[0]["score"] > results[1]["score"]
    assert results[0]["score"] > results[2]["score"]


def test_hybrid_returns_empty_for_invalid_input() -> None:
    retriever = make_retriever([], [])

    assert retriever.search("", top_k=5) == []
    assert retriever.search("query", top_k=0) == []
    assert retriever.search("query", candidate_k=0) == []


def test_hybrid_preserves_chunk_fields_and_adds_score() -> None:
    lexical = [chunk("a.pdf", 1, "original text")]
    retriever = make_retriever(lexical, [])

    with patch(
        "app.rag.hybrid_retriever.search_chunks",
        return_value=lexical,
    ):
        results = retriever.search("query")

    assert results[0]["text"] == "original text"
    assert results[0]["score"] > 0
    assert "score" not in lexical[0]
