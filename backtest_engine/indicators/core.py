from __future__ import annotations

import numpy as np
import pandas as pd


def momentum_return(close: pd.Series, lookback: int) -> float:
    if len(close) <= lookback:
        return float("nan")
    return float(close.iloc[-1] / close.iloc[-lookback - 1] - 1.0)


def annualized_mean_return(close: pd.Series, lookback: int, periods: int = 252) -> float:
    returns = close.pct_change().dropna().iloc[-lookback:]
    if len(returns) < max(2, lookback // 2):
        return float("nan")
    return float(returns.mean() * periods)


def annualized_volatility(close: pd.Series, lookback: int, periods: int = 252) -> float:
    returns = close.pct_change().dropna().iloc[-lookback:]
    if len(returns) < max(2, lookback // 2):
        return float("nan")
    return float(returns.std(ddof=1) * np.sqrt(periods))

