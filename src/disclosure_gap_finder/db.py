from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .parse import load_test_cases
from .schema import Document, Evidence, GapAssessment, Page


DB_PATH = Path("data/disclosure_gap_finder.sqlite")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: str | Path = DB_PATH) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def session(path: str | Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS companies (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          sector TEXT NOT NULL,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS documents (
          id INTEGER PRIMARY KEY,
          doc_key TEXT NOT NULL UNIQUE,
          company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
          period_end TEXT NOT NULL,
          revenue_crore REAL NOT NULL,
          synthetic INTEGER NOT NULL DEFAULT 0,
          source_type TEXT NOT NULL DEFAULT 'test_excerpt',
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pages (
          id INTEGER PRIMARY KEY,
          document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          page_number INTEGER NOT NULL,
          text TEXT NOT NULL,
          UNIQUE(document_id, page_number)
        );

        CREATE TABLE IF NOT EXISTS runs (
          id INTEGER PRIMARY KEY,
          document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          mode TEXT NOT NULL,
          model TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL,
          started_at TEXT NOT NULL,
          completed_at TEXT,
          config_json TEXT NOT NULL,
          searched_pages_json TEXT NOT NULL DEFAULT '[]',
          review_required INTEGER NOT NULL DEFAULT 0,
          fuel_cost_share_revenue_pct REAL,
          stale INTEGER NOT NULL DEFAULT 0,
          pre_shock INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS evidence (
          id INTEGER PRIMARY KEY,
          run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
          field TEXT NOT NULL,
          value_text TEXT,
          numeric_value REAL,
          unit TEXT,
          page_number INTEGER,
          quote TEXT,
          status TEXT NOT NULL,
          verifier_note TEXT NOT NULL DEFAULT '',
          review_status TEXT NOT NULL DEFAULT 'pending',
          reviewer_note TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS flags (
          id INTEGER PRIMARY KEY,
          run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
          flag TEXT NOT NULL,
          severity TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS review_events (
          id INTEGER PRIMARY KEY,
          evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
          decision TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        );
        """
    )


def reset_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DELETE FROM review_events;
        DELETE FROM flags;
        DELETE FROM evidence;
        DELETE FROM runs;
        DELETE FROM pages;
        DELETE FROM documents;
        DELETE FROM companies;
        """
    )


def seed_demo(conn: sqlite3.Connection, tests_path: str | Path = "data/tests/labelled_examples.json") -> dict[str, int]:
    init_db(conn)
    cases = load_test_cases(tests_path)
    for case in cases:
        company_id = upsert_company(conn, case["company"], case["sector"])
        doc_id = upsert_document(
            conn,
            doc_key=case["id"],
            company_id=company_id,
            period_end=case["period_end"],
            revenue_crore=float(case["revenue_crore"]),
            synthetic=bool(case.get("synthetic", False)),
            source_type="synthetic_test",
        )
        conn.execute("DELETE FROM pages WHERE document_id = ?", (doc_id,))
        for page in case["pages"]:
            conn.execute(
                "INSERT INTO pages(document_id, page_number, text) VALUES (?, ?, ?)",
                (doc_id, int(page["page"]), str(page["text"])),
            )
    return {"companies": count(conn, "companies"), "documents": count(conn, "documents"), "pages": count(conn, "pages")}


def count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def upsert_company(conn: sqlite3.Connection, name: str, sector: str) -> int:
    conn.execute(
        """
        INSERT INTO companies(name, sector, created_at)
        VALUES (?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET sector = excluded.sector
        """,
        (name, sector, utc_now()),
    )
    return int(conn.execute("SELECT id FROM companies WHERE name = ?", (name,)).fetchone()["id"])


def upsert_document(
    conn: sqlite3.Connection,
    doc_key: str,
    company_id: int,
    period_end: str,
    revenue_crore: float,
    synthetic: bool,
    source_type: str,
) -> int:
    conn.execute(
        """
        INSERT INTO documents(doc_key, company_id, period_end, revenue_crore, synthetic, source_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(doc_key) DO UPDATE SET
          company_id = excluded.company_id,
          period_end = excluded.period_end,
          revenue_crore = excluded.revenue_crore,
          synthetic = excluded.synthetic,
          source_type = excluded.source_type
        """,
        (doc_key, company_id, period_end, revenue_crore, int(synthetic), source_type, utc_now()),
    )
    return int(conn.execute("SELECT id FROM documents WHERE doc_key = ?", (doc_key,)).fetchone()["id"])


def load_document(conn: sqlite3.Connection, document_id: int) -> Document:
    row = conn.execute(
        """
        SELECT d.*, c.name AS company, c.sector
        FROM documents d
        JOIN companies c ON c.id = d.company_id
        WHERE d.id = ?
        """,
        (document_id,),
    ).fetchone()
    if row is None:
        raise KeyError(f"Document {document_id} not found")
    pages = [
        Page(page=int(page["page_number"]), text=str(page["text"]))
        for page in conn.execute("SELECT page_number, text FROM pages WHERE document_id = ? ORDER BY page_number", (document_id,))
    ]
    return Document(
        doc_id=str(row["doc_key"]),
        company=str(row["company"]),
        sector=str(row["sector"]),
        period_end=date.fromisoformat(str(row["period_end"])),
        revenue_crore=float(row["revenue_crore"]),
        synthetic=bool(row["synthetic"]),
        pages=pages,
    )


def create_run(conn: sqlite3.Connection, document_id: int, mode: str, model: str, config: dict[str, Any]) -> int:
    cur = conn.execute(
        """
        INSERT INTO runs(document_id, mode, model, status, started_at, config_json)
        VALUES (?, ?, ?, 'running', ?, ?)
        """,
        (document_id, mode, model, utc_now(), json.dumps(config, sort_keys=True)),
    )
    return int(cur.lastrowid)


def finish_run(conn: sqlite3.Connection, run_id: int, extraction: Any, gaps: GapAssessment) -> None:
    conn.execute(
        """
        UPDATE runs
        SET status = 'complete',
            completed_at = ?,
            searched_pages_json = ?,
            review_required = ?,
            fuel_cost_share_revenue_pct = ?,
            stale = ?,
            pre_shock = ?
        WHERE id = ?
        """,
        (
            utc_now(),
            json.dumps(extraction.searched_pages),
            int(gaps.review_required),
            gaps.fuel_cost_share_revenue_pct,
            int(gaps.stale),
            int(gaps.pre_shock),
            run_id,
        ),
    )
    save_evidence(conn, run_id, "fuel_cost_crore", extraction.fuel_cost_crore)
    save_evidence(conn, run_id, "fuel_sensitivity_impact_crore", extraction.fuel_sensitivity_impact_crore)
    save_evidence(conn, run_id, "fx_net_exposure_crore", extraction.fx_net_exposure_crore)
    save_evidence(conn, run_id, "fx_sensitivity_impact_crore", extraction.fx_sensitivity_impact_crore)
    save_evidence(conn, run_id, "hedge_ratio_pct", extraction.hedge_ratio_pct)
    save_boolean_evidence(conn, run_id, "fuel_sensitivity_present", extraction.fuel_sensitivity_present)
    save_boolean_evidence(conn, run_id, "fx_sensitivity_present", extraction.fx_sensitivity_present)
    save_boolean_evidence(conn, run_id, "pass_through_present", extraction.pass_through_present)
    save_boolean_evidence(conn, run_id, "prompt_injection_detected", extraction.prompt_injection_detected)
    for field in extraction.ambiguous_fields:
        save_flag(conn, run_id, "AMBIGUOUS_" + field.upper(), "high", "Conflicting values were extracted for this field.")
    for flag in gaps.flags:
        save_flag(conn, run_id, flag, severity_for_flag(flag), "")
    for note in gaps.notes:
        save_flag(conn, run_id, "REVIEW_NOTE", "medium", note)


def fail_run(conn: sqlite3.Connection, run_id: int, message: str) -> None:
    conn.execute("UPDATE runs SET status = 'failed', completed_at = ? WHERE id = ?", (utc_now(), run_id))
    save_flag(conn, run_id, "RUN_FAILED", "high", message)


def save_evidence(conn: sqlite3.Connection, run_id: int, field: str, evidence: Evidence | None) -> None:
    if evidence is None:
        conn.execute(
            """
            INSERT INTO evidence(run_id, field, status)
            VALUES (?, ?, 'NOT_DISCLOSED')
            """,
            (run_id, field),
        )
        return
    numeric_value = None
    try:
        numeric_value = float(evidence.value)
    except (TypeError, ValueError):
        pass
    conn.execute(
        """
        INSERT INTO evidence(run_id, field, value_text, numeric_value, unit, page_number, quote, status, verifier_note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            field,
            str(evidence.value),
            numeric_value,
            evidence.unit,
            evidence.page,
            evidence.quote,
            evidence.status.value if hasattr(evidence.status, "value") else str(evidence.status),
            evidence.note,
        ),
    )


def save_boolean_evidence(conn: sqlite3.Connection, run_id: int, field: str, value: bool | None) -> None:
    status = "NOT_DISCLOSED" if value is None else "DISCLOSED"
    conn.execute(
        """
        INSERT INTO evidence(run_id, field, value_text, numeric_value, unit, status)
        VALUES (?, ?, ?, ?, 'boolean', ?)
        """,
        (run_id, field, None if value is None else str(bool(value)).lower(), None if value is None else int(bool(value)), status),
    )


def save_flag(conn: sqlite3.Connection, run_id: int, flag: str, severity: str, note: str) -> None:
    conn.execute(
        "INSERT INTO flags(run_id, flag, severity, note) VALUES (?, ?, ?, ?)",
        (run_id, flag, severity, note),
    )


def severity_for_flag(flag: str) -> str:
    if flag in {"MISSING_FUEL_SENSITIVITY", "AMBIGUOUS_DISCLOSURE", "PROMPT_INJECTION_TEXT"}:
        return "high"
    if flag == "STALE_DISCLOSURE":
        return "medium"
    return "low"


def review_evidence(conn: sqlite3.Connection, evidence_id: int, decision: str, note: str) -> None:
    conn.execute(
        "UPDATE evidence SET review_status = ?, reviewer_note = ? WHERE id = ?",
        (decision, note, evidence_id),
    )
    conn.execute(
        "INSERT INTO review_events(evidence_id, decision, note, created_at) VALUES (?, ?, ?, ?)",
        (evidence_id, decision, note, utc_now()),
    )


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def dashboard(conn: sqlite3.Connection) -> dict[str, Any]:
    counts = {
        "companies": count(conn, "companies"),
        "documents": count(conn, "documents"),
        "runs": count(conn, "runs"),
        "openEvidence": int(conn.execute("SELECT COUNT(*) FROM evidence WHERE review_status = 'pending' AND status != 'DISCLOSED'").fetchone()[0]),
        "highFlags": int(conn.execute("SELECT COUNT(*) FROM flags WHERE severity = 'high'").fetchone()[0]),
    }
    runs = [
        row_to_dict(row)
        for row in conn.execute(
            """
            SELECT r.id, r.status, r.mode, r.model, r.started_at, r.completed_at, r.review_required,
                   r.fuel_cost_share_revenue_pct, r.stale, r.pre_shock,
                   d.doc_key, d.period_end, c.name AS company, c.sector
            FROM runs r
            JOIN documents d ON d.id = r.document_id
            JOIN companies c ON c.id = d.company_id
            ORDER BY r.id DESC
            LIMIT 40
            """
        )
    ]
    documents = [
        row_to_dict(row)
        for row in conn.execute(
            """
            SELECT d.id, d.doc_key, d.period_end, d.revenue_crore, d.synthetic, d.source_type,
                   c.name AS company, c.sector,
                   (SELECT COUNT(*) FROM pages p WHERE p.document_id = d.id) AS pages,
                   (SELECT MAX(id) FROM runs r WHERE r.document_id = d.id) AS latest_run_id
            FROM documents d
            JOIN companies c ON c.id = d.company_id
            ORDER BY c.name
            """
        )
    ]
    flags = [
        row_to_dict(row)
        for row in conn.execute(
            """
            SELECT f.id, f.run_id, f.flag, f.severity, f.note, c.name AS company
            FROM flags f
            JOIN runs r ON r.id = f.run_id
            JOIN documents d ON d.id = r.document_id
            JOIN companies c ON c.id = d.company_id
            ORDER BY CASE f.severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, f.id DESC
            LIMIT 80
            """
        )
    ]
    return {"counts": counts, "runs": runs, "documents": documents, "flags": flags}


def run_detail(conn: sqlite3.Connection, run_id: int) -> dict[str, Any]:
    run = conn.execute(
        """
        SELECT r.*, d.doc_key, d.period_end, d.revenue_crore, d.synthetic, c.name AS company, c.sector
        FROM runs r
        JOIN documents d ON d.id = r.document_id
        JOIN companies c ON c.id = d.company_id
        WHERE r.id = ?
        """,
        (run_id,),
    ).fetchone()
    if run is None:
        raise KeyError(f"Run {run_id} not found")
    evidence = [row_to_dict(row) for row in conn.execute("SELECT * FROM evidence WHERE run_id = ? ORDER BY id", (run_id,))]
    flags = [row_to_dict(row) for row in conn.execute("SELECT * FROM flags WHERE run_id = ? ORDER BY id", (run_id,))]
    pages = [
        row_to_dict(row)
        for row in conn.execute(
            """
            SELECT p.page_number, p.text
            FROM pages p
            JOIN runs r ON r.document_id = p.document_id
            WHERE r.id = ?
            ORDER BY p.page_number
            """,
            (run_id,),
        )
    ]
    return {"run": row_to_dict(run), "evidence": evidence, "flags": flags, "pages": pages}
