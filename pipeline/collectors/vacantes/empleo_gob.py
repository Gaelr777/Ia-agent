"""Colector para el Portal del Empleo (empleo.gob.mx / STPS), fuente
primaria recomendada — ver docs/LEGAL_TOS.md.

El portal es una SPA de Angular (el HTML crudo no trae las vacantes), pero
usa una API JSON interna para la búsqueda que confirmamos inspeccionando el
tráfico de red del sitio real:

    POST https://www.empleo.gob.mx/api/Login/busqueda/empleos
    body: {"que": "<palabra clave>", "donde": {}, "items": 50, "page": 0,
           "orden": "fecha_publicacion desc", "filter": {}}

Solo se pide la primera página (50 resultados más recientes) por palabra
clave — suficiente para un resumen mensual, no se busca ser exhaustivo.
"""
from datetime import date, datetime

from pipeline.collectors.vacantes.base import JobPosting, RateLimitedSession

SEARCH_URL = "https://www.empleo.gob.mx/api/Login/busqueda/empleos"

SECTOR_KEYWORDS: dict[str, list[str]] = {
    "31-33": ["manufactura", "producción industrial", "operador de máquina", "planta industrial"],
    "54": ["servicios profesionales", "consultoría"],
    # Agrega más sectores conforme los necesites (ver data/scian_sectors.json).
}


def search(scian_code: str, max_results: int = 50) -> list[JobPosting]:
    keywords = SECTOR_KEYWORDS.get(scian_code)
    if not keywords:
        print(f"No hay keywords configuradas para el sector {scian_code} en SECTOR_KEYWORDS.")
        return []

    session = RateLimitedSession()
    postings: list[JobPosting] = []

    for keyword in keywords:
        payload = {
            "que": keyword,
            "donde": {},
            "items": max_results,
            "page": 0,
            "orden": "fecha_publicacion desc",
            "filter": {},
        }
        try:
            response = session.post(
                SEARCH_URL,
                json=payload,
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Origin": "https://www.empleo.gob.mx",
                    "Referer": "https://www.empleo.gob.mx/PortalDigital",
                },
            )
        except Exception as exc:
            print(f"Aviso: búsqueda '{keyword}' falló, se omite: {exc}")
            continue

        if response.status_code != 200:
            print(f"Aviso: búsqueda '{keyword}' devolvió HTTP {response.status_code}, se omite.")
            continue

        for item in response.json().get("content", []):
            posting = _parse_item(item)
            if posting:
                postings.append(posting)

    seen = set()
    unique = []
    for p in postings:
        if p.external_id not in seen:
            seen.add(p.external_id)
            unique.append(p)
    return unique


def _parse_item(item: dict) -> JobPosting | None:
    vacancy_id = item.get("id")
    title = item.get("tituloOferta")
    if vacancy_id is None or not title:
        return None

    return JobPosting(
        external_id=str(vacancy_id),
        title=title,
        company=item.get("nombreEmpresa"),
        location=_location(item),
        description_raw=item.get("descripcion") or "",
        # La ruta real incluye el título en slug (ej. .../21037150-MECANICO-OPERADOR/Manufactura);
        # no lo reconstruimos, así que este link puede no resolver perfecto, pero el ID sí es correcto.
        description_url=f"https://www.empleo.gob.mx/puesto-de-trabajo/vacante/{vacancy_id}",
        salary_min=_salary(item.get("salarioOfrecido")),
        salary_max=_salary(item.get("salarioOfrecidoMaximo")),
        posted_at=_parse_posted_at(item.get("fechaPublicacion")),
    )


def _location(item: dict) -> str | None:
    parts = [p for p in (item.get("municipio"), item.get("entidad")) if p]
    return ", ".join(parts) if parts else None


def _salary(value) -> float | None:
    # El portal manda 0.0 cuando el campo no está especificado.
    if not value:
        return None
    return float(value)


def _parse_posted_at(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None
