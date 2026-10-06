"""Portable PDF page recovery, without a machine-local source fixture."""

from __future__ import annotations

from pathlib import Path

import pytest

from vengine import documents
from vengine.store import Store


def _write_pdf(path: Path) -> None:
    streams = [b"BT /F1 12 Tf 72 720 Td (First page source) Tj ET",
               b"BT /F1 12 Tf 72 720 Td (Second page source) Tj ET"]
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(streams[0]) + streams[0] + b"\nendstream",
        b"<< /Length %d >>\nstream\n" % len(streams[1]) + streams[1] + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(b"%d 0 obj\n" % number + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(b"xref\n0 8\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(b"%010d 00000 n \n" % offset)
    data.extend(b"trailer\n<< /Size 8 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % xref)
    path.write_bytes(data)


def test_pdf_page_checkpoint_and_resume(tmp_path: Path) -> None:
    path = tmp_path / "sample.pdf"
    _write_pdf(path)
    store = Store(tmp_path / "data")
    source = store.add_source(path, "application/pdf")
    calls = []

    def interrupted(page, total):
        store.save_document_page(source["id"], page)
        calls.append((page.number, total))
        raise RuntimeError("interrupted after durable page")

    with pytest.raises(RuntimeError, match="interrupted"):
        documents.parse(Path(source["path"]), source["id"], source["name"],
                        cached_pages=store.document_pages(source["id"]), on_page=interrupted)
    assert calls == [(1, 2)]
    assert len(store.document_pages(source["id"])) == 1

    resumed = []
    doc = documents.parse(Path(source["path"]), source["id"], source["name"],
                          cached_pages=store.document_pages(source["id"]),
                          on_page=lambda page, total: resumed.append(page.number))
    assert resumed == [2]
    assert [page.number for page in doc.pages] == [1, 2]
    assert "First page source" in doc.pages[0].blocks[0].text
    assert "Second page source" in doc.pages[1].blocks[0].text
