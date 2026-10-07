from __future__ import annotations

from pathlib import Path

import pandas as pd

from backtest_engine.analytics import compute_metrics
from backtest_engine.data.providers import validate_bars
from backtest_engine.execution import CostModel
from backtest_engine.indicators import realized_volatility, simple_moving_average, wilder_rsi
from backtest_engine.portfolio import Portfolio
from backtest_engine.strategy import MarketDataView, Strategy
from backtest_engine.validation import scan_for_forbidden_terms


def bars(prices):
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=len(prices), freq="B"),
            "open": prices,
            "high": prices,
            "low": prices,
            "close": prices,
            "volume": [1000] * len(prices),
        }
    )


def test_accounting_identity_after_fill():
    p = Portfolio(1000)
    p.apply_fill(pd.Timestamp("2024-01-02"), "AAA", 5, 100, CostModel(slippage_bps=0, min_commission=0), "test")
    assert p.cash == 500 - 0.025
    assert abs(p.value({"AAA": 100}) - 999.975) < 1e-9


def test_data_view_blocks_future_bars():
    data = {"AAA": bars([10, 11, 12, 13])}
    view = MarketDataView(data, pd.Timestamp("2024-01-03"))
    hist = view.history("AAA")
    assert list(hist.values) == [10, 11, 12]


def test_validate_rejects_bad_prices():
    bad = bars([10, 0, 12])
    try:
        validate_bars("AAA", bad)
    except ValueError as exc:
        assert "non-positive" in str(exc)
    else:
        raise AssertionError("expected validation failure")


def test_metrics_known_drawdown():
    eq = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3), "equity": [100, 120, 90]})
    metrics = compute_metrics(eq)
    assert round(metrics["total_return"], 6) == -0.1
    assert round(metrics["max_drawdown"], 6) == -0.25


def test_static_independence_scan(tmp_path: Path):
    (tmp_path / "ok.py").write_text("import pandas as pd\n", encoding="utf-8")
    assert scan_for_forbidden_terms(tmp_path) == []


def test_target_rebalance_whole_shares():
    p = Portfolio(1000)
    p.rebalance_to_targets(
        pd.Timestamp("2024-01-02"),
        {"AAA": 50, "BBB": 100},
        {"AAA": 0.5, "BBB": 0.5},
        CostModel(commission_per_share=0, slippage_bps=0, min_commission=0),
    )
    assert p.positions == {"AAA": 10, "BBB": 5}


def test_simple_moving_average():
    assert simple_moving_average(pd.Series([1, 2, 3, 4]), 3) == 3.0


def test_wilder_rsi_bounds():
    value = wilder_rsi(pd.Series([1, 2, 3, 2, 4, 5, 4, 6, 7, 8, 7, 9]), 5)
    assert 0 <= value <= 100


def test_realized_volatility_positive_for_moving_series():
    value = realized_volatility(pd.Series([100, 101, 99, 103, 102, 105]), 5)
    assert value > 0


def test_fred_like_factor_bars_validate():
    factor = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3),
            "open": [1.0, -0.1, 1.2],
            "high": [1.0, -0.1, 1.2],
            "low": [1.0, -0.1, 1.2],
            "close": [1.0, -0.1, 1.2],
            "volume": [0, 0, 0],
        }
    )
    validate_bars("T10Y3M", factor, require_positive_prices=False)


def test_portfolio_supports_short_target():
    p = Portfolio(1000)
    p.rebalance_to_targets(
        pd.Timestamp("2024-01-02"),
        {"AAA": 50},
        {"AAA": -0.5},
        CostModel(commission_per_share=0, slippage_bps=0, min_commission=0),
    )
    assert p.positions == {"AAA": -10}
    assert abs(p.value({"AAA": 50}) - 1000) < 1e-9
