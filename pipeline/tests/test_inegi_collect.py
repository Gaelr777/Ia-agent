from pipeline.collectors.inegi.collect import _series_for_sector

_CONFIG = {
    "national": [
        {"indicator_id": "444612", "source": "ENOE", "description": "Tasa de desocupación"},
    ],
    "by_sector": {
        "31-33": [
            {"indicator_id": "702844", "source": "EMIM", "description": "Personal ocupado total"},
            {"indicator_id": "TODO", "source": "EMIM", "description": "Placeholder sin llenar"},
        ]
    },
}


def test_series_for_sector_combines_national_and_sector_entries():
    entries = _series_for_sector(_CONFIG, "31-33")
    indicator_ids = {e["indicator_id"] for e in entries}
    assert indicator_ids == {"444612", "702844"}


def test_series_for_sector_filters_out_todo_placeholders():
    entries = _series_for_sector(_CONFIG, "31-33")
    assert all(e["indicator_id"] != "TODO" for e in entries)


def test_series_for_sector_returns_only_national_for_unconfigured_sector():
    entries = _series_for_sector(_CONFIG, "54")
    assert {e["indicator_id"] for e in entries} == {"444612"}
