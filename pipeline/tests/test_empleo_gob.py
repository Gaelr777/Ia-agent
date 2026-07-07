from datetime import date

from pipeline.collectors.vacantes.empleo_gob import (
    _location,
    _parse_item,
    _parse_posted_at,
    _salary,
)

_SAMPLE_ITEM = {
    "id": 21172468,
    "fechaPublicacion": "2026-07-06T00:00:00.000+00:00",
    "salarioOfrecido": 9583.0,
    "salarioOfrecidoMaximo": 0.0,
    "tituloOferta": "AYUDANTE GENERAL",
    "descripcion": "Carga y descarga\nAbastecer bandas de manufactura",
    "ciudad": None,
    "municipio": "Azcapotzalco",
    "entidad": "Ciudad de México",
    "colonia": "El Jagüey",
    "nombreEmpresa": "BIO TECNICA",
}


def test_parse_item_maps_real_api_fields():
    posting = _parse_item(_SAMPLE_ITEM)
    assert posting.external_id == "21172468"
    assert posting.title == "AYUDANTE GENERAL"
    assert posting.company == "BIO TECNICA"
    assert posting.location == "Azcapotzalco, Ciudad de México"
    assert posting.salary_min == 9583.0
    assert posting.salary_max is None
    assert posting.posted_at == date(2026, 7, 6)


def test_parse_item_returns_none_without_id_or_title():
    assert _parse_item({"tituloOferta": "X"}) is None
    assert _parse_item({"id": 1}) is None


def test_location_handles_missing_municipio():
    assert _location({"municipio": None, "entidad": "Ciudad de México"}) == "Ciudad de México"
    assert _location({"municipio": None, "entidad": None}) is None


def test_salary_treats_zero_as_not_specified():
    assert _salary(0.0) is None
    assert _salary(None) is None
    assert _salary(9583.0) == 9583.0


def test_parse_posted_at_parses_iso_format():
    assert _parse_posted_at("2026-07-06T00:00:00.000+00:00") == date(2026, 7, 6)
    assert _parse_posted_at(None) is None
