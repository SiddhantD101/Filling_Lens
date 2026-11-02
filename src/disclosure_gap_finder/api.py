from __future__ import annotations

import json
import os
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import db
from .service import analyze_all, analyze_document, load_config


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class Handler(SimpleHTTPRequestHandler):
    server_version = "DisclosureGapFinder/0.2"

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_PUT(self) -> None:
        self._handle("PUT")

    def _handle(self, method: str) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                result = self.route_api(method, parsed.path, parse_qs(parsed.query))
                self.send_json(result)
                return
            self.serve_frontend(parsed.path)
        except ApiError as exc:
            self.send_json({"error": exc.message}, exc.status)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def route_api(self, method: str, path: str, query: dict) -> dict:
        body = self.read_json()
        with db.session(self.server.db_path) as conn:  # type: ignore[attr-defined]
            db.init_db(conn)
            if method == "GET" and path == "/api/health":
                return {"ok": True}
            if method == "GET" and path == "/api/dashboard":
                return db.dashboard(conn)
            if method == "GET" and path.startswith("/api/runs/"):
                run_id = int(path.rsplit("/", 1)[-1])
                return db.run_detail(conn, run_id)
            if method == "POST" and path == "/api/seed":
                if body.get("reset", True):
                    db.reset_db(conn)
                return db.seed_demo(conn)
            if method == "POST" and path == "/api/analyze":
                config = load_config(body.get("config_path", "data/shock_scenarios.json"))
                mode = body.get("mode", "regex")
                model = body.get("model", "")
                if body.get("document_id"):
                    run_ids = [analyze_document(conn, int(body["document_id"]), config, mode, model)]
                else:
                    run_ids = analyze_all(conn, config, mode, model)
                return {"run_ids": run_ids}
            if method == "PUT" and path.startswith("/api/evidence/") and path.endswith("/review"):
                evidence_id = int(path.split("/")[-2])
                decision = str(body.get("decision", "accepted"))
                note = str(body.get("note", ""))
                if decision not in {"accepted", "rejected", "needs_followup"}:
                    raise ApiError(400, "Invalid review decision")
                db.review_evidence(conn, evidence_id, decision, note)
                return {"ok": True}
            if method == "POST" and path == "/api/chat":
                message = str(body.get("message", "")).strip()
                if not message:
                    raise ApiError(400, "Message is required")
                return answer_chat(conn, message)
        raise ApiError(404, f"No route for {method} {path}")

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def send_json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def serve_frontend(self, path: str) -> None:
        root = Path("frontend/dist")
        if not root.exists():
            raise ApiError(404, "Frontend build not found. Run npm run build in frontend or use npm run dev.")
        target = (root / path.lstrip("/")).resolve()
        root_resolved = root.resolve()
        if not str(target).startswith(str(root_resolved)) or not target.is_file():
            target = root_resolved / "index.html"
        self.path = "/" + str(target.relative_to(root_resolved)).replace("\\", "/")
        self.directory = str(root_resolved)
        return super().do_GET()


def run(host: str = "127.0.0.1", port: int = 8000, db_path: str = str(db.DB_PATH)) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    server.db_path = db_path  # type: ignore[attr-defined]
    print(f"API server on http://{host}:{port}")
    server.serve_forever()


