"""Exploración puntual del catálogo de datos.gob.mx (portal de datos abiertos
del gobierno mexicano, corre sobre CKAN) buscando datasets de empleo,
vacantes o mercado laboral.

No es un colector de producción — es un script de reconocimiento para
decidir si vale la pena construir uno. Si encuentra un dataset útil, el
siguiente paso sería un colector real que descargue ese recurso específico
(CSV/JSON) en vez de este script exploratorio.

Uso: python -m pipeline.collectors.explore_datos_gob
"""
import requests

BASE_URL = "https://datos.gob.mx/busca/api/3/action/package_search"

QUERIES = ["empleo", "vacantes", "mercado laboral", "IMSS puestos de trabajo"]

USER_AGENT = (
    "MonitorMercadoLaboralMX/1.0 (+bot de investigación de mercado laboral; "
    "contacto: configura CONTACT_EMAIL en el workflow)"
)


def search(query: str, rows: int = 5) -> list[dict]:
    response = requests.get(
        BASE_URL,
        params={"q": query, "rows": rows},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("success"):
        print(f"  Respuesta sin éxito para '{query}': {data}")
        return []
    return data["result"]["results"]


def main() -> None:
    for query in QUERIES:
        print(f"=== Buscando: '{query}' ===")
        try:
            results = search(query)
        except Exception as exc:
            print(f"  ERROR al buscar '{query}': {exc}")
            continue

        if not results:
            print("  Sin resultados.")
            continue

        for pkg in results:
            title = pkg.get("title", "(sin título)")
            org = (pkg.get("organization") or {}).get("title", "(sin organización)")
            notes = (pkg.get("notes") or "").replace("\n", " ")[:200]
            resources = pkg.get("resources", [])
            formats = ", ".join(sorted({r.get("format", "?") for r in resources})) or "sin recursos"
            print(f"  - {title}")
            print(f"    Organización: {org}")
            print(f"    Formatos: {formats}")
            if notes:
                print(f"    Notas: {notes}")
        print()


if __name__ == "__main__":
    main()
