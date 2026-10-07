from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


REQUIRED_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def validate_bars(symbol: str, bars: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in bars.columns]
    if missing:
        raise ValueError(f"{symbol} missing columns: {missing}")
    if bars["date"].duplicated().any():
        raise ValueError(f"{symbol} has duplicate dates")
    price_cols = ["open", "high", "low", "close"]
    if (bars[price_cols] <= 0).any().any():
        raise ValueError(f"{symbol} has non-positive prices")
    if not bars["date"].is_monotonic_increasing:
        raise ValueError(f"{symbol} dates are not sorted")


@dataclass
class DataPortal:
    cache_dir: Path

    def load(self, symbols: Iterable[str], start: str | None = None, end: str | None = None) -> dict[str, pd.DataFrame]:
        result: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            path = self.cache_dir / f"{symbol}.parquet"
            if not path.exists():
                raise FileNotFoundError(f"Missing cache file for {symbol}: {path}")
            bars = pd.read_parquet(path)
            bars["date"] = pd.to_datetime(bars["date"])
            bars = bars.sort_values("date").reset_index(drop=True)
            if start:
                bars = bars[bars["date"] >= pd.Timestamp(start)]
            if end:
                bars = bars[bars["date"] <= pd.Timestamp(end)]
            bars = bars.reset_index(drop=True)
            validate_bars(symbol, bars)
            result[symbol] = bars
        return result


@dataclass
class YFinanceProvider:
    cache_dir: Path

    def fetch(self, symbols: list[str], start: str, end: str) -> None:
        import yfinance as yf

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        raw = yf.download(symbols, start=start, end=end, auto_adjust=True, progress=False, group_by="ticker", threads=False)
        if raw.empty:
            raise RuntimeError("yfinance returned no data")
        for symbol in symbols:
            if isinstance(raw.columns, pd.MultiIndex):
                if symbol not in raw.columns.get_level_values(0):
                    raise RuntimeError(f"yfinance result missing {symbol}")
                frame = raw[symbol]
            else:
                frame = raw
            frame = frame.reset_index()
            rename = {c: c.lower() for c in frame.columns}
            frame = frame.rename(columns=rename)
            if "date" not in frame.columns:
                frame = frame.rename(columns={"datetime": "date"})
            frame = frame[["date", "open", "high", "low", "close", "volume"]].dropna()
            frame["date"] = pd.to_datetime(frame["date"]).dt.tz_localize(None)
            frame = frame.sort_values("date").reset_index(drop=True)
            validate_bars(symbol, frame)
            frame.to_parquet(self.cache_dir / f"{symbol}.parquet", index=False)

