
from pathlib import Path

import pymupdf
import pytest

from app.rag.pdf_loader import load_pdf


def test_load_pdf_extracts_text_and_page_number(tmp_path):
    pdf_path = tmp_path / "report.pdf"
    font_path = Path("/c/Windows/Fonts/arial.ttf")

    # Git Bash путь /c/... преобразуем в Windows-путь.
    if not font_path.exists():
        font_path = Path("C:/Windows/Fonts/arial.ttf")

    assert font_path.exists(), "Не найден Arial: C:/Windows/Fonts/arial.ttf"

    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_font(fontname="F0", fontfile=str(font_path))
        page.insert_text(
            (72, 72),
            "Ключевая ставка",
            fontname="F0",
        )
        document.save(pdf_path)

    pages = load_pdf(pdf_path)

    assert len(pages) == 1
    assert pages[0]["document"] == "report.pdf"
    assert pages[0]["page"] == 1
    assert "Ключевая ставка" in pages[0]["text"].replace("\xa0", " ")


def test_load_pdf_raises_for_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_pdf(tmp_path / "missing.pdf")


def test_load_pdf_rejects_non_pdf_file(tmp_path):
    file_path = tmp_path / "report.txt"
    file_path.write_text("Текст", encoding="utf-8")

    with pytest.raises(ValueError):
        load_pdf(file_path)