def answer_chat(conn, message: str) -> dict:
    text = message.lower()
    data = db.dashboard(conn)
    run_ids = [int(row["id"]) for row in data["runs"]]
    details = [db.run_detail(conn, run_id) for run_id in run_ids]

    if any(term in text for term in ["explain this product", "what is this", "what does this do", "how does this work"]):
        answer = (
            "This product reads company reports and checks whether they clearly explain important risks.\n\n"
            "For example, if a company spends a lot on fuel, the product asks: did the report explain what happens if fuel prices rise? "
            "If a company has foreign currency exposure, did it explain what happens if exchange rates move?\n\n"
            "It does not predict stock prices or give advice. It simply shows what the report said, what it did not say, and the exact text behind each finding."
        )
        return _chat_response(answer, [], ["Which reports need a closer look?", "Which company has the biggest fuel cost?", "Show missing explanations"], "local")

    if any(term in text for term in ["largest", "highest", "fuel exposure", "most exposed"]):
        rows = sorted(_peer_rows(details), key=lambda row: row["fuel_share"] or 0, reverse=True)[:5]
        lines = ["The largest disclosed fuel or crude-linked exposure by share of revenue is:"]
        sources = []
        for row in rows:
            lines.append(f"- {row['company']}: {row['fuel_share']:.1f}% of revenue, run #{row['run_id']}.")
            sources.append(_source(row["company"], row["run_id"], "Fuel cost share computed from verified evidence."))
        return _chat_response("\n".join(lines), sources, ["Which reports need a closer look?", "Explain this in simple words"], "local")

    if any(term in text for term in ["missing", "gap", "not disclosed", "sensitivity"]):
        flags = [flag for flag in data["flags"] if flag["flag"] == "MISSING_FUEL_SENSITIVITY"]
        lines = [f"{len(flags)} companies spend a meaningful amount on fuel or import-linked costs, but their report does not clearly say how profits might change if prices move:"]
        sources = []
        for flag in flags[:8]:
            lines.append(f"- {flag['company']} in run #{flag['run_id']}.")
            sources.append(_source(flag["company"], flag["run_id"], flag.get("note") or "Missing fuel sensitivity flag."))
        return _chat_response("\n".join(lines), sources, ["Which one should I review first?", "What does this mean?"])

    if any(term in text for term in ["stale", "old", "outdated", "shock"]):
        stale = [row for row in _peer_rows(details) if row["stale"]]
        if not stale:
            return _chat_response("None of the reports are marked very old by the current rule. Some are still from before the market shock date, so a reviewer may still want to refresh them.", [], ["Show largest exposure", "Which reports need review?"])
        lines = [f"{len(stale)} report looks old enough that the numbers may no longer describe today:"]
        sources = []
        for row in stale:
            lines.append(f"- {row['company']}: period end {row['period_end']}, run #{row['run_id']}.")
            sources.append(_source(row["company"], row["run_id"], "Staleness rule fired."))
        return _chat_response("\n".join(lines), sources, ["Which gaps are high priority?", "Show evidence for MetroFly"])

    if any(term in text for term in ["prompt", "injection", "malicious"]):
        flags = [flag for flag in data["flags"] if flag["flag"] == "PROMPT_INJECTION_TEXT"]
        lines = [f"{len(flags)} source passage contains instruction-like text that an AI system should ignore:"]
        sources = []
        for flag in flags:
            lines.append(f"- {flag['company']}, run #{flag['run_id']}. The source page contains instruction-like text and should be treated only as data.")
            sources.append(_source(flag["company"], flag["run_id"], "Prompt injection text flag."))
        return _chat_response("\n".join(lines), sources, ["Open flagged run", "Why does this matter?"])

    matched = _match_company(details, text)
    if matched:
        run = matched["run"]
        evidence = {row["field"]: row for row in matched["evidence"]}
        flags = [flag["flag"] for flag in matched["flags"] if flag["flag"] != "REVIEW_NOTE"]
        lines = [
            f"{run['company']} has run #{run['id']} for period end {run['period_end']}.",
            f"- Fuel/import cost size: {_fmt_pct(run['fuel_cost_share_revenue_pct'])}.",
            f"- Did it explain fuel price impact? {_fmt_evidence(evidence.get('fuel_sensitivity_impact_crore'))}.",
            f"- Foreign currency exposure: {_fmt_evidence(evidence.get('fx_net_exposure_crore'))}.",
            f"- Did it explain currency impact? {_fmt_evidence(evidence.get('fx_sensitivity_impact_crore'))}.",
            f"- Items to review: {', '.join(_plain_flag(flag) for flag in flags) if flags else 'none'}."
        ]
        return _chat_response("\n".join(lines), [_source(run["company"], run["id"], "Company run summary.")], ["Show source evidence", "Compare with peers"], "local")

    fallback = _fallback_ai(message, data)
    if fallback:
        return _chat_response(fallback, [], ["Ask about a company in this workspace", "Show missing report explanations"], "ai")

    counts = data["counts"]
    high = [flag for flag in data["flags"] if flag["severity"] == "high"]
    answer = (
        "I can answer questions about the reports already loaded here, like which company has the biggest exposure or which reports need review. "
        "For general questions outside this workspace, add an OpenRouter key and model as environment variables.\n\n"
        f"Current workspace: {counts['companies']} companies, {counts['runs']} checked reports, "
        f"{counts['highFlags']} items that need attention."
    )
    return _chat_response(answer, [_source(flag["company"], flag["run_id"], _plain_flag(flag["flag"])) for flag in high[:4]], ["Which company has the largest exposure?", "Show reports that need review", "Summarize BudgetAir"])


