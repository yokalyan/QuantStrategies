from __future__ import annotations

import pandas as pd

from backtest_engine.indicators import momentum_return, simple_moving_average, wilder_rsi
from backtest_engine.strategy import MarketDataView, Strategy, register_strategy


@register_strategy("quad_ensemble")
class QuadEnsemble(Strategy):
    QUARTER = 0.25
    SVIX_LIVE = pd.Timestamp("2022-03-30")
    UVIX_LIVE = pd.Timestamp("2022-03-30")

    def target_weights(self, data: MarketDataView, current_weights: dict[str, float]) -> dict[str, float]:
        sleeves = [self._t10(data), self._t11(data), self._s2(data), self._s3(data)]
        combined: dict[str, float] = {}
        for sleeve in sleeves:
            for symbol, weight in sleeve.items():
                combined[symbol] = combined.get(symbol, 0.0) + weight
        return combined

    def _rsi(self, data: MarketDataView, symbol: str, period: int) -> float:
        return wilder_rsi(data.history(symbol, "close"), period)

    def _price(self, data: MarketDataView, symbol: str) -> float:
        return float(data.history(symbol, "close").iloc[-1])

    def _sma(self, data: MarketDataView, symbol: str, period: int) -> float:
        return simple_moving_average(data.history(symbol, "close"), period)

    def _available(self, data: MarketDataView, symbol: str, min_bars: int = 1) -> bool:
        try:
            return len(data.history(symbol, "close").dropna()) >= min_bars
        except KeyError:
            return False

    def _t10(self, data: MarketDataView) -> dict[str, float]:
        symbols = ["QQQE", "VTV", "VOX", "TECL", "VOOG", "VOOV", "XLP", "TQQQ", "XLY", "FAS", "SPY", "SOXL", "SPXL", "LABU", "XLK", "KMLM"]
        r = {s: self._rsi(data, s, 10) for s in symbols if self._available(data, s, 11)}
        required = ["QQQE", "VTV", "VOX", "TECL", "VOOG", "VOOV", "XLP", "TQQQ", "XLY", "FAS", "SPY", "SOXL", "SPXL", "XLK"]
        if any(s not in r or pd.isna(r[s]) for s in required):
            return {}
        if (
            r["QQQE"] > 79 or r["VTV"] > 79 or r["VOX"] > 79 or r["TECL"] > 79 or r["VOOG"] > 79
            or r["VOOV"] > 79 or r["XLP"] > 75 or r["TQQQ"] > 79 or r["XLY"] > 80
            or r["FAS"] > 80 or r["SPY"] > 80
        ):
            return {"UVXY": self.QUARTER}
        if r["TQQQ"] < 30:
            return {"TECL": self.QUARTER}
        if r["SOXL"] < 30:
            return {"SOXL": self.QUARTER}
        if r["SPXL"] < 30:
            return {"SPXL": self.QUARTER}
        if "LABU" in r and r["LABU"] < 25:
            return {"LABU": self.QUARTER}
        short_vol = "SVIX" if data.current_date >= self.SVIX_LIVE and self._available(data, "SVIX") else "SVXY"
        xlk_wins = "KMLM" not in r or r["XLK"] > r["KMLM"]
        if xlk_wins:
            return {"TECL": self.QUARTER / 3, "SOXL": self.QUARTER / 3, short_vol: self.QUARTER / 3}
        return {"SQQQ": self.QUARTER * 0.5, "TLT": self.QUARTER * 0.5}

    def _t11(self, data: MarketDataView) -> dict[str, float]:
        r10_symbols = ["SPY", "IOO", "TQQQ", "VTV", "XLF", "XLK", "KMLM", "PSQ", "BND", "QQQ", "IEF"]
        r10 = {s: self._rsi(data, s, 10) for s in r10_symbols if self._available(data, s, 11)}
        r20 = {s: self._rsi(data, s, 20) for s in ["TLT", "PSQ", "AGG"] if self._available(data, s, 21)}
        core = ["SPY", "IOO", "TQQQ", "VTV", "XLF", "XLK", "PSQ", "BND", "QQQ", "IEF"]
        if any(s not in r10 or pd.isna(r10[s]) for s in core) or len(r20) < 3:
            return {}
        if any(r10[s] > 79 for s in ["SPY", "IOO", "TQQQ", "VTV", "XLF"]):
            if any(r10[s] > 81 for s in ["SPY", "IOO", "TQQQ", "VTV", "XLF"]):
                return {"UVXY": self.QUARTER}
            return {"UVXY": self.QUARTER / 3, "BIL": self.QUARTER / 3, "BTAL": self.QUARTER / 3}
        if r10["TQQQ"] < 30:
            return {"TQQQ": self.QUARTER}
        if r10["SPY"] < 30:
            return {"SPXL": self.QUARTER}

        spy_px = self._price(data, "SPY")
        spy_sma = self._sma(data, "SPY", 200)
        tqqq_px = self._price(data, "TQQQ")
        tqqq_sma = self._sma(data, "TQQQ", 20)
        if spy_px > spy_sma:
            kmlm_ready = "KMLM" in r10 and self._available(data, "KMLM", 20)
            if (not kmlm_ready) or r10["XLK"] > r10["KMLM"] or self._price(data, "KMLM") < self._sma(data, "KMLM", 20):
                return {"TECL": self.QUARTER / 3, "SOXL": self.QUARTER / 3, "TQQQ": self.QUARTER / 3}
            return {"TECS": self.QUARTER / 3, "SOXS": self.QUARTER / 3, "SQQQ": self.QUARTER / 3}

        bond_baller = self._t11_bond_baller(data, r10, r20, tqqq_px, tqqq_sma)
        feaver_bear = self._t11_feaver_bear(data, r10, r20, tqqq_px, tqqq_sma)
        out: dict[str, float] = {}
        out[bond_baller] = out.get(bond_baller, 0.0) + self.QUARTER * 0.5
        out[feaver_bear] = out.get(feaver_bear, 0.0) + self.QUARTER * 0.5
        return out

    def _t11_bond_baller(self, data: MarketDataView, r10: dict[str, float], r20: dict[str, float], tqqq_px: float, tqqq_sma: float) -> str:
        if r20["TLT"] > r20["PSQ"]:
            return "QQQ"
        if tqqq_px > tqqq_sma:
            if r10["PSQ"] < 35:
                return "PSQ"
            if r20["AGG"] > self._rsi(data, "SH", 60):
                return "TQQQ"
            return "PSQ"
        if r10["IEF"] > r20["PSQ"]:
            return "PSQ"
        return "SQQQ"

    def _t11_feaver_bear(self, data: MarketDataView, r10: dict[str, float], r20: dict[str, float], tqqq_px: float, tqqq_sma: float) -> str:
        qqq_60d = momentum_return(data.history("QQQ", "close"), 60) * 100
        if qqq_60d < -12:
            return "QLD" if r10["BND"] > r10["QQQ"] else "BTAL"
        return self._t11_bond_baller(data, r10, r20, tqqq_px, tqqq_sma)

    def _s2(self, data: MarketDataView) -> dict[str, float]:
        required = ["TQQQ", "SOXL", "SQQQ", "BSV"]
        if any(not self._available(data, s, 201 if s == "TQQQ" else 11) for s in required):
            return {}
        tqqq_price = self._price(data, "TQQQ")
        if tqqq_price > self._sma(data, "TQQQ", 200):
            return {"UVXY" if self._rsi(data, "TQQQ", 10) > 79 else "TQQQ": self.QUARTER}
        if self._rsi(data, "TQQQ", 10) < 31:
            return {"TECL": self.QUARTER}
        if self._rsi(data, "SOXL", 10) < 30:
            return {"SOXL": self.QUARTER}
        if tqqq_price < self._sma(data, "TQQQ", 20):
            return {"SQQQ" if self._rsi(data, "SQQQ", 10) > self._rsi(data, "BSV", 10) else "BSV": self.QUARTER}
        return {"TQQQ": self.QUARTER}

    def _s3(self, data: MarketDataView) -> dict[str, float]:
        assets = ["SPY", "QQQ", "SMH", "SOXL"]
        if any(not self._available(data, s, 203) for s in assets):
            return {}
        bull = sum(1 for s in assets if self._price(data, s) > self._sma(data, s, 202)) >= 3
        overbought = any(self._rsi(data, s, 15) > 72 for s in assets)
        if bull:
            if overbought:
                vol = "UVIX" if data.current_date >= self.UVIX_LIVE and self._available(data, "UVIX") else "UVXY"
                return {vol: self.QUARTER}
            return {"TQQQ": self.QUARTER * 0.5, "SOXL": self.QUARTER * 0.5}
        if self._rsi(data, "QQQ", 8) < 29 or self._rsi(data, "SMH", 8) < 31:
            return {"SOXL": self.QUARTER}
        return {}
