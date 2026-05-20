from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from psycopg2.extras import Json, execute_values

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scrapers.governance.access_strategy import infer_access_strategy, upsert_access_strategy
from scrapers.governance.evidence_quality import compute_contamination_rate, compute_evidence_quality
from scrapers.governance.freshness_scoring import compute_freshness_score, freshness_label
from scrapers.governance.source_reliability import (
    apply_schema,
    classify_source_tier,
    compute_reliability,
    get_connection,
    list_sources,
    snapshot_to_dict,
)
from scrapers.governance.source_sla import compute_sla_metrics, upsert_sla_metrics


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def gold_readiness(row: dict[str, Any], *, min_reliability: float = 0.74) -> bool:
    return (
        row["reliability_score"] >= min_reliability
        and row["blocked_auth_rate"] <= 0.05
        and row["contamination_rate"] <= 0.12
        and row["evidence_quality"] >= 0.62
        and row["freshness_score"] >= 0.45
        and row["extraction_completeness"] >= 0.55
    )


def build_source_row(source: str) -> dict[str, Any]:
    reliability = snapshot_to_dict(compute_reliability(source))
    evidence = compute_evidence_quality(source)
    freshness = compute_freshness_score(source)
    sla = compute_sla_metrics(source)
    access = infer_access_strategy(source)
    contamination = compute_contamination_rate(source)
    row = {
        **reliability,
        "freshness_score": freshness,
        "freshness_label": freshness_label(freshness),
        "contamination_rate": contamination,
        "evidence_quality": evidence["evidence_quality"] or reliability["evidence_quality"],
        "source_stability": min(reliability["source_stability"], sla["response_stability"]),
        "access_strategy": access["access_strategy"],
        "access_risk_level": access["risk_level"],
        "sla": sla,
        "access": access,
        "evidence": evidence,
    }
    ready = gold_readiness(row)
    row["gold_readiness"] = ready
    row["source_tier"] = classify_source_tier(compute_reliability(source), ready)
    row["notes"] = recommended_note(row)
    return row


def recommended_note(row: dict[str, Any]) -> str:
    if row["blocked_auth_rate"] > 0.15 or row["access_strategy"] == "blocked_auth":
        return "resolver acceso autorizado antes de promocionar fuente"
    if row["contamination_rate"] > 0.18:
        return "ajustar normalizacion y filtros anti-contaminacion"
    if row["freshness_score"] < 0.35:
        return "programar nueva corrida o revisar scheduler"
    if row["evidence_quality"] < 0.55:
        return "elevar densidad de descripcion, skills y detalle"
    if row["gold_readiness"]:
        return "fuente apta para pruebas de KPI institucional"
    return "mantener como fuente observada hasta mejorar umbrales"


