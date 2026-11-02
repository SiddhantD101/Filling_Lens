from __future__ import annotations

import math
import re
from collections import Counter

from .schema import Document, Page

KEYWORDS = {
    "sensitivity",
    "hedge",
    "hedged",
    "forward",
    "contract",
    "crude",
    "fuel",
    "diesel",
    "bitumen",
    "foreign",
    "currency",
    "exchange",
    "usd",
    "inr",
    "payables",
    "borrowings",
    "depreciation",
    "pass-through",
    "pass through",
}


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def retrieve_candidate_pages(document: Document, limit: int = 8) -> list[Page]:
    if not document.pages:
        return []

    doc_freq: Counter[str] = Counter()
    page_terms = []
    for page in document.pages:
        terms = tokenize(page.text)
        page_terms.append((page, Counter(terms), len(terms) or 1))
        doc_freq.update(set(terms))

    total_pages = len(document.pages)
    scored: list[tuple[float, Page]] = []
    for page, counts, length in page_terms:
        score = 0.0
        lower = page.text.lower()
        for keyword in KEYWORDS:
            if " " in keyword:
                if keyword in lower:
                    score += 2.5
                continue
            if counts[keyword]:
                idf = math.log((total_pages + 1) / (doc_freq[keyword] + 0.5))
                score += counts[keyword] * idf / math.sqrt(length)
        if score > 0:
            scored.append((score, page))

    if not scored:
        return document.pages[:limit]
    return [page for _, page in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]
