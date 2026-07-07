from datetime import date

from pipeline.analysis.generate_report import _parse_period, render_summary_md


def test_parse_period_parses_year_and_month():
    assert _parse_period("2026-07") == date(2026, 7, 1)


def test_render_summary_md_includes_sector_and_period():
    report = {
        "sector": "31-33",
        "period": "2026-07-01",
        "inegi_indicators": [
            {
                "source": "EMIM",
                "description": "Personal ocupado total",
                "current_value": 4655127,
                "delta_pct": 1.234,
            },
            {
                "source": "IGAE",
                "description": "IGAE variación mensual",
                "current_value": 100.5,
                "delta_pct": None,
            },
        ],
        "top_hard_skills": [{"skill": "Python", "count": 12}],
        "top_soft_skills": [{"skill": "Trabajo en equipo", "count": 8}],
        "hard_skills_month_over_month": {"rising": [("Python", 4)], "falling": []},
    }

    summary = render_summary_md(report)

    assert "sector 31-33" in summary
    assert "2026-07-01" in summary
    assert "Personal ocupado total: 4655127 (+1.2% vs. mes anterior)" in summary
    assert "IGAE variación mensual: 100.5 (s/d vs. mes anterior)" in summary
    assert "Python (12 vacantes)" in summary
    assert "Trabajo en equipo (8 vacantes)" in summary
    assert "Python: +4" in summary


def test_render_summary_md_skips_rising_section_when_no_increases():
    report = {
        "sector": "31-33",
        "period": "2026-07-01",
        "inegi_indicators": [],
        "top_hard_skills": [],
        "top_soft_skills": [],
        "hard_skills_month_over_month": {"rising": [("Python", -2)], "falling": []},
    }
    summary = render_summary_md(report)
    assert "en ascenso" not in summary
