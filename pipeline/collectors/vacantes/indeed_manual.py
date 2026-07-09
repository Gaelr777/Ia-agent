"""Importador manual de vacantes de Indeed.

Indeed no permite scraping automatizado (ver docs/LEGAL_TOS.md) y ya no
ofrece una API pública self-service. Sin embargo, dentro de una sesión de
chat de Claude hay disponible un conector oficial (`search_jobs` /
`get_job_details`) que trae datos reales de la API de búsqueda de Indeed —
no es scraping, pero tampoco es una credencial que se pueda usar desde un
script desatendido en GitHub Actions: solo funciona de forma interactiva,
ligada a esa sesión de chat.

Este script es la mitad "automatizable" de un flujo en dos pasos:

  1. En una sesión de chat de Claude con el conector de Indeed disponible,
     corre búsquedas por sector (`search_jobs` para descubrir vacantes,
     `get_job_details` por cada una para la descripción completa y el
     salario) y arma un JSON con la lista según el esquema de abajo.
  2. Pega ese JSON en el input del workflow `indeed-manual-import.yml`
     (Actions -> Run workflow) — ese workflow sí tiene las credenciales de
     Supabase como secreto del repo y llama a este script para persistir
     los resultados con el mismo `persist_postings()` que usan las demás
     fuentes.

Esquema esperado (lista de objetos JSON):
    {
        "external_id": "...",      # requerido: Job Id de Indeed
        "title": "...",            # requerido
        "company": "...",          # opcional
        "location": "...",         # opcional
        "description_raw": "...",  # opcional pero recomendado (alimenta skills_extraction.py)
        "description_url": "...", # recomendado: el link de "aplicar" que trae get_job_details.
                                    # Indeed pide conservar este link junto al título de la
                                    # vacante en cualquier lugar donde se muestre — no lo omitas
                                    # si en algún momento este dato se expone en un reporte/dashboard.
        "salary_min": 0.0,         # opcional
        "salary_max": 0.0,         # opcional
        "posted_at": "YYYY-MM-DD"  # opcional
    }

Uso:
    python -m pipeline.collectors.vacantes.indeed_manual --sector 31-33 --input vacantes.json
    cat vacantes.json | python -m pipeline.collectors.vacantes.indeed_manual --sector 31-33
"""
import argparse
import json
import sys
from datetime import date, datetime

from pipeline.collectors.vacantes.base import JobPosting, persist_postings

SOURCE_NAME = "indeed"


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def parse_postings(raw_items: list[dict]) -> list[JobPosting]:
    postings = []
    for item in raw_items:
        external_id = item.get("external_id")
        title = item.get("title")
        if not external_id or not title:
            print(f"Aviso: item sin external_id/title, se omite: {item}")
            continue
        postings.append(
            JobPosting(
                external_id=str(external_id),
                title=title,
                company=item.get("company"),
                location=item.get("location"),
                description_raw=item.get("description_raw") or "",
                description_url=item.get("description_url"),
                salary_min=item.get("salary_min"),
                salary_max=item.get("salary_max"),
                posted_at=_parse_date(item.get("posted_at")),
            )
        )
    return postings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sector", required=True, help="Código SCIAN, ej. '31-33'")
    parser.add_argument(
        "--input",
        default="-",
        help="Ruta a un archivo JSON con la lista de vacantes, o '-' para leer de stdin (default).",
    )
    args = parser.parse_args()

    raw_text = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()
    raw_items = json.loads(raw_text)

    postings = parse_postings(raw_items)
    count = persist_postings(SOURCE_NAME, args.sector, postings)
    print(f"Vacantes de Indeed insertadas/actualizadas: {count}")


if __name__ == "__main__":
    main()
