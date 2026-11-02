# System Design

## Product Shape

Disclosure Gap Finder is an analyst workbench for oil/fuel and FX exposure disclosures. It is not a chatbot and not an earnings-impact predictor. Its core output is an auditable ledger:

- what was disclosed;
- where it was disclosed;
- what quote supports it;
- whether code verified it;
- what gap or staleness rules fired;
- what the analyst accepted or rejected.

## Architecture

```text
React analyst console
  |
  | HTTP JSON
  v
Python API server
  |
  +--> SQLite: companies, documents, pages, runs, evidence, flags, reviews
  |
  +--> Analysis service
        |
        +--> Candidate page retrieval
        +--> Extractor
        |     +--> regex baseline, reproducible
        |     +--> optional OpenRouter LLM extractor
        +--> Verifier
        +--> Gap and staleness rules
```

The important boundary is extraction versus verification. The AI path can read fuzzy filing language, but it cannot directly decide final status. Downstream code checks quotes, numbers, units, stale dates, and materiality rules.

## Data Model

`companies`
: Company name and sector.

`documents`
: One public filing or excerpt. Stores period end, revenue, source type and whether the input is synthetic.

`pages`
: Page-level text. All evidence points back to this layer.

`runs`
: A single analysis pass over one document. Stores mode, model, config snapshot, searched pages and run-level assessment.

`evidence`
: Field-level extraction result. Includes field name, value, unit, page number, quote, verifier status and analyst review status.

`flags`
: Gap, staleness, ambiguity, prompt-injection and review-note records.

`review_events`
: Audit trail for analyst decisions.

## API

`GET /api/dashboard`
: Counts, document inventory, run history and flag queue.

`GET /api/runs/{id}`
: Run detail with evidence rows, flags and source pages.

`POST /api/seed`
: Load the labelled demo set.

`POST /api/analyze`
: Run the analysis pipeline for all documents or one selected document.

`PUT /api/evidence/{id}/review`
: Mark an evidence item as accepted, rejected or needing follow-up.

## Model Strategy

The baseline extractor is deterministic and exists for two reasons:

1. It gives a reproducible comparison point.
2. It exposes where a non-AI approach becomes brittle.

The optional LLM extractor uses the same schema. It is allowed to locate and transcribe. It is not allowed to calculate advice, invent values, or bypass the verifier.

## Feature Roadmap

High-value next features:

- Public annual report ingestion with source URLs and checksums.
- Sector-specific materiality thresholds.
- Side-by-side peer comparison with sortable flags.
- Run diffing across quarterly and annual filings.
- Reviewer assignment and sign-off export.
- Confidence measured from verifier outcomes and analyst corrections, not model self-confidence.
- A public-filings pack with at least five real excerpts for the final submission.
