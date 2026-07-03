from __future__ import annotations

from pathlib import Path

from .models import PageText


class UnsupportedDocumentTypeError(ValueError):
    pass


class MissingDocumentDependencyError(RuntimeError):
    pass


def extract_pages(path: str | Path) -> list[PageText]:
    file_path = Path(path)
    suffix = file_path.suffix.lower()

    if suffix == ".txt":
        return [PageText(text=file_path.read_text(encoding="utf-8"), page_number=1)]
    if suffix == ".pdf":
        return _extract_pdf_pages(file_path)
    if suffix == ".docx":
        return _extract_docx_pages(file_path)

    raise UnsupportedDocumentTypeError(f"Unsupported document type: {suffix or '<none>'}")


def _extract_pdf_pages(path: Path) -> list[PageText]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise MissingDocumentDependencyError(
            "PDF extraction requires the optional dependency: pip install 'studyrag-core[pdf]'"
        ) from exc

    reader = PdfReader(str(path))
    pages: list[PageText] = []
    for index, page in enumerate(reader.pages, start=1):
        pages.append(PageText(text=page.extract_text() or "", page_number=index))
    return pages


def _extract_docx_pages(path: Path) -> list[PageText]:
    try:
        from docx import Document
    except ImportError as exc:
        raise MissingDocumentDependencyError(
            "DOCX extraction requires the optional dependency: pip install 'studyrag-core[docx]'"
        ) from exc

    document = Document(str(path))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    return [PageText(text=text, page_number=None)]
