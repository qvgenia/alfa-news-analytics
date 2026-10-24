
"""Загрузка текста из PDF с сохранением метаданных страниц."""

from pathlib import Path

import pymupdf


def load_pdf(pdf_path: str | Path) -> list[dict[str, str | int]]:
    """Извлекает непустые страницы PDF.

    Возвращает список страниц с именем документа, номером страницы
    и извлечённым текстом.
    """
    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF-файл не найден: {path}")

    if not path.is_file() or path.suffix.lower() != ".pdf":
        raise ValueError(f"Ожидался PDF-файл: {path}")

    pages: list[dict[str, str | int]] = []

    with pymupdf.open(path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()

            if not text:
                continue

            pages.append(
                {
                    "document": path.name,
                    "page": page_number,
                    "text": text,
                }
            )

    return pages
