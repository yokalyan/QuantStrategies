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


def realized_volatility(close: pd.Series, lookback: int, periods: int = 252) -> float:
    returns = close.pct_change().dropna().iloc[-lookback:]
    if len(returns) < max(2, lookback // 2):
        return float("nan")
    return float(returns.std(ddof=0) * np.sqrt(periods))


def simple_moving_average(close: pd.Series, period: int) -> float:
    if len(close) < period:
        return float("nan")
    return float(close.iloc[-period:].mean())


def wilder_rsi(close: pd.Series, period: int) -> float:
    if len(close) <= period:
        return float("nan")
    delta = close.diff().dropna()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = gains.iloc[:period].mean()
    avg_loss = losses.iloc[:period].mean()
    for gain, loss in zip(gains.iloc[period:], losses.iloc[period:]):
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + rs)))
