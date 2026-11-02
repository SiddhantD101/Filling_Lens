from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .schema import Document, Page


def document_from_test_case(case: dict[str, Any]) -> Document:
    return Document(
        doc_id=case["id"],
        company=case["company"],
        sector=case["sector"],
        period_end=date.fromisoformat(case["period_end"]),
        revenue_crore=float(case["revenue_crore"]),
        synthetic=bool(case.get("synthetic", False)),
        pages=[Page(page=int(p["page"]), text=str(p["text"])) for p in case["pages"]],
    )


def load_test_cases(path: str | Path) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_documents(path: str | Path) -> list[Document]:
    return [document_from_test_case(case) for case in load_test_cases(path)]


def parse_pdf(path: str | Path, doc_id: str, company: str, sector: str, period_end: date, revenue_crore: float) -> Document:
    """Parse a text-based PDF if pypdf is installed.

    Scanned PDFs are intentionally out of scope for this prototype.
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Install pypdf to parse PDFs: python -m pip install pypdf") from exc

    reader = PdfReader(str(path))
    pages = [Page(page=i, text=page.extract_text() or "") for i, page in enumerate(reader.pages, start=1)]
    return Document(doc_id=doc_id, company=company, sector=sector, period_end=period_end, revenue_crore=revenue_crore, pages=pages)
