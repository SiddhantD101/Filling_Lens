# Disclosure Gap Finder: Written Brief

## Problem

When oil prices or the rupee move sharply, analysts need to know which companies are exposed and what those companies have actually disclosed. The answer is scattered through annual reports: market-risk notes, hedging notes, management commentary and cost lines. The most useful finding is often negative: a company may show a large fuel or import-linked cost line but disclose no sensitivity.

This matters now because annual reports describe positions as of an earlier reporting date, while hedges roll off and shocks happen later. A disclosure that looked sufficient at year-end may not be useful after an oil or FX move.

In scope: public filings, extraction of oil/fuel and FX exposure disclosures, non-disclosure and staleness flags, and an analyst review step. Out of scope: EPS forecasts, price targets, hedge valuation, investment advice, scanned PDFs and private data.

## Solution Design

The architecture separates probabilistic reading from auditable checks:

```text
Public filings
  -> page parser with page numbers
  -> keyword/BM25 candidate-page retrieval
  -> narrow extraction into a fixed schema
  -> verifier: quote exists, number is present or unit-normalised
  -> gap and staleness rules
  -> exposure card and peer table
  -> analyst sign-off
```

The AI component should only locate passages and transcribe values with a page number and verbatim quote. Code owns quote verification, unit conversion, arithmetic, status assignment and gap rules. This keeps exact and probabilistic work apart.

Knowledge lives in three places: company facts in the source documents, thresholds and shock scenarios in config, and judgement in the human reviewer. If rules or disclosure formats change, the schema, retrieval terms and config must be updated.

## Prototype

The current prototype runs without an API key and uses a deterministic extractor as the baseline. It evaluates 14 labelled synthetic examples covering clean tables, prose sensitivities, Indian number formats, hedge ratios in words, expired hedges, missing sensitivities, conflicting figures, wrong currency references and prompt-injection-like text.

The generated HTML cards show each value, unit, source page, quote, gap flags, staleness and review notes. This is intentionally small but demonstrates the core design: a value is only accepted when it can be traced to source text.

## Risks

Wrong answers are handled with quote verification, number checks and analyst sign-off. False `NOT_DISCLOSED` claims are the most sensitive risk, so the card shows searched pages and requires review. Outdated figures are handled with period-end dates and staleness warnings. Confidential data is avoided by using only public or synthetic data. Liability is limited by positioning the tool as research support, not advice.

The weakest point is retrieval. If the right page is missed, the system can wrongly flag non-disclosure. That status should be measured separately and confirmed by a human.

## Alternatives Rejected

An end-to-end model that predicts EPS impact is not auditable and would look more certain than it is. A chatbot over reports has no fixed schema or peer comparison. A regex-only system is useful as a baseline but brittle on real filing language. Several cooperating agents add complexity without much value for a retrieve-extract-verify workflow.

## Before Investing More Time

The next checks are practical: add five public annual-report excerpts, confirm whether Indian companies disclose enough sensitivities to make this valuable, speak to one analyst or treasury practitioner, and decide whether the materiality threshold should be user-configurable by sector.
