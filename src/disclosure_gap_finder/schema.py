from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class Status(str, Enum):
    DISCLOSED = "DISCLOSED"
    PARTIAL = "PARTIAL"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_DISCLOSED = "NOT_DISCLOSED"
    NOT_FOUND = "NOT_FOUND"


@dataclass
class Page:
    page: int
    text: str


@dataclass
class Document:
    doc_id: str
    company: str
    sector: str
    period_end: date
    revenue_crore: float
    pages: list[Page]
    synthetic: bool = False


@dataclass
class Evidence:
    value: Any
    unit: str
    page: int
    quote: str
    status: Status = Status.DISCLOSED
    note: str = ""


@dataclass
class Extraction:
    fuel_cost_crore: Evidence | None = None
    fuel_sensitivity_impact_crore: Evidence | None = None
    fuel_sensitivity_present: bool | None = None
    fx_net_exposure_crore: Evidence | None = None
    fx_sensitivity_impact_crore: Evidence | None = None
    fx_sensitivity_present: bool | None = None
    hedge_ratio_pct: Evidence | None = None
    pass_through_present: bool = False
    prompt_injection_detected: bool = False
    ambiguous_fields: list[str] = field(default_factory=list)
    searched_pages: list[int] = field(default_factory=list)
    review_notes: list[str] = field(default_factory=list)


@dataclass
class GapAssessment:
    flags: list[str]
    stale: bool
    pre_shock: bool
    fuel_cost_share_revenue_pct: float | None
    review_required: bool
    notes: list[str]
