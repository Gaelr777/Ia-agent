"""Genera el reporte mensual de un sector: combina tendencias de INEGI,
top skills y comparativo mes a mes, y lo guarda en `monthly_sector_reports`.

Uso:
    python -m pipeline.analysis.generate_report --sector 31-33 --period 2026-07
"""
import argparse
from datetime import date, datetime, timezone

from pipeline.analysis.trends import inegi_trends, skills_month_over_month, top_skills
from pipeline.common.supabase_client import get_client


def _parse_period(value: str) -> date:
    year, month = value.split("-")
    return date(int(year), int(month), 1)


def build_report(sector: str, period: date) -> dict:
    indicator_trends = inegi_trends(sector, period)
    hard_skills = top_skills(sector, period, "hard")
    soft_skills = top_skills(sector, period, "soft")
    hard_mom = skills_month_over_month(sector, period, "hard")
    soft_mom = skills_month_over_month(sector, period, "soft")

    return {
        "sector": sector,
        "period": period.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inegi_indicators": [
            {
                "source": t.source,
                "description": t.description,
                "current_value": t.current_value,
                "previous_value": t.previous_value,
                "delta_abs": t.delta_abs,
                "delta_pct": t.delta_pct,
            }
            for t in indicator_trends
        ],
        "top_hard_skills": [{"skill": s, "count": c} for s, c in hard_skills],
        "top_soft_skills": [{"skill": s, "count": c} for s, c in soft_skills],
        "hard_skills_month_over_month": hard_mom,
        "soft_skills_month_over_month": soft_mom,
    }


def render_summary_md(report: dict) -> str:
    lines = [f"# Reporte de mercado laboral — sector {report['sector']} — {report['period']}", ""]

    lines.append("## Indicadores INEGI")
    for ind in report["inegi_indicators"]:
        delta = f"{ind['delta_pct']:+.1f}%" if ind["delta_pct"] is not None else "s/d"
        lines.append(f"- **{ind['source']}** — {ind['description']}: {ind['current_value']} ({delta} vs. mes anterior)")

    lines.append("\n## Habilidades técnicas más demandadas")
    for item in report["top_hard_skills"]:
        lines.append(f"- {item['skill']} ({item['count']} vacantes)")

    lines.append("\n## Habilidades blandas más demandadas")
    for item in report["top_soft_skills"]:
        lines.append(f"- {item['skill']} ({item['count']} vacantes)")

    rising = report["hard_skills_month_over_month"]["rising"]
    if rising:
        lines.append("\n## Habilidades técnicas en ascenso (vs. mes anterior)")
        for skill, delta in rising:
            if delta > 0:
                lines.append(f"- {skill}: +{delta}")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sector", required=True)
    parser.add_argument("--period", required=True, help="YYYY-MM")
    args = parser.parse_args()

    period = _parse_period(args.period)
    report = build_report(args.sector, period)
    summary_md = render_summary_md(report)

    client = get_client()
    client.table("monthly_sector_reports").upsert(
        {
            "scian_code": args.sector,
            "period": period.isoformat(),
            "report_json": report,
            "summary_md": summary_md,
        },
        on_conflict="scian_code,period",
    ).execute()

    print(summary_md)


if __name__ == "__main__":
    main()
