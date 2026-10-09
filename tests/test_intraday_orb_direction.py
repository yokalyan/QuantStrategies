import math

import pandas as pd

from backtest_engine.intraday_orb import _add_intraday_anchors, _intraday_filter_passes, _resolve_orb_direction


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


def test_entry_vwap_filter_requires_price_on_directional_side():
    long_bar = pd.Series({"close": 101.0, "vwap": 100.0, "twap": 99.0})
    short_bar = pd.Series({"close": 99.0, "vwap": 100.0, "twap": 101.0})

    assert _intraday_filter_passes(1, long_bar, "entry_vwap") is True
    assert _intraday_filter_passes(-1, short_bar, "entry_vwap") is True
    assert _intraday_filter_passes(1, short_bar, "entry_vwap") is False
    assert _intraday_filter_passes(-1, long_bar, "entry_vwap") is False


def test_intraday_anchors_compute_vwap_and_twap():
    frame = pd.DataFrame(
        {
            "high": [10.0, 12.0],
            "low": [9.0, 10.0],
            "close": [9.5, 11.0],
            "volume": [100.0, 300.0],
        }
    )

    out = _add_intraday_anchors(frame)

    assert round(float(out.iloc[-1]["twap"]), 4) == 10.25
    assert round(float(out.iloc[-1]["vwap"]), 4) == 10.625
