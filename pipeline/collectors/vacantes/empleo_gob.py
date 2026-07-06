"""Colector para el Portal del Empleo (empleo.gob.mx / STPS), fuente
primaria recomendada — ver docs/LEGAL_TOS.md.

ESTADO: esqueleto funcional, con los TODOs marcados donde hace falta
inspeccionar la estructura HTML real del sitio (este entorno de desarrollo
no tiene salida de red hacia dominios públicos, así que no pude abrir el
sitio para mapear los selectores exactos). Antes de usarlo en producción:

1. Abre https://www.empleo.gob.mx/ en un navegador, busca vacantes por
   palabra clave del sector (ej. "manufactura", "producción industrial") y
   revisa con las devtools la estructura del listado de resultados.
2. Actualiza `RESULT_ITEM_SELECTOR` y los selectores de campos abajo.
3. Si encuentras que el portal expone un endpoint JSON/XML detrás del
   buscador (común en portales de bolsa de trabajo gubernamentales,
   pensado para sindicación), prefiere consumir ese endpoint directamente
   en vez de parsear HTML — es más estable y explícitamente ToS-friendly.

Palabras clave por sector: usa `SECTOR_KEYWORDS` en este archivo para mapear
un código SCIAN a términos de búsqueda razonables.
"""
from datetime import date

from bs4 import BeautifulSoup

from pipeline.collectors.vacantes.base import JobPosting, RateLimitedSession

SEARCH_URL = "https://www.empleo.gob.mx/PortalWeb/BuscarVacante"  # TODO: confirma la ruta real de búsqueda

SECTOR_KEYWORDS: dict[str, list[str]] = {
    "31-33": ["manufactura", "producción industrial", "operador de máquina", "planta industrial"],
    "54": ["servicios profesionales", "consultoría"],
    # Agrega más sectores conforme los necesites (ver data/scian_sectors.json).
}

RESULT_ITEM_SELECTOR = "div.vacante-card"  # TODO: verificar contra el HTML real


def search(scian_code: str, max_results: int = 50) -> list[JobPosting]:
    keywords = SECTOR_KEYWORDS.get(scian_code)
    if not keywords:
        print(f"No hay keywords configuradas para el sector {scian_code} en SECTOR_KEYWORDS.")
        return []

    session = RateLimitedSession()
    postings: list[JobPosting] = []

    for keyword in keywords:
        response = session.get(SEARCH_URL, params={"q": keyword})
        if response.status_code != 200:
            print(f"Aviso: búsqueda '{keyword}' devolvió HTTP {response.status_code}, se omite.")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        for item in soup.select(RESULT_ITEM_SELECTOR)[: max_results]:
            posting = _parse_item(item)
            if posting:
                postings.append(posting)

    # Dedup por external_id (una vacante puede salir en varias búsquedas de keyword)
    seen = set()
    unique = []
    for p in postings:
        if p.external_id not in seen:
            seen.add(p.external_id)
            unique.append(p)
    return unique


def _parse_item(item) -> JobPosting | None:
    # TODO: ajustar selectores a la estructura real del sitio.
    title_el = item.select_one(".titulo-vacante")
    if title_el is None:
        return None
    external_id = item.get("data-vacante-id") or title_el.get_text(strip=True)

    return JobPosting(
        external_id=str(external_id),
        title=title_el.get_text(strip=True),
        company=_text_or_none(item.select_one(".empresa")),
        location=_text_or_none(item.select_one(".ubicacion")),
        description_raw=_text_or_none(item.select_one(".descripcion")) or "",
        description_url=_href_or_none(item.select_one("a")),
        posted_at=date.today(),
    )


def _text_or_none(el) -> str | None:
    return el.get_text(strip=True) if el else None


def _href_or_none(el) -> str | None:
    return el.get("href") if el else None