def persist_governance(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with get_connection() as conn, conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO public.source_governance (
                source, source_tier, reliability_score, freshness_score,
                contamination_rate, blocked_auth_rate, semantic_density,
                evidence_quality, extraction_completeness, source_stability,
                gold_readiness, access_strategy, notes, metadata
            )
            VALUES %s
            ON CONFLICT (source) DO UPDATE SET
                source_tier = EXCLUDED.source_tier,
                reliability_score = EXCLUDED.reliability_score,
                freshness_score = EXCLUDED.freshness_score,
                contamination_rate = EXCLUDED.contamination_rate,
                blocked_auth_rate = EXCLUDED.blocked_auth_rate,
                semantic_density = EXCLUDED.semantic_density,
                evidence_quality = EXCLUDED.evidence_quality,
                extraction_completeness = EXCLUDED.extraction_completeness,
                source_stability = EXCLUDED.source_stability,
                gold_readiness = EXCLUDED.gold_readiness,
                access_strategy = EXCLUDED.access_strategy,
                notes = EXCLUDED.notes,
                metadata = EXCLUDED.metadata,
                computed_at = now()
            """,
            [
                (
                    row["source"],
                    row["source_tier"],
                    row["reliability_score"],
                    row["freshness_score"],
                    row["contamination_rate"],
                    row["blocked_auth_rate"],
                    row["semantic_density"],
                    row["evidence_quality"],
                    row["extraction_completeness"],
                    row["source_stability"],
                    row["gold_readiness"],
                    row["access_strategy"],
                    row["notes"],
                    Json(json_safe({"sla": row["sla"], "access": row["access"], "evidence": row["evidence"]})),
                )
                for row in rows
            ],
        )
        execute_values(
            cur,
            """
            INSERT INTO public.source_quality_history (
                source, source_tier, reliability_score, freshness_score,
                contamination_rate, blocked_auth_rate, semantic_density,
                evidence_quality, extraction_completeness, source_stability,
                gold_readiness, access_strategy, metadata
            )
            VALUES %s
            ON CONFLICT (source, snapshot_date) DO UPDATE SET
                source_tier = EXCLUDED.source_tier,
                reliability_score = EXCLUDED.reliability_score,
                freshness_score = EXCLUDED.freshness_score,
                contamination_rate = EXCLUDED.contamination_rate,
                blocked_auth_rate = EXCLUDED.blocked_auth_rate,
                semantic_density = EXCLUDED.semantic_density,
                evidence_quality = EXCLUDED.evidence_quality,
                extraction_completeness = EXCLUDED.extraction_completeness,
                source_stability = EXCLUDED.source_stability,
                gold_readiness = EXCLUDED.gold_readiness,
                access_strategy = EXCLUDED.access_strategy,
                metadata = EXCLUDED.metadata
            """,
            [
                (
                    row["source"],
                    row["source_tier"],
                    row["reliability_score"],
                    row["freshness_score"],
                    row["contamination_rate"],
                    row["blocked_auth_rate"],
                    row["semantic_density"],
                    row["evidence_quality"],
                    row["extraction_completeness"],
                    row["source_stability"],
                    row["gold_readiness"],
                    row["access_strategy"],
                    Json(json_safe({"sla": row["sla"], "access": row["access"], "evidence": row["evidence"]})),
                )
                for row in rows
            ],
        )
    for row in rows:
        upsert_access_strategy(row["access"])
        upsert_sla_metrics(row["sla"])


def render_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Source Governance Dashboard",
        "",
        "Dashboard tecnico interno para confiabilidad de fuentes laborales.",
        "",
        "| Fuente | Tier | Reliability | Freshness | Contaminacion | Blocked auth | Evidencia | Completitud | Acceso | Gold readiness |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in sorted(rows, key=lambda item: item["reliability_score"], reverse=True):
        lines.append(
            "| {source} | {source_tier} | {reliability_score:.2f} | {freshness_score:.2f} | "
            "{contamination_rate:.2f} | {blocked_auth_rate:.2f} | {evidence_quality:.2f} | "
            "{extraction_completeness:.2f} | {access_strategy} | {gold_readiness} |".format(**row)
        )
    lines.extend(["", "## Recomendaciones", ""])
    for row in rows:
        lines.append(f"- `{row['source']}`: {row['notes']}.")
    return "\n".join(lines) + "\n"


def render_html(rows: list[dict[str, Any]]) -> str:
    sorted_rows = sorted(rows, key=lambda item: item["reliability_score"], reverse=True)
    cards = []
    table_rows = []
    for row in sorted_rows:
        tier_class = row["source_tier"].lower()
        cards.append(
            f"""
            <article class="source-card {tier_class}">
              <div>
                <span class="eyebrow">{row['source_tier']}</span>
                <h2>{row['source']}</h2>
              </div>
              <strong>{row['reliability_score']:.2f}</strong>
              <p>{row['notes']}</p>
              <div class="metrics">
                <span>Freshness <b>{row['freshness_score']:.2f}</b></span>
                <span>Blocked auth <b>{row['blocked_auth_rate']:.2f}</b></span>
                <span>Evidence <b>{row['evidence_quality']:.2f}</b></span>
              </div>
            </article>
            """
        )
        table_rows.append(
            f"""
            <tr>
              <td><strong>{row['source']}</strong><small>{row['access_strategy']}</small></td>
              <td><span class="pill {tier_class}">{row['source_tier']}</span></td>
              <td>{row['reliability_score']:.2f}</td>
              <td>{row['freshness_score']:.2f}</td>
              <td>{row['contamination_rate']:.2f}</td>
              <td>{row['blocked_auth_rate']:.2f}</td>
              <td>{row['evidence_quality']:.2f}</td>
              <td>{'Ready' if row['gold_readiness'] else 'Blocked'}</td>
            </tr>
            """
        )
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Source Governance Dashboard</title>
  <style>
    :root {{
      --ink: #111827;
      --muted: #64748b;
      --line: #e5e7eb;
      --blue: #005baa;
      --bg: #f6f8fb;
      --white: #ffffff;
      --warn: #b45309;
      --bad: #991b1b;
      --ok: #166534;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, "Segoe UI", Arial, sans-serif;
      color: var(--ink);
      background: var(--bg);
    }}
    header {{
      background: var(--white);
      border-bottom: 1px solid var(--line);
      padding: 22px 40px;
    }}
    header small {{
      color: var(--blue);
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 8px 0 4px;
      font-size: 30px;
      line-height: 1.15;
      font-weight: 650;
    }}
    header p {{ margin: 0; color: var(--muted); max-width: 880px; }}
    main {{ padding: 28px 40px 44px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 14px;
      margin-bottom: 24px;
    }}
    .source-card {{
      background: var(--white);
      border: 1px solid var(--line);
      border-top: 3px solid var(--blue);
      padding: 16px;
      min-height: 172px;
    }}
    .source-card.experimental {{ border-top-color: var(--bad); }}
    .source-card.bronze {{ border-top-color: var(--warn); }}
    .source-card.silver {{ border-top-color: #64748b; }}
    .source-card.gold {{ border-top-color: var(--ok); }}
    .source-card h2 {{ margin: 4px 0 0; font-size: 20px; font-weight: 650; }}
    .source-card strong {{ display: block; margin-top: 12px; font-size: 34px; font-weight: 650; }}
    .source-card p {{ min-height: 40px; color: var(--muted); font-size: 13px; }}
    .eyebrow {{ font-size: 11px; text-transform: uppercase; color: var(--muted); font-weight: 700; letter-spacing: .08em; }}
    .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; font-size: 12px; color: var(--muted); }}
    .metrics span {{ border-top: 1px solid var(--line); padding-top: 8px; }}
    .metrics b {{ display: block; margin-top: 2px; color: var(--ink); }}
    section {{
      background: var(--white);
      border: 1px solid var(--line);
    }}
    .section-head {{
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
    }}
    .section-head h2 {{ margin: 0; font-size: 18px; font-weight: 650; }}
    .section-head span {{ color: var(--muted); font-size: 13px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 13px 18px; border-bottom: 1px solid var(--line); text-align: left; font-size: 14px; }}
    th {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .06em; }}
    td small {{ display: block; color: var(--muted); margin-top: 3px; }}
    .pill {{ display: inline-flex; padding: 4px 8px; border: 1px solid var(--line); font-size: 12px; }}
    .pill.experimental {{ color: var(--bad); background: #fef2f2; border-color: #fecaca; }}
    .pill.bronze {{ color: var(--warn); background: #fffbeb; border-color: #fde68a; }}
    .pill.silver {{ color: #475569; background: #f8fafc; }}
    .pill.gold {{ color: var(--ok); background: #f0fdf4; border-color: #bbf7d0; }}
    @media (max-width: 760px) {{
      header, main {{ padding-left: 18px; padding-right: 18px; }}
      table {{ display: block; overflow-x: auto; }}
    }}
  </style>
</head>
<body>
  <header>
    <small>Labor Intelligence Governance</small>
    <h1>Source Governance Dashboard</h1>
    <p>Salud, confiabilidad y readiness de fuentes laborales antes de alimentar KPIs institucionales.</p>
  </header>
  <main>
    <div class="grid">
      {''.join(cards)}
    </div>
    <section>
      <div class="section-head">
        <h2>Reliability matrix</h2>
        <span>{len(rows)} fuentes evaluadas</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>Fuente</th>
            <th>Tier</th>
            <th>Reliability</th>
            <th>Freshness</th>
            <th>Contaminacion</th>
            <th>Blocked auth</th>
            <th>Evidencia</th>
            <th>Gold</th>
          </tr>
        </thead>
        <tbody>
          {''.join(table_rows)}
        </tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


def build_dashboard(*, sources: list[str] | None = None, write_db: bool = False) -> dict[str, Any]:
    apply_schema()
    selected_sources = sources or list_sources()
    rows = [build_source_row(source) for source in selected_sources]
    output_dir = ROOT_DIR / "outputs" / "source_governance"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "source_governance_dashboard.json"
    md_path = output_dir / "source_governance_dashboard.md"
    html_path = output_dir / "source_governance_dashboard.html"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render_markdown(rows), encoding="utf-8")
    html_path.write_text(render_html(rows), encoding="utf-8")
    if write_db:
        persist_governance(rows)
    return {
        "sources": len(rows),
        "json": str(json_path),
        "markdown": str(md_path),
        "html": str(html_path),
        "write_db": write_db,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build source governance and data reliability dashboard.")
    parser.add_argument("--sources", nargs="*", default=None)
    parser.add_argument("--write-db", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build_dashboard(sources=args.sources, write_db=args.write_db), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
