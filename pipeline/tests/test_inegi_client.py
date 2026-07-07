from pipeline.collectors.inegi.client import (
    _build_indicator_url,
    _parse_time_period,
    parse_observations,
)


def test_build_indicator_url_joins_multiple_indicators_with_comma():
    url = _build_indicator_url(
        ["702844", "704728"], area_geografica="00", idioma="es", recientes=False, token="TOKEN123"
    )
    assert "702844,704728" in url
    assert url.startswith("https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/")
    assert "/es/00/false/BISE/2.0/TOKEN123?type=json" in url


def test_build_indicator_url_recientes_true():
    url = _build_indicator_url(["444612"], area_geografica="00", idioma="es", recientes=True, token="TOKEN")
    assert "/true/BISE/2.0/TOKEN" in url


def test_parse_time_period_monthly():
    assert _parse_time_period("2024/01") == "2024-01-01"
    assert _parse_time_period("2026/12") == "2026-12-01"


def test_parse_time_period_invalid_returns_none():
    assert _parse_time_period("") is None
    assert _parse_time_period("no-slash") is None
    assert _parse_time_period("abcd/ef") is None


def test_parse_observations_flattens_series_and_skips_missing_values():
    raw = {
        "Series": [
            {
                "INDICADOR": "702844",
                "OBSERVATIONS": [
                    {"TIME_PERIOD": "2026/01", "OBS_VALUE": "4655127"},
                    {"TIME_PERIOD": "2026/02", "OBS_VALUE": "N/E"},
                    {"TIME_PERIOD": "2026/03", "OBS_VALUE": ""},
                    {"TIME_PERIOD": "", "OBS_VALUE": "999"},
                ],
            }
        ]
    }
    rows = parse_observations(raw)
    assert rows == [
        {"indicator_id": "702844", "period": "2026-01-01", "value": 4655127.0}
    ]


def test_parse_observations_handles_multiple_series():
    raw = {
        "Series": [
            {"INDICADOR": "A", "OBSERVATIONS": [{"TIME_PERIOD": "2026/01", "OBS_VALUE": "1"}]},
            {"INDICADOR": "B", "OBSERVATIONS": [{"TIME_PERIOD": "2026/01", "OBS_VALUE": "2"}]},
        ]
    }
    rows = parse_observations(raw)
    assert {r["indicator_id"] for r in rows} == {"A", "B"}
