from datetime import date

from pipeline.collectors.vacantes.indeed_manual import _parse_date, parse_postings

_SAMPLE_ITEM = {
    "external_id": "aatw8tryg9zj",
    "title": "Operador de Producción / Surtido y Dispensado de Materia Prima",
    "company": "Reckitt",
    "location": "Ex-Hacienda Coapa, CDMX",
    "description_raw": "Operar líneas de producción, cumplir normas de seguridad e higiene.",
    "description_url": "https://to.indeed.com/aatw8tryg9zj",
    "salary_min": 8000.0,
    "salary_max": 10000.0,
    "posted_at": "2026-07-02",
}


def test_parse_postings_maps_valid_item():
    postings = parse_postings([_SAMPLE_ITEM])
    assert len(postings) == 1
    posting = postings[0]
    assert posting.external_id == "aatw8tryg9zj"
    assert posting.title == _SAMPLE_ITEM["title"]
    assert posting.company == "Reckitt"
    assert posting.description_url == "https://to.indeed.com/aatw8tryg9zj"
    assert posting.salary_min == 8000.0
    assert posting.posted_at == date(2026, 7, 2)


def test_parse_postings_skips_items_without_external_id_or_title():
    postings = parse_postings([{"title": "X"}, {"external_id": "1"}, _SAMPLE_ITEM])
    assert len(postings) == 1
    assert postings[0].external_id == "aatw8tryg9zj"


def test_parse_postings_defaults_missing_optional_fields():
    postings = parse_postings([{"external_id": "1", "title": "Vacante mínima"}])
    posting = postings[0]
    assert posting.company is None
    assert posting.description_raw == ""
    assert posting.salary_min is None
    assert posting.posted_at is None


def test_parse_date_handles_invalid_and_empty_values():
    assert _parse_date(None) is None
    assert _parse_date("") is None
    assert _parse_date("fecha-invalida") is None
    assert _parse_date("2026-07-02") == date(2026, 7, 2)
