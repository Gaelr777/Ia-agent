from pipeline.cv_classifier import sector_taxonomy


def test_load_sectors_returns_20_scian_sectors():
    sectors = sector_taxonomy.load_sectors()
    assert len(sectors) == 20
    assert all({"code", "name"} <= set(s) for s in sectors)


def test_valid_codes_includes_manufacturing_pilot_sector():
    assert "31-33" in sector_taxonomy.valid_codes()


def test_valid_codes_has_no_duplicates():
    codes = [s["code"] for s in sector_taxonomy.load_sectors()]
    assert len(codes) == len(set(codes))


def test_as_prompt_catalog_includes_every_code():
    catalog = sector_taxonomy.as_prompt_catalog()
    for code in sector_taxonomy.valid_codes():
        assert code in catalog
