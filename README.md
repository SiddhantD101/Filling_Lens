# Disclosure Gap Finder

Full-stack prototype for the Tresata finance AI take-home assignment.

The tool reads filing excerpts or page text, stores documents in SQLite, extracts disclosed oil/fuel and FX exposure facts into a fixed schema, verifies that every extracted value is backed by a quote, applies gap and staleness rules, stores analysis runs, and exposes a React analyst review console.

## Why this prototype exists

Analysts often need to answer two questions after a commodity or currency shock:

1. What did each company disclose about fuel/oil and FX exposure?
2. What looks material but was not disclosed clearly?

This prototype deliberately does not forecast EPS impact, recommend trades, or value hedges. It reports disclosed facts, omissions, source quotes, and review flags.

## Run the Full App

Backend and built frontend:

```powershell
$env:PYTHONPATH="src"
python -m disclosure_gap_finder.cli seed-demo --db data/disclosure_gap_finder.sqlite --tests data/tests/labelled_examples.json
python -m disclosure_gap_finder.cli analyze-db --db data/disclosure_gap_finder.sqlite --config data/shock_scenarios.json
python -m disclosure_gap_finder.cli api --db data/disclosure_gap_finder.sqlite --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/
```

Frontend development mode:

```powershell
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

## Run the Evaluation

From this directory:

```powershell
$env:PYTHONPATH="src"
python -m disclosure_gap_finder.cli eval --tests data/tests/labelled_examples.json --out eval/results.md
python -m disclosure_gap_finder.cli card --tests data/tests/labelled_examples.json --out app/index.html
```

Open `app/index.html` in a browser to view the generated exposure cards.

## What is implemented

- Page/document model that preserves page numbers.
- SQLite persistence for companies, documents, pages, runs, evidence, flags, and review events.
- HTTP API using the Python standard library.
- React analyst console with document inventory, run history, flag queue, source pages, and evidence review actions.
- Keyword retrieval over page text.
- Baseline extractor for fuel cost, FX exposure, sensitivities, hedges, pass-through wording, and prompt-injection-like text.
- Verifier that requires extracted quotes to appear in source text and extracted numbers to appear in or be directly implied by the quote.
- Gap rules:
  - fuel or import-linked cost above 5% of revenue and no sensitivity disclosure means `MISSING_SENSITIVITY`;
  - disclosures older than 9 months are marked stale;
  - disclosures before the configured shock date are marked pre-shock.
- Evaluation on 14 labelled synthetic examples.
- Static HTML exposure card retained as an export-style artifact.

## Optional AI path

The assignment asks for an AI-based design. The production design uses an LLM only for the narrow extraction step: given candidate pages, return a JSON object with `value`, `unit`, `page`, and `verbatim_quote` for each field. Code then verifies and rejects anything that cannot be traced back.

This repo keeps the runnable default model-free so it can be evaluated without API keys. The deterministic extractor is also the baseline mentioned in the written brief.

For the chatbot, local workspace questions work without a key. General questions outside the loaded data use OpenRouter if these environment variables are set before starting the API server:

```powershell
$env:OPENROUTER_API_KEY="..."
$env:OPENROUTER_MODEL="provider/model-name"
```

The same key/model can also be used for the optional LLM extraction path:

```powershell
$env:OPENROUTER_API_KEY="..."
$env:OPENROUTER_MODEL="provider/model-name"
$env:PYTHONPATH="src"
python -m disclosure_gap_finder.cli eval --mode openrouter --tests data/tests/labelled_examples.json --out eval/openrouter_results.md
```

Use the default `regex` mode when you want a reproducible local baseline. Use `openrouter` mode when you want to test the intended AI extraction slot.

## Data status

The examples in `data/tests/labelled_examples.json` are synthetic and explicitly marked as such. They are designed to probe the failure modes in the plan: prose sensitivities, Indian number formats, hedge ratios in words, expired hedges, true non-disclosure, conflicting disclosures, wrong currencies, and prompt injection.

For a stronger submission, replace or extend five examples with excerpts from public annual reports and keep the same answer-key format.

## Repository map

```text
data/
  shock_scenarios.json
  tests/labelled_examples.json
docs/
  written_brief.md
  appendix_ai_use.md
  system_design.md
eval/
  run_eval.py
frontend/
  src/               React analyst console
src/disclosure_gap_finder/
  api.py             HTTP API and frontend serving
  card.py
  cli.py
  db.py              SQLite schema and persistence helpers
  extract.py
  gaps.py
  llm.py             optional OpenRouter extractor
  parse.py
  retrieve.py
  schema.py
  service.py         analysis orchestration
  verify.py
```

## Limits

- The tested extractor is a baseline, not the final AI extractor.
- PDF parsing is scaffolded but not exercised in the bundled tests.
- All examples are synthetic until public annual report excerpts are added.
- `NOT_DISCLOSED` still needs human review because a missed page can become a false gap.
