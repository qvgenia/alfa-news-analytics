"""Загрузка текста из PDF с сохранением метаданных страниц."""

from pathlib import Path

import pymupdf


TESSDATA_PATH = r"C:\Program Files\Tesseract-OCR\tessdata"


def load_pdf(pdf_path: str | Path) -> list[dict[str, str | int]]:
    """Извлекает текст страниц PDF, используя OCR при необходимости."""
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
                try:
                    text_page = page.get_textpage_ocr(
                        language="rus+eng",
                        dpi=120,
                        full=True,
                        tessdata=r"C:\Program Files\Tesseract-OCR\tessdata",
                    )
                    text = page.get_text(
                        "text",
                        textpage=text_page,
                    ).strip()
                except Exception as exc:
                    raise RuntimeError(
                        f"Не удалось извлечь текст или выполнить OCR: "
                        f"{path.name}, страница {page_number}. "
                        "Проверьте установку Tesseract и языковые данные."
                    ) from exc

            if text:
                pages.append(
                    {
                        "document": path.name,
                        "page": page_number,
                        "text": text,
                    }
                )

    return pages


def load_reports(
    reports_dir: str | Path = "data/reports",
) -> list[dict[str, str | int]]:
    """Загружает текст всех PDF из папки с отчётами."""
    directory = Path(reports_dir)

    if not directory.exists():
        raise FileNotFoundError(f"Папка с отчётами не найдена: {directory}")

    if not directory.is_dir():
        raise ValueError(f"Ожидалась папка с отчётами: {directory}")

    pdf_files = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() == ".pdf"
    )

    pages: list[dict[str, str | int]] = []

    for pdf_path in pdf_files:
        pages.extend(load_pdf(pdf_path))

    return pages