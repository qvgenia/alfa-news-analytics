
import pytest

from app.rag.chunker import chunk_pages


def test_chunk_pages_splits_long_text_with_overlap():
    pages = [
        {
            "document": "report.pdf",
            "page": 1,
            "text": "A" * 12,
        }
    ]

    chunks = chunk_pages(pages, chunk_size=5, overlap=2)

    assert [chunk["text"] for chunk in chunks] == [
    "AAAAA",
    "AAAAA",
    "AAAAA",
    "AAA",
    ]
    assert [chunk["chunk_index"] for chunk in chunks] == [0, 1, 2, 3]


def test_chunk_pages_preserves_metadata():
    pages = [
        {
            "document": "report.pdf",
            "page": 3,
            "text": "Important findings",
        }
    ]

    chunks = chunk_pages(pages, chunk_size=100, overlap=0)

    assert chunks == [
        {
            "document": "report.pdf",
            "page": 3,
            "text": "Important findings",
            "chunk_index": 0,
        }
    ]


def test_chunk_pages_skips_empty_text():
    pages = [
        {"document": "report.pdf", "page": 1, "text": "   "}
    ]

    assert chunk_pages(pages) == []


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (-1, 0), (5, 5), (5, 6), (5, -1)],
)
def test_chunk_pages_rejects_invalid_parameters(chunk_size, overlap):
    with pytest.raises(ValueError):
        chunk_pages([], chunk_size=chunk_size, overlap=overlap)
