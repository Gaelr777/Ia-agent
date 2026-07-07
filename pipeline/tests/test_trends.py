from pipeline.analysis.trends import IndicatorTrend


def _trend(current, previous):
    return IndicatorTrend(
        source="EMIM",
        description="Personal ocupado total",
        current_period="2026-07-01",
        current_value=current,
        previous_value=previous,
    )


def test_delta_abs_computes_difference():
    assert _trend(110, 100).delta_abs == 10


def test_delta_abs_none_when_missing_value():
    assert _trend(None, 100).delta_abs is None
    assert _trend(110, None).delta_abs is None


def test_delta_pct_computes_percentage():
    assert _trend(110, 100).delta_pct == 10.0


def test_delta_pct_none_when_previous_is_zero_or_missing():
    assert _trend(110, 0).delta_pct is None
    assert _trend(110, None).delta_pct is None
