from pathlib import Path

import pymupdf
import pytest

from app.rag.pdf_loader import load_pdf, load_reports


def create_pdf(pdf_path: Path, text: str = "Test report") -> None:
    """Создаёт небольшой PDF для тестов."""
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), text)
        document.save(pdf_path)


def test_load_pdf_extracts_text_and_page_number(tmp_path):
    pdf_path = tmp_path / "report.pdf"
    create_pdf(pdf_path, "Key rate")

    pages = load_pdf(pdf_path)

    assert len(pages) == 1
    assert pages[0]["document"] == "report.pdf"
    assert pages[0]["page"] == 1
    assert "Key rate" in pages[0]["text"]


def test_load_pdf_raises_for_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_pdf(tmp_path / "missing.pdf")


def test_load_pdf_rejects_non_pdf_file(tmp_path):
    file_path = tmp_path / "report.txt"
    file_path.write_text("Text", encoding="utf-8")

    with pytest.raises(ValueError):
        load_pdf(file_path)


def test_load_reports_reads_all_pdfs(tmp_path):
    create_pdf(tmp_path / "report_a.pdf", "First report")
    create_pdf(tmp_path / "report_b.pdf", "Second report")
    (tmp_path / "notes.txt").write_text("Ignore me", encoding="utf-8")

    pages = load_reports(tmp_path)

    assert len(pages) == 2
    assert {page["document"] for page in pages} == {
        "report_a.pdf",
        "report_b.pdf",
    }
    assert {page["text"].strip() for page in pages} == {
        "First report",
        "Second report",
    }


def test_load_reports_raises_for_missing_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_reports(tmp_path / "missing")


def test_load_reports_rejects_file_instead_of_directory(tmp_path):
    file_path = tmp_path / "reports.txt"
    file_path.write_text("Not a directory", encoding="utf-8")

    with pytest.raises(ValueError):
        load_reports(file_path)