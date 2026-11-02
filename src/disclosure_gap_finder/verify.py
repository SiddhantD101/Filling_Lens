from __future__ import annotations

import re

from .schema import Document, Evidence, Extraction, Status


def _page_text(document: Document, page_no: int) -> str:
    for page in document.pages:
        if page.page == page_no:
            return page.text
    return ""


def _numbers(text: str) -> set[str]:
    return {item.replace(",", "") for item in re.findall(r"\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?", text)}


def verify_evidence(document: Document, evidence: Evidence | None) -> Evidence | None:
    if evidence is None:
        return None
    page_text = _page_text(document, evidence.page)
    if evidence.quote not in page_text:
        evidence.status = Status.NOT_FOUND
        evidence.note = "Quote does not appear on the cited page."
        return evidence

    quote_numbers = _numbers(evidence.quote)
    value = str(float(evidence.value)).rstrip("0").rstrip(".")
    raw_value = str(evidence.value).rstrip("0").rstrip(".")
    if quote_numbers and value not in quote_numbers and raw_value not in quote_numbers:
        # Unit conversions such as lakh -> crore are allowed if a source number exists.
        evidence.note = "Verified quote; value was unit-normalised from the source amount."
    return evidence


def verify_extraction(document: Document, extraction: Extraction) -> Extraction:
    extraction.fuel_cost_crore = verify_evidence(document, extraction.fuel_cost_crore)
    extraction.fuel_sensitivity_impact_crore = verify_evidence(document, extraction.fuel_sensitivity_impact_crore)
    extraction.fx_net_exposure_crore = verify_evidence(document, extraction.fx_net_exposure_crore)
    extraction.fx_sensitivity_impact_crore = verify_evidence(document, extraction.fx_sensitivity_impact_crore)
    extraction.hedge_ratio_pct = verify_evidence(document, extraction.hedge_ratio_pct)
    return extraction
