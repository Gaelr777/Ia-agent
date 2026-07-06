"""Orquestador del colector de vacantes: corre cada fuente habilitada para
un sector y persiste los resultados.

Uso:
    python -m pipeline.collectors.vacantes.collect --sector 31-33
"""
import argparse

from pipeline.collectors.vacantes import empleo_gob, occ_mundial
from pipeline.collectors.vacantes.base import persist_postings
from pipeline.common.collection_log import CollectionRun

# Orden = prioridad. empleo_gob.py es la fuente primaria recomendada
# (ver docs/LEGAL_TOS.md); las demás son opcionales y están deshabilitadas
# por defecto tanto a nivel de flag como en la tabla job_sources.
SOURCES = [
    ("empleo_gob_mx", empleo_gob),
    ("occ_mundial", occ_mundial),
]


def collect_for_sector(sector: str) -> int:
    total = 0
    for source_name, module in SOURCES:
        try:
            postings = module.search(sector)
        except Exception as exc:
            print(f"Aviso: colector {source_name} falló para sector {sector}: {exc}")
            continue
        if postings:
            total += persist_postings(source_name, sector, postings)
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sector", required=True, help="Código SCIAN, ej. '31-33'")
    args = parser.parse_args()

    with CollectionRun("vacantes", scian_code=args.sector) as run:
        count = collect_for_sector(args.sector)
        run.records_collected = count
        print(f"Vacantes insertadas/actualizadas: {count}")


if __name__ == "__main__":
    main()
