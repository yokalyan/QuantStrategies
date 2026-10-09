import math

from backtest_engine.intraday_orb import _resolve_orb_direction


def test_previous_close_agreement_skips_bullish_opening_range_after_gap_down():
    direction, agreement = _resolve_orb_direction(
        "previous_close_agreement",
        opening_range_direction=1,
        previous_close=85.0,
        or_close=80.50,
    )

    assert direction == 0
    assert agreement is False


def test_previous_close_agreement_skips_bearish_opening_range_after_gap_up():
    direction, agreement = _resolve_orb_direction(
        "previous_close_agreement",
        opening_range_direction=-1,
        previous_close=85.0,
        or_close=86.0,
    )

    assert direction == 0
    assert agreement is False


def test_previous_close_mode_uses_prior_close_to_opening_range_close_direction():
    direction, agreement = _resolve_orb_direction(
        "previous_close",
        opening_range_direction=-1,
        previous_close=85.0,
        or_close=86.0,
    )

    assert direction == 1
    assert agreement is True


def test_opening_range_mode_preserves_existing_behavior_without_prior_close():
    direction, agreement = _resolve_orb_direction(
        "opening_range",
        opening_range_direction=-1,
        previous_close=math.nan,
        or_close=86.0,
    )

    assert direction == -1
    assert agreement is True
