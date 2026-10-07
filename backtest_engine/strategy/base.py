from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd


class MarketDataView:
    def __init__(self, bars: dict[str, pd.DataFrame], current_date: pd.Timestamp):
        self._bars = bars
        self.current_date = current_date
        self._cache: dict[tuple[str, str], pd.Series] = {}

    def history(self, symbol: str, field: str = "close") -> pd.Series:
        key = (symbol, field)
        if key in self._cache:
            return self._cache[key]
        frame = self._bars[symbol]
        if "date" in frame.columns:
            visible = frame[frame["date"] <= self.current_date]
            series = visible.set_index("date")[field]
        else:
            series = frame.loc[: self.current_date, field]
        series.name = symbol
        self._cache[key] = series
        return series

    def symbols(self) -> list[str]:
        return list(self._bars.keys())


@dataclass
class Strategy:
    params: dict

    def target_weights(self, data: MarketDataView, current_weights: dict[str, float]) -> dict[str, float]:
        raise NotImplementedError


_REGISTRY: dict[str, Callable[[dict], Strategy]] = {}


def register_strategy(name: str):
    def wrapper(cls):
        _REGISTRY[name] = cls
        return cls
    return wrapper


def get_strategy(name: str, params: dict) -> Strategy:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown strategy '{name}'. Registered: {sorted(_REGISTRY)}")
    return _REGISTRY[name](params)
