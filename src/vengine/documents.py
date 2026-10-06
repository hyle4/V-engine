"""Source adapters preserving page numbers and text provenance."""

from __future__ import annotations

import csv
import json
import mimetypes
import os
import shutil
import subprocess
from collections.abc import Callable
from importlib.metadata import version
from io import BytesIO
from pathlib import Path

from .models import ContentBlock, DocumentIR, DocumentPage, SourceRef

SUPPORTED = {".pdf", ".txt", ".md", ".markdown", ".json", ".csv",
             ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}


def supported_formats() -> set[str]:
    from .plugins import supported_extensions

    return SUPPORTED | supported_extensions()


def media_type(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def parse(path: Path, source_id: str, filename: str | None = None, *,
          cached_pages: list[DocumentPage] | None = None,
          on_page: Callable[[DocumentPage, int], None] | None = None) -> DocumentIR:
    suffix = Path(filename or path.name).suffix.lower()
    from .plugins import parser_for

    custom = parser_for(suffix)
    if custom:
        return DocumentIR.model_validate(custom(path, source_id, filename or path.name))
    if suffix not in SUPPORTED:
        raise ValueError(f"Unsupported format: {suffix}. Supported: {', '.join(sorted(supported_formats()))}")
    if suffix == ".pdf":
        return _pdf(path, source_id, filename, cached_pages=cached_pages, on_page=on_page)
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}:
        text = _ocr(path.read_bytes())
        return DocumentIR(source_id=source_id, title=filename or path.name,
                          pages=[DocumentPage(number=1, blocks=_paragraphs(text, source_id, 1),
                                              warnings=[] if text else ["OCR found no text"])],
                          parser="tesseract", parser_version="system")
    text = path.read_text(encoding="utf-8-sig")
    if suffix == ".json":
        data = json.loads(text)
        text = json.dumps(data, ensure_ascii=False, indent=2)
    elif suffix == ".csv":
        rows = list(csv.reader(text.splitlines()))
        text = "\n".join(" | ".join(row) for row in rows)
    blocks = _paragraphs(text, source_id, 1)
    return DocumentIR(source_id=source_id, title=filename or path.name,
                      pages=[DocumentPage(number=1, blocks=blocks)],
                      parser="builtin", parser_version="1")


def render_pdf_page(path: Path, page: int, *, scale: float = 1.5) -> bytes:
    """Rasterize one 1-based PDF page. Raises ValueError when the page is absent."""
    import pypdfium2 as pdfium

    if page < 1:
        raise ValueError("Page not found")
    with pdfium.PdfDocument(path) as pdf:
        if page > len(pdf):
            raise ValueError("Page not found")
        pdf_page = pdf[page - 1]
        try:
            bitmap = pdf_page.render(scale=scale)
            try:
                output = BytesIO()
                bitmap.to_pil().save(output, format="PNG")
                return output.getvalue()
            finally:
                bitmap.close()
        finally:
            pdf_page.close()


def _paragraphs(text: str, source_id: str, page: int) -> list[ContentBlock]:
    result = []
    for chunk in text.replace("\r\n", "\n").split("\n\n"):
        chunk = chunk.strip()
        if chunk:
            result.append(ContentBlock(text=chunk, source=SourceRef(
                source_id=source_id, page=page, quote=chunk[:300])))
    return result


def _pdf(path: Path, source_id: str, filename: str | None = None, *,
         cached_pages: list[DocumentPage] | None = None,
         on_page: Callable[[DocumentPage, int], None] | None = None) -> DocumentIR:
    import pypdfium2 as pdfium

    pages = []
    cached = {page.number: page for page in cached_pages or []}
    with pdfium.PdfDocument(path) as pdf:
        total = len(pdf)
        for number in range(total):
            if number + 1 in cached:
                pages.append(cached[number + 1])
                continue
            page = pdf[number]
            try:
                textpage = page.get_textpage()
                try:
                    text = textpage.get_text_range()
                finally:
                    textpage.close()
                if not text.strip() and shutil.which("tesseract"):
                    bitmap = page.render(scale=2)
                    try:
                        output = BytesIO()
                        bitmap.to_pil().save(output, format="PNG")
                        text = _ocr(output.getvalue())
                    finally:
                        bitmap.close()
            finally:
                page.close()
            blocks = _paragraphs(text, source_id, number + 1)
            warning = [] if text.strip() else ["No text found; check OCR language and scan quality."]
            completed = DocumentPage(number=number + 1, blocks=blocks, warnings=warning)
            pages.append(completed)
            if on_page:
                on_page(completed, total)
    return DocumentIR(source_id=source_id, title=filename or path.name, pages=pages,
                      parser="pypdfium2", parser_version=version("pypdfium2"),
                      warnings=["Some pages have no extractable text"] if any(p.warnings for p in pages) else [])


def _ocr(image_bytes: bytes) -> str:
    if not shutil.which("tesseract"):
        raise RuntimeError("Tesseract OCR is required for image sources")
    language = os.environ.get("VENGINE_OCR_LANG", "eng")
    if not all(part.replace("_", "").isalnum() for part in language.split("+")):
        raise ValueError("Invalid OCR language code")
    result = subprocess.run(["tesseract", "stdin", "stdout", "-l", language],
                            input=image_bytes, capture_output=True, timeout=60, check=False)
    if result.returncode:
        raise RuntimeError("Tesseract OCR failed: " + result.stderr.decode(errors="replace")[:200])
    return result.stdout.decode("utf-8", errors="replace")
