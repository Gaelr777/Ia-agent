from pipeline.analysis.skills_extraction import _normalize


def test_normalize_lowercases_and_strips():
    assert _normalize("  Excel Avanzado  ") == "excel avanzado"


def test_normalize_collapses_internal_whitespace():
    assert _normalize("Trabajo   en\nequipo") == "trabajo en equipo"


def test_normalize_treats_variants_as_equal():
    assert _normalize("Python ") == _normalize(" python")
