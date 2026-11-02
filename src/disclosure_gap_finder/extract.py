from __future__ import annotations

import re
from typing import Iterable

from .schema import Evidence, Extraction, Page

RUPEE = r"(?:rs\.?|inr)"
NUMBER = r"(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)"


def _normalise_number(raw: str) -> float:
    return float(raw.replace(",", ""))


def _to_crore(amount: float, unit_text: str) -> float:
    unit = unit_text.lower()
    if "lakh" in unit:
        return amount / 100.0
    if "million" in unit:
        return amount / 10.0
    return amount


def _sentences(text: str) -> list[str]:
    # Keep "Rs. 100 crore" together; otherwise the amount is separated from its label.
    safe = text.replace("Rs.", "RS_DOT").replace("rs.", "rs_DOT")
    return [part.replace("RS_DOT", "Rs.").replace("rs_DOT", "rs.").strip() for part in re.split(r"(?<=[.!?])\s+", safe) if part.strip()]


def _evidence(value: float, unit: str, page: int, quote: str) -> Evidence:
    return Evidence(value=round(value, 4), unit=unit, page=page, quote=quote.strip())


def _find_rupee_amount(sentence: str) -> tuple[float, str] | None:
    match = re.search(RUPEE + r"\s*" + NUMBER + r"\s*(crore|lakh|million)?", sentence, re.IGNORECASE)
    if not match:
        return None
    unit = match.group(2) or "crore"
    return _to_crore(_normalise_number(match.group(1)), unit), unit


def _is_negated_sensitivity(sentence: str) -> bool:
    lower = sentence.lower()
    return "no sensitivity" in lower or "no quantified" in lower or "does not quantify" in lower or "not disclose" in lower


def _word_ratio(sentence: str) -> float | None:
    lower = sentence.lower()
    if "three-quarters" in lower or "three quarters" in lower:
        return 75.0
    if "half" in lower:
        return 50.0
    if "one-quarter" in lower or "one quarter" in lower:
        return 25.0
    return None


def _conflicting(values: Iterable[Evidence]) -> bool:
    seen = {round(float(item.value), 4) for item in values}
    return len(seen) > 1


def extract_with_regex(pages: list[Page]) -> Extraction:
    extraction = Extraction(searched_pages=[p.page for p in pages])
    fuel_sensitivities: list[Evidence] = []
    fx_sensitivities: list[Evidence] = []

    for page in pages:
        text = page.text
        lower_text = text.lower()
        if "ignore previous instructions" in lower_text or "automated readers" in lower_text:
            extraction.prompt_injection_detected = True
            extraction.review_notes.append(f"Potential prompt injection text on page {page.page}.")

        for sentence in _sentences(text):
            lower = sentence.lower()

            if extraction.fuel_cost_crore is None and any(term in lower for term in ["fuel expense", "fuel cost", "fuel reimbursements", "aviation turbine fuel", "aviation fuel expense", "bitumen purchases", "crude derivatives"]):
                amount = _find_rupee_amount(sentence)
                if amount:
                    extraction.fuel_cost_crore = _evidence(amount[0], "crore", page.page, sentence)

            if extraction.fx_net_exposure_crore is None and any(term in lower for term in ["foreign currency payables", "usd borrowings", "usd receivables", "eur receivables"]):
                amount = _find_rupee_amount(sentence)
                if amount:
                    extraction.fx_net_exposure_crore = _evidence(amount[0], "crore", page.page, sentence)

            if "pass-through" in lower or "pass through" in lower or "price escalation" in lower:
                extraction.pass_through_present = True

            if "hedg" in lower or "forward contracts cover" in lower:
                ratio_match = re.search(r"(?:hedged|cover|covers)\s+(\d+(?:\.\d+)?)\s*%", sentence, re.IGNORECASE)
                word_ratio = _word_ratio(sentence)
                if ratio_match:
                    extraction.hedge_ratio_pct = _evidence(float(ratio_match.group(1)), "percent", page.page, sentence)
                elif word_ratio is not None:
                    extraction.hedge_ratio_pct = _evidence(word_ratio, "percent", page.page, sentence)
                elif extraction.hedge_ratio_pct is None and any(term in lower for term in ["hedge", "contracts"]):
                    extraction.review_notes.append(f"Hedge mentioned without ratio on page {page.page}.")

            if any(term in lower for term in ["crude", "fuel", "commodity", "bitumen"]):
                if _is_negated_sensitivity(sentence):
                    extraction.fuel_sensitivity_present = False
                elif "sensitivity" in lower or "would decrease" in lower or "would lower" in lower:
                    amount = _find_rupee_amount(sentence)
                    if amount:
                        fuel_sensitivities.append(_evidence(amount[0], "crore", page.page, sentence))
                        extraction.fuel_sensitivity_present = True

            if any(term in lower for term in ["inr", "usd", "eur", "foreign exchange", "foreign currency"]):
                if _is_negated_sensitivity(sentence) and "usd sensitivity" in lower:
                    extraction.review_notes.append(f"USD sensitivity explicitly absent on page {page.page}.")
                elif "sensitivity" in lower or "depreciation" in lower or "appreciation" in lower or "would reduce" in lower or "would affect" in lower:
                    extraction.fx_sensitivity_present = True
                    amount = _find_rupee_amount(sentence)
                    if amount and "equity" not in lower:
                        fx_sensitivities.append(_evidence(amount[0], "crore", page.page, sentence))
                    elif "equity" in lower:
                        extraction.review_notes.append(f"FX sensitivity disclosed as percent of equity on page {page.page}; no crore impact.")

    if fuel_sensitivities:
        extraction.fuel_sensitivity_impact_crore = fuel_sensitivities[0]
        if _conflicting(fuel_sensitivities):
            extraction.ambiguous_fields.append("fuel_sensitivity_impact_crore")

    if fx_sensitivities:
        extraction.fx_sensitivity_impact_crore = fx_sensitivities[0]
        if _conflicting(fx_sensitivities):
            extraction.ambiguous_fields.append("fx_sensitivity_impact_crore")

    if extraction.fuel_sensitivity_present is None:
        extraction.fuel_sensitivity_present = bool(extraction.fuel_sensitivity_impact_crore)
    if extraction.fx_sensitivity_present is None:
        extraction.fx_sensitivity_present = bool(extraction.fx_sensitivity_impact_crore)

    return extraction
