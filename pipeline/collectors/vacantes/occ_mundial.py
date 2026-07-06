"""Colector OPCIONAL para OCC Mundial. Lee docs/LEGAL_TOS.md antes de
habilitar esto — el ToS de OCC restringe la extracción automatizada.

Deshabilitado por defecto. Para habilitarlo explícitamente:
  1. Pon `enabled=true` en la fila 'occ_mundial' de la tabla `job_sources`.
  2. Exporta ENABLE_OCC_SCRAPER=true en el workflow.
  3. Mantén el volumen bajo (pocas búsquedas por sector al mes) y respeta
     el rate limiting de `RateLimitedSession`.

Requiere Playwright porque OCC Mundial renderiza resultados vía JS (no es
HTML estático). No incluido en requirements.txt por defecto para no forzar
la instalación de un navegador si no vas a usar este colector; instálalo
con `pip install playwright && playwright install chromium` si lo activas.
"""
import os
from datetime import date

from pipeline.collectors.vacantes.base import JobPosting

SEARCH_URL_TEMPLATE = "https://www.occ.com.mx/empleos/de-{keyword}/"  # TODO: confirmar estructura real de URL

SECTOR_KEYWORDS: dict[str, list[str]] = {
    "31-33": ["produccion-industrial", "manufactura", "operador-de-produccion"],
}


def search(scian_code: str, max_results: int = 30) -> list[JobPosting]:
    if os.environ.get("ENABLE_OCC_SCRAPER", "false").lower() != "true":
        print("occ_mundial.search: deshabilitado (ENABLE_OCC_SCRAPER != true). Ver docs/LEGAL_TOS.md.")
        return []

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright no está instalado. Corre "
            "`pip install playwright && playwright install chromium` "
            "si vas a habilitar este colector."
        ) from exc

    keywords = SECTOR_KEYWORDS.get(scian_code, [])
    if not keywords:
        print(f"No hay keywords configuradas para el sector {scian_code} en occ_mundial.SECTOR_KEYWORDS.")
        return []

    postings: list[JobPosting] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for keyword in keywords:
            url = SEARCH_URL_TEMPLATE.format(keyword=keyword)
            page.goto(url, timeout=30000)
            # TODO: ajustar selectores tras inspeccionar el HTML real de OCC.
            cards = page.query_selector_all("article.card-job")
            for card in cards[:max_results]:
                posting = _parse_card(card)
                if posting:
                    postings.append(posting)
        browser.close()

    seen = set()
    unique = []
    for posting in postings:
        if posting.external_id not in seen:
            seen.add(posting.external_id)
            unique.append(posting)
    return unique


def _parse_card(card) -> JobPosting | None:
    title_el = card.query_selector("h2")
    if title_el is None:
        return None
    link_el = card.query_selector("a")
    href = link_el.get_attribute("href") if link_el else None
    external_id = (href or title_el.inner_text()).rsplit("/", 1)[-1]

    company_el = card.query_selector(".company-name")
    location_el = card.query_selector(".location")
    desc_el = card.query_selector(".job-description")

    return JobPosting(
        external_id=external_id,
        title=title_el.inner_text().strip(),
        company=company_el.inner_text().strip() if company_el else None,
        location=location_el.inner_text().strip() if location_el else None,
        description_raw=desc_el.inner_text().strip() if desc_el else "",
        description_url=href,
        posted_at=date.today(),
    )
