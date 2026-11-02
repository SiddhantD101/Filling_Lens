from __future__ import annotations

import html
from pathlib import Path

from .schema import Document, Evidence, Extraction, GapAssessment


def _fmt_evidence(label: str, evidence: Evidence | None) -> str:
    if evidence is None:
        return f"<tr><th>{html.escape(label)}</th><td class='missing'>Not disclosed</td><td></td><td></td></tr>"
    value = html.escape(str(evidence.value))
    quote = html.escape(evidence.quote)
    note = f" <span class='note'>{html.escape(evidence.note)}</span>" if evidence.note else ""
    return (
        f"<tr><th>{html.escape(label)}</th><td>{value} {html.escape(evidence.unit)}</td>"
        f"<td>p. {evidence.page}</td><td><q>{quote}</q>{note}</td></tr>"
    )


def render_card(document: Document, extraction: Extraction, gaps: GapAssessment) -> str:
    flags = " ".join(f"<span class='flag'>{html.escape(flag)}</span>" for flag in gaps.flags) or "<span class='ok'>No gap flag</span>"
    notes = "".join(f"<li>{html.escape(note)}</li>" for note in gaps.notes) or "<li>No review notes.</li>"
    fuel_share = "n/a" if gaps.fuel_cost_share_revenue_pct is None else f"{gaps.fuel_cost_share_revenue_pct:.2f}%"
    synthetic = "Synthetic test excerpt" if document.synthetic else "Public filing excerpt"

    return f"""
    <section class="card">
      <header>
        <div>
          <h2>{html.escape(document.company)}</h2>
          <p>{html.escape(document.sector)} | Period end {document.period_end.isoformat()} | {synthetic}</p>
        </div>
        <div class="flags">{flags}</div>
      </header>
      <div class="metrics">
        <div><strong>Revenue</strong><span>Rs. {document.revenue_crore:,.0f} crore</span></div>
        <div><strong>Fuel cost share</strong><span>{fuel_share}</span></div>
        <div><strong>Review</strong><span>{'Required' if gaps.review_required else 'Not required'}</span></div>
      </div>
      <table>
        <tbody>
          {_fmt_evidence("Fuel/import cost", extraction.fuel_cost_crore)}
          {_fmt_evidence("Fuel sensitivity impact", extraction.fuel_sensitivity_impact_crore)}
          {_fmt_evidence("FX net exposure", extraction.fx_net_exposure_crore)}
          {_fmt_evidence("FX sensitivity impact", extraction.fx_sensitivity_impact_crore)}
          {_fmt_evidence("Hedge ratio", extraction.hedge_ratio_pct)}
          <tr><th>Pass-through language</th><td>{'Present' if extraction.pass_through_present else 'Not found'}</td><td></td><td></td></tr>
          <tr><th>Searched pages</th><td>{', '.join(str(p) for p in extraction.searched_pages)}</td><td></td><td></td></tr>
        </tbody>
      </table>
      <h3>Review notes</h3>
      <ul>{notes}</ul>
    </section>
    """


def write_html(cards: list[str], out_path: str | Path) -> None:
    body = "\n".join(cards)
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Disclosure Gap Finder</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #172026;
      --muted: #5f6b73;
      --line: #d9e0e4;
      --paper: #f7f9fa;
      --accent: #006b5f;
      --warn: #9d2f2f;
      --ok: #1f6f43;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--paper);
      color: var(--ink);
      line-height: 1.45;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px 18px 48px;
    }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: end;
      margin-bottom: 18px;
    }}
    h1 {{ margin: 0; font-size: 28px; }}
    .topbar p {{ margin: 6px 0 0; color: var(--muted); }}
    .card {{
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      margin: 16px 0;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: start;
      border-bottom: 1px solid var(--line);
      padding-bottom: 12px;
    }}
    h2 {{ margin: 0 0 4px; font-size: 20px; }}
    header p {{ margin: 0; color: var(--muted); }}
    .flags {{ display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 6px; min-width: 180px; }}
    .flag, .ok {{
      border-radius: 999px;
      padding: 4px 9px;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .flag {{ background: #f8dddd; color: var(--warn); }}
    .ok {{ background: #dff3e8; color: var(--ok); }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin: 14px 0;
    }}
    .metrics div {{ border: 1px solid var(--line); border-radius: 6px; padding: 10px; }}
    .metrics strong {{ display: block; font-size: 12px; color: var(--muted); }}
    .metrics span {{ display: block; margin-top: 4px; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
    th, td {{ border-top: 1px solid var(--line); padding: 10px 8px; vertical-align: top; text-align: left; }}
    th {{ width: 20%; color: var(--muted); font-weight: 700; }}
    td:nth-child(2) {{ width: 18%; }}
    td:nth-child(3) {{ width: 9%; color: var(--muted); }}
    q {{ quotes: none; }}
    q::before, q::after {{ content: ""; }}
    .missing {{ color: var(--warn); font-weight: 700; }}
    .note {{ color: var(--muted); display: block; margin-top: 4px; }}
    h3 {{ font-size: 15px; margin: 16px 0 6px; }}
    ul {{ margin: 0; padding-left: 18px; }}
    @media (max-width: 760px) {{
      .topbar, header {{ display: block; }}
      .flags {{ justify-content: flex-start; margin-top: 10px; }}
      .metrics {{ grid-template-columns: 1fr; }}
      table, tbody, tr, th, td {{ display: block; width: 100%; }}
      td:nth-child(2), td:nth-child(3) {{ width: 100%; }}
      th {{ border-top: 1px solid var(--line); padding-bottom: 2px; }}
      td {{ border-top: 0; padding-top: 2px; }}
    }}
  </style>
</head>
<body>
  <main>
    <div class="topbar">
      <div>
        <h1>Disclosure Gap Finder</h1>
        <p>Auditable oil/fuel and FX exposure cards generated from labelled prototype examples.</p>
      </div>
    </div>
    {body}
  </main>
</body>
</html>
"""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(html_doc, encoding="utf-8")
