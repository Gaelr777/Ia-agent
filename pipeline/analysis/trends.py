"""Cálculo de tendencias mes a mes por sector: variación de indicadores
INEGI y cambios en la frecuencia de habilidades solicitadas.

La agregación se hace en Python (no en SQL) a propósito: el volumen mensual
de vacantes por sector es manejable (cientos, no millones de filas), así
que no vale la pena la complejidad de funciones PL/pgSQL para esto.
"""
from collections import Counter
from dataclasses import dataclass
from datetime import date

from dateutil.relativedelta import relativedelta

from pipeline.common.supabase_client import get_client


@dataclass
class IndicatorTrend:
    source: str
    description: str
    current_period: str
    current_value: float | None
    previous_value: float | None

    @property
    def delta_abs(self) -> float | None:
        if self.current_value is None or self.previous_value is None:
            return None
        return self.current_value - self.previous_value

    @property
    def delta_pct(self) -> float | None:
        if not self.previous_value:
            return None
        return (self.delta_abs or 0) / self.previous_value * 100


def inegi_trends(sector: str, period: date) -> list[IndicatorTrend]:
    client = get_client()
    series_rows = (
        client.table("inegi_series")
        .select("id, source, description")
        .or_(f"scian_code.eq.{sector},scian_code.is.null")
        .execute()
        .data
    )

    previous_period = period - relativedelta(months=1)
    trends = []
    for series in series_rows:
        snapshots = (
            client.table("inegi_snapshots")
            .select("period, value")
            .eq("series_id", series["id"])
            .in_("period", [period.isoformat(), previous_period.isoformat()])
            .execute()
            .data
        )
        by_period = {row["period"]: row["value"] for row in snapshots}
        trends.append(
            IndicatorTrend(
                source=series["source"],
                description=series["description"],
                current_period=period.isoformat(),
                current_value=by_period.get(period.isoformat()),
                previous_value=by_period.get(previous_period.isoformat()),
            )
        )
    return trends


def _skill_counts(client, sector: str, snapshot_month: date, skill_type: str) -> Counter:
    postings = (
        client.table("job_postings")
        .select("id")
        .eq("scian_code", sector)
        .eq("snapshot_month", snapshot_month.isoformat())
        .execute()
        .data
    )
    posting_ids = [p["id"] for p in postings]
    if not posting_ids:
        return Counter()

    skill_links = (
        client.table("job_posting_skills")
        .select("skill_id, skills_catalog(display_name, skill_type)")
        .in_("job_posting_id", posting_ids)
        .execute()
        .data
    )
    counter = Counter()
    for link in skill_links:
        catalog = link.get("skills_catalog") or {}
        if catalog.get("skill_type") == skill_type:
            counter[catalog["display_name"]] += 1
    return counter


def top_skills(sector: str, snapshot_month: date, skill_type: str, limit: int = 15) -> list[tuple[str, int]]:
    client = get_client()
    return _skill_counts(client, sector, snapshot_month, skill_type).most_common(limit)


def skills_month_over_month(sector: str, current_month: date, skill_type: str, limit: int = 10) -> dict:
    client = get_client()
    previous_month = current_month - relativedelta(months=1)
    current_counts = _skill_counts(client, sector, current_month, skill_type)
    previous_counts = _skill_counts(client, sector, previous_month, skill_type)

    all_skills = set(current_counts) | set(previous_counts)
    deltas = {
        skill: current_counts.get(skill, 0) - previous_counts.get(skill, 0)
        for skill in all_skills
    }
    rising = sorted(deltas.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    falling = sorted(deltas.items(), key=lambda kv: kv[1])[:limit]
    return {"rising": rising, "falling": falling}
