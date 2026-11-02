from __future__ import annotations

from datetime import date

from .schema import Document, Extraction, GapAssessment


def _month_delta(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def assess_gaps(document: Document, extraction: Extraction, config: dict) -> GapAssessment:
    flags: list[str] = []
    notes: list[str] = []
    threshold = float(config.get("material_cost_share_threshold_pct", 5.0))
    shock_date = date.fromisoformat(config.get("shock_date", date.today().isoformat()))
    stale_after = int(config.get("stale_after_months", 9))

    fuel_share = None
    if extraction.fuel_cost_crore and document.revenue_crore:
        fuel_share = 100.0 * float(extraction.fuel_cost_crore.value) / document.revenue_crore
        if fuel_share >= threshold and not extraction.fuel_sensitivity_present:
            flags.append("MISSING_FUEL_SENSITIVITY")
            notes.append(f"Fuel/import-linked cost is {fuel_share:.1f}% of revenue, above the {threshold:.1f}% threshold.")

    if extraction.ambiguous_fields:
        flags.append("AMBIGUOUS_DISCLOSURE")
        notes.append("Conflicting extracted values require analyst review: " + ", ".join(extraction.ambiguous_fields))

    if extraction.prompt_injection_detected:
        flags.append("PROMPT_INJECTION_TEXT")
        notes.append("Source text contains instruction-like language and must be treated as data only.")

    stale = _month_delta(document.period_end, shock_date) > stale_after
    pre_shock = document.period_end < shock_date
    if stale:
        flags.append("STALE_DISCLOSURE")
        notes.append(f"Period end {document.period_end.isoformat()} is older than {stale_after} months versus shock date {shock_date.isoformat()}.")
    elif pre_shock:
        notes.append(f"Disclosure predates shock date {shock_date.isoformat()}.")

    review_required = bool(flags or extraction.review_notes)
    return GapAssessment(
        flags=flags,
        stale=stale,
        pre_shock=pre_shock,
        fuel_cost_share_revenue_pct=round(fuel_share, 2) if fuel_share is not None else None,
        review_required=review_required,
        notes=notes + extraction.review_notes,
    )
