from __future__ import annotations

import numpy as np
import pandas as pd


def max_drawdown(equity: pd.Series) -> tuple[float, int]:
    peak = equity.cummax()
    dd = equity / peak - 1.0
    min_dd = float(dd.min())
    underwater = dd < 0
    duration = 0
    longest = 0
    for val in underwater:
        duration = duration + 1 if val else 0
        longest = max(longest, duration)
    return min_dd, longest


def compute_metrics(equity: pd.DataFrame, benchmark: pd.DataFrame | None = None, trades: int = 0, costs: float = 0.0) -> dict[str, float]:
    curve = equity.set_index("date")["equity"].astype(float)
    daily = curve.pct_change().dropna()
    years = max((curve.index[-1] - curve.index[0]).days / 365.25, 1e-9)
    total_return = curve.iloc[-1] / curve.iloc[0] - 1.0
    cagr = (curve.iloc[-1] / curve.iloc[0]) ** (1.0 / years) - 1.0
    vol = daily.std(ddof=1) * np.sqrt(252) if len(daily) > 1 else 0.0
    sharpe = daily.mean() / daily.std(ddof=1) * np.sqrt(252) if len(daily) > 1 and daily.std(ddof=1) > 0 else 0.0
    downside = daily[daily < 0].std(ddof=1)
    sortino = daily.mean() / downside * np.sqrt(252) if downside and downside > 0 else 0.0
    mdd, dd_duration = max_drawdown(curve)
    calmar = cagr / abs(mdd) if mdd < 0 else 0.0
    out = {
        "total_return": float(total_return),
        "cagr": float(cagr),
        "annual_volatility": float(vol),
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "calmar": float(calmar),
        "max_drawdown": float(mdd),
        "max_drawdown_duration_days": float(dd_duration),
        "best_day": float(daily.max()) if len(daily) else 0.0,
        "worst_day": float(daily.min()) if len(daily) else 0.0,
        "number_of_trades": float(trades),
        "total_costs": float(costs),
    }
    if benchmark is not None:
        bench = benchmark.set_index("date")["equity"].astype(float).pct_change().dropna()
        aligned = pd.concat([daily.rename("strategy"), bench.rename("benchmark")], axis=1).dropna()
        if len(aligned) > 2 and aligned["benchmark"].var() > 0:
            beta = aligned.cov().loc["strategy", "benchmark"] / aligned["benchmark"].var()
            alpha = (aligned["strategy"].mean() - beta * aligned["benchmark"].mean()) * 252
            corr = aligned.corr().loc["strategy", "benchmark"]
            out.update({"beta": float(beta), "alpha": float(alpha), "correlation": float(corr)})
    return out

