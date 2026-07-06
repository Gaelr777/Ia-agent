"""Orquestador del colector de INEGI: lee series_config.yaml, trae los
indicadores nacionales + los del sector pedido, y hace upsert en
`inegi_series` / `inegi_snapshots`.

Uso:
    python -m pipeline.collectors.inegi.collect --sector 31-33
"""
import argparse
from pathlib import Path

import yaml

from pipeline.collectors.inegi.client import fetch_indicators, parse_observations
from pipeline.common.collection_log import CollectionRun
from pipeline.common.supabase_client import get_client

_CONFIG_PATH = Path(__file__).parent / "series_config.yaml"


def _load_config() -> dict:
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _series_for_sector(config: dict, sector: str) -> list[dict]:
    entries = list(config.get("national", []))
    entries += config.get("by_sector", {}).get(sector, [])
    return [e for e in entries if e["indicator_id"] != "TODO"]


def _upsert_series_row(client, sector: str | None, entry: dict) -> str:
    row = (
        client.table("inegi_series")
        .upsert(
            {
                "scian_code": sector,
                "indicator_id": entry["indicator_id"],
                "source": entry["source"],
                "description": entry["description"],
                "frequency": entry.get("frequency", "monthly"),
                "verified": entry.get("verified", False),
            },
            on_conflict="indicator_id,source",
        )
        .execute()
    )
    return row.data[0]["id"]


def collect_for_sector(sector: str) -> int:
    config = _load_config()
    entries = _series_for_sector(config, sector)
    if not entries:
        print(f"No hay series configuradas para el sector {sector} (revisa series_config.yaml).")
        return 0

    client = get_client()
    total_snapshots = 0

    for entry in entries:
        is_national = entry in config.get("national", [])
        sector_for_row = None if is_national else sector
        series_id = _upsert_series_row(client, sector_for_row, entry)

        raw = fetch_indicators([entry["indicator_id"]])
        observations = parse_observations(raw)

        for obs in observations:
            client.table("inegi_snapshots").upsert(
                {
                    "series_id": series_id,
                    "period": obs["period"],
                    "value": obs["value"],
                },
                on_conflict="series_id,period",
            ).execute()
        total_snapshots += len(observations)

    return total_snapshots


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sector", required=True, help="Código SCIAN, ej. '31-33'")
    args = parser.parse_args()

    with CollectionRun("inegi", scian_code=args.sector) as run:
        count = collect_for_sector(args.sector)
        run.records_collected = count
        print(f"Snapshots insertados/actualizados: {count}")


if __name__ == "__main__":
    main()
