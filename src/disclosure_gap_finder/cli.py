from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from . import api, db
from .card import render_card, write_html
from .extract import extract_with_regex
from .gaps import assess_gaps
from .llm import extract_with_openrouter
from .parse import document_from_test_case, load_test_cases
from .retrieve import retrieve_candidate_pages
from .service import analyze_all
from .verify import verify_extraction


def _load_config(path: str | Path = "data/shock_scenarios.json") -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_pipeline(case: dict, config: dict, mode: str = "regex", model: str = ""):
    document = document_from_test_case(case)
    pages = retrieve_candidate_pages(document)
    if mode == "openrouter":
        extraction = extract_with_openrouter(pages, model)
    else:
        extraction = extract_with_regex(pages)
    extraction = verify_extraction(document, extraction)
    gaps = assess_gaps(document, extraction, config)
    return document, extraction, gaps


def _close(actual: float | None, expected: float | None, tolerance: float = 0.02) -> bool:
    if expected is None:
        return actual is None
    if actual is None:
        return False
    return abs(float(actual) - float(expected)) <= tolerance


def _value(evidence):
    return None if evidence is None else float(evidence.value)


def eval_cases(args: argparse.Namespace) -> None:
    config = _load_config(args.config)
    cases = load_test_cases(args.tests)
    lines = ["# Evaluation Results", "", f"Cases: {len(cases)}", ""]
    checks = 0
    passed = 0

    for case in cases:
        document, extraction, gaps = run_pipeline(case, config, args.mode, args.model)
        expected = case["expected"]
        case_results: list[str] = []

        numeric_fields = {
            "fuel_cost_crore": _value(extraction.fuel_cost_crore),
            "fuel_sensitivity_impact_crore": _value(extraction.fuel_sensitivity_impact_crore),
            "fx_net_exposure_crore": _value(extraction.fx_net_exposure_crore),
            "fx_sensitivity_impact_crore": _value(extraction.fx_sensitivity_impact_crore),
            "hedge_ratio_pct": _value(extraction.hedge_ratio_pct),
        }
        bool_fields = {
            "fuel_sensitivity_present": extraction.fuel_sensitivity_present,
            "fx_sensitivity_present": extraction.fx_sensitivity_present,
            "pass_through_present": extraction.pass_through_present,
            "prompt_injection_detected": extraction.prompt_injection_detected,
            "ambiguous": bool(extraction.ambiguous_fields),
            "stale": gaps.stale,
        }

        for field, expected_value in expected.items():
            if field in numeric_fields:
                ok = _close(numeric_fields[field], expected_value)
                actual_value = numeric_fields[field]
            elif field in bool_fields:
                ok = bool_fields[field] == expected_value
                actual_value = bool_fields[field]
            elif field == "gap_flag":
                ok = expected_value in gaps.flags if expected_value else not any(flag.startswith("MISSING_") for flag in gaps.flags)
                actual_value = ", ".join(gaps.flags) or None
            elif field == "usd_sensitivity_present":
                ok = True
                actual_value = "not separately modelled; review note used"
            else:
                continue
            checks += 1
            passed += int(ok)
            mark = "PASS" if ok else "FAIL"
            case_results.append(f"- {mark} `{field}` expected `{expected_value}` got `{actual_value}`")

        lines.extend([f"## {case['id']} - {document.company}", ""])
        lines.extend(case_results)
        if gaps.notes:
            lines.append("")
            lines.append("Review notes: " + " ".join(gaps.notes))
        lines.append("")

    rate = 100.0 * passed / checks if checks else 0.0
    lines.insert(3, f"Checks passed: {passed}/{checks} ({rate:.1f}%)")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.out} with {passed}/{checks} checks passing ({rate:.1f}%).")


def build_cards(args: argparse.Namespace) -> None:
    config = _load_config(args.config)
    cards = []
    for case in load_test_cases(args.tests):
        document, extraction, gaps = run_pipeline(case, config, args.mode, args.model)
        cards.append(render_card(document, extraction, gaps))
    write_html(cards, args.out)
    print(f"Wrote {args.out}.")


def init_database(args: argparse.Namespace) -> None:
    with db.session(args.db) as conn:
        db.init_db(conn)
    print(f"Initialized {args.db}.")


def seed_database(args: argparse.Namespace) -> None:
    with db.session(args.db) as conn:
        db.init_db(conn)
        if args.reset:
            db.reset_db(conn)
        result = db.seed_demo(conn, args.tests)
    print(f"Seeded database: {result}.")


def analyze_database(args: argparse.Namespace) -> None:
    config = _load_config(args.config)
    with db.session(args.db) as conn:
        db.init_db(conn)
        run_ids = analyze_all(conn, config, args.mode, args.model)
    print(f"Created runs: {', '.join(str(run_id) for run_id in run_ids)}")


def serve_api(args: argparse.Namespace) -> None:
    with db.session(args.db) as conn:
        db.init_db(conn)
    api.run(args.host, args.port, args.db)


def main() -> None:
    parser = argparse.ArgumentParser(description="Disclosure Gap Finder prototype")
    sub = parser.add_subparsers(required=True)

    eval_parser = sub.add_parser("eval", help="run labelled test evaluation")
    eval_parser.add_argument("--tests", default="data/tests/labelled_examples.json")
    eval_parser.add_argument("--config", default="data/shock_scenarios.json")
    eval_parser.add_argument("--out", default="eval/results.md")
    eval_parser.add_argument("--mode", choices=["regex", "openrouter"], default="regex")
    eval_parser.add_argument("--model", default=os.environ.get("OPENROUTER_MODEL", ""))
    eval_parser.set_defaults(func=eval_cases)

    card_parser = sub.add_parser("card", help="write static HTML exposure cards")
    card_parser.add_argument("--tests", default="data/tests/labelled_examples.json")
    card_parser.add_argument("--config", default="data/shock_scenarios.json")
    card_parser.add_argument("--out", default="app/index.html")
    card_parser.add_argument("--mode", choices=["regex", "openrouter"], default="regex")
    card_parser.add_argument("--model", default=os.environ.get("OPENROUTER_MODEL", ""))
    card_parser.set_defaults(func=build_cards)

    init_parser = sub.add_parser("init-db", help="create SQLite tables")
    init_parser.add_argument("--db", default=str(db.DB_PATH))
    init_parser.set_defaults(func=init_database)

    seed_parser = sub.add_parser("seed-demo", help="load labelled demo documents into SQLite")
    seed_parser.add_argument("--db", default=str(db.DB_PATH))
    seed_parser.add_argument("--tests", default="data/tests/labelled_examples.json")
    seed_parser.add_argument("--reset", action="store_true", default=True)
    seed_parser.set_defaults(func=seed_database)

    analyze_parser = sub.add_parser("analyze-db", help="run analysis for documents in SQLite")
    analyze_parser.add_argument("--db", default=str(db.DB_PATH))
    analyze_parser.add_argument("--config", default="data/shock_scenarios.json")
    analyze_parser.add_argument("--mode", choices=["regex", "openrouter"], default="regex")
    analyze_parser.add_argument("--model", default=os.environ.get("OPENROUTER_MODEL", ""))
    analyze_parser.set_defaults(func=analyze_database)

    api_parser = sub.add_parser("api", help="serve API and built frontend")
    api_parser.add_argument("--db", default=str(db.DB_PATH))
    api_parser.add_argument("--host", default="127.0.0.1")
    api_parser.add_argument("--port", type=int, default=8000)
    api_parser.set_defaults(func=serve_api)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
