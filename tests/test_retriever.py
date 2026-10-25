
import pytest

from app.rag.retriever import search_chunks, tokenize


def make_chunk(text, page=1, chunk_index=0):
    return {
        "document": "report.pdf",
        "page": page,
        "text": text,
        "chunk_index": chunk_index,
    }


def test_tokenize_handles_case_and_punctuation():
    assert tokenize("Ставка, Рынок! ставка.") == [
        "ставка",
        "рынок",
        "ставка",
    ]


def test_search_chunks_returns_most_relevant_first():
    chunks = [
        make_chunk("Рынок труда охлаждается", page=1),
        make_chunk("Ключевая ставка остаётся высокой", page=2),
        make_chunk("Рынок труда и рынок вакансий", page=3),
    ]

    results = search_chunks("рынок труда", chunks, top_k=2)

    assert [chunk["page"] for chunk in results] == [3, 1]


def test_search_chunks_returns_empty_for_no_matches():
    chunks = [make_chunk("Инфляция замедлилась")]

    assert search_chunks("золото", chunks) == []


def test_search_chunks_returns_empty_for_empty_query():
    assert search_chunks(" !!! ", [make_chunk("Любой текст")]) == []


def test_search_chunks_rejects_invalid_top_k():
    with pytest.raises(ValueError):
        search_chunks("рынок", [], top_k=0)


def test_search_chunks_preserves_source_metadata():
    chunk = make_chunk("Рост инфляции", page=7, chunk_index=2)

    assert search_chunks("инфляции", [chunk]) == [chunk]
