from __future__ import annotations

from pathlib import Path

from . import db
from .extract import extract_with_regex
from .gaps import assess_gaps
from .llm import extract_with_openrouter
from .retrieve import retrieve_candidate_pages
from .verify import verify_extraction


def load_config(path: str | Path = "data/shock_scenarios.json") -> dict:
    import json

    return json.loads(Path(path).read_text(encoding="utf-8"))


def analyze_document(conn, document_id: int, config: dict, mode: str = "regex", model: str = "") -> int:
    document = db.load_document(conn, document_id)
    run_id = db.create_run(conn, document_id, mode, model, config)
    try:
        pages = retrieve_candidate_pages(document)
        if mode == "openrouter":
            extraction = extract_with_openrouter(pages, model)
        else:
            extraction = extract_with_regex(pages)
        extraction = verify_extraction(document, extraction)
        gaps = assess_gaps(document, extraction, config)
        db.finish_run(conn, run_id, extraction, gaps)
    except Exception as exc:
        db.fail_run(conn, run_id, str(exc))
        raise
    return run_id


def analyze_all(conn, config: dict, mode: str = "regex", model: str = "") -> list[int]:
    rows = conn.execute("SELECT id FROM documents ORDER BY id").fetchall()
    return [analyze_document(conn, int(row["id"]), config, mode, model) for row in rows]
