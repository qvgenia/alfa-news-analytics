
"""Разбиение текста страниц PDF на фрагменты для RAG."""

from typing import TypedDict


class PageText(TypedDict):
    document: str
    page: int
    text: str


class TextChunk(TypedDict):
    document: str
    page: int
    text: str
    chunk_index: int


def chunk_pages(
    pages: list[PageText],
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[TextChunk]:
    """Разбивает текст страниц на фрагменты с перекрытием."""
    if chunk_size <= 0:
        raise ValueError("chunk_size должен быть больше нуля")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap должен быть неотрицательным и меньше chunk_size")

    chunks: list[TextChunk] = []

    for page_data in pages:
        text = page_data["text"].strip()
        if not text:
            continue

        start = 0
        chunk_index = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(
                    {
                        "document": page_data["document"],
                        "page": page_data["page"],
                        "text": chunk_text,
                        "chunk_index": chunk_index,
                    }
                )
                chunk_index += 1

            if end == len(text):
                break

            start = end - overlap

    return chunks