def _chat_response(answer: str, sources: list[dict], suggestions: list[str], mode: str = "local") -> dict:
    return {"answer": answer, "sources": sources, "suggestions": suggestions, "mode": mode}


def _fallback_ai(message: str, data: dict) -> str | None:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    model = os.environ.get("OPENROUTER_MODEL")
    if not api_key or not model:
        return None
    prompt = (
        "You are a friendly assistant inside a simple disclosure-checking product. "
        "Answer in plain English for a non-finance user. If useful, mention that the workspace checks whether company reports explain oil/fuel and currency exposure. "
        "Do not give investment advice.\n\n"
        f"Workspace summary: {data['counts']}\n"
        f"User question: {message}"
    )
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(
            {
                "model": model,
                "temperature": 0.3,
                "messages": [
                    {"role": "system", "content": "You explain financial disclosure products in simple, non-technical language."},
                    {"role": "user", "content": prompt},
                ],
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://local.prototype/disclosure-gap-finder",
            "X-Title": "Disclosure Gap Finder Prototype",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"]
    except Exception as exc:
        return f"I tried to use the general AI fallback, but it failed: {exc}"


def _source(company: str, run_id: int, detail: str) -> dict:
    return {"company": company, "run_id": run_id, "detail": detail}


def _peer_rows(details: list[dict]) -> list[dict]:
    rows = []
    for detail in details:
        run = detail["run"]
        rows.append(
            {
                "run_id": int(run["id"]),
                "company": run["company"],
                "sector": run["sector"],
                "period_end": run["period_end"],
                "fuel_share": run["fuel_cost_share_revenue_pct"],
                "stale": bool(run["stale"]),
            }
        )
    return rows


def _match_company(details: list[dict], text: str) -> dict | None:
    for detail in details:
        company = str(detail["run"]["company"]).lower()
        words = [word for word in company.replace("ltd", "").split() if len(word) > 3]
        if company in text or any(word in text for word in words):
            return detail
    return None


def _fmt_pct(value) -> str:
    if value is None:
        return "not available"
    return f"{float(value):.1f}% of revenue"


def _fmt_evidence(row: dict | None) -> str:
    if not row or row.get("value_text") is None:
        return "not disclosed"
    unit = row.get("unit") or ""
    page = f" on page {row['page_number']}" if row.get("page_number") else ""
    return f"{row['value_text']} {unit}{page}".strip()


def _plain_flag(flag: str) -> str:
    names = {
        "MISSING_FUEL_SENSITIVITY": "missing explanation of fuel price impact",
        "PROMPT_INJECTION_TEXT": "source text contains AI instructions",
        "AMBIGUOUS_DISCLOSURE": "conflicting numbers",
        "STALE_DISCLOSURE": "old report",
    }
    return names.get(flag, flag.replace("_", " ").lower())
