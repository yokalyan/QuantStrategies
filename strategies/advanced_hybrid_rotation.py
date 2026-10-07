from __future__ import annotations

import numpy as np

from backtest_engine.indicators import momentum_return, realized_volatility, simple_moving_average, wilder_rsi
from backtest_engine.strategy import MarketDataView, Strategy, register_strategy


@register_strategy("advanced_hybrid_rotation")
class AdvancedHybridRotation(Strategy):
    def __init__(self, params: dict):
        super().__init__(params)
        self.days_since_rebalance = 0
        self.core_targets: dict[str, float] = {}
        self.base_core = float(params.get("base_allocation_core", 0.60))
        self.base_sat = float(params.get("base_allocation_sat", 0.40))

    def target_weights(self, data: MarketDataView, current_weights: dict[str, float]) -> dict[str, float]:
        self._manage_volatility(data)
        satellite = self._satellite_targets(data)
        self.days_since_rebalance += 1
        if self.days_since_rebalance >= int(self.params.get("rebalance_days", 5)) or not self.core_targets:
            self.core_targets = self._core_targets(data)
            self.days_since_rebalance = 0
        combined = dict(self.core_targets)
        for symbol, weight in satellite.items():
            combined[symbol] = combined.get(symbol, 0.0) + weight
        return {symbol: weight for symbol, weight in combined.items() if weight > 0}

    def _manage_volatility(self, data: MarketDataView) -> None:
        vol = realized_volatility(data.history("SPY", "close"), int(self.params.get("vol_lookback", 20)))
        if vol <= 0 or np.isnan(vol):
            return
        target_exposure = min(float(self.params.get("leverage_cap", 1.0)), float(self.params.get("vol_target", 0.15)) / vol)
        self.base_core = float(self.params.get("base_allocation_core", 0.60)) * min(1.0, target_exposure)
        self.base_sat = float(self.params.get("base_allocation_sat", 0.40)) * target_exposure

    def _core_targets(self, data: MarketDataView) -> dict[str, float]:
        candidates: list[tuple[float, str]] = []
        for symbol in self.params["core_tickers"]:
            close = data.history(symbol, "close")
            if len(close) <= max(int(self.params.get("core_lookback", 60)), int(self.params.get("core_ma_period", 200))):
                continue
            if symbol == "BIL":
                candidates.append((0.0, symbol))
                continue
            price = float(close.iloc[-1])
            sma = simple_moving_average(close, int(self.params.get("core_ma_period", 200)))
            roc = momentum_return(close, int(self.params.get("core_lookback", 60)))
            if price > sma and roc > 0:
                candidates.append((roc, symbol))
        selected = [symbol for _, symbol in sorted(candidates, key=lambda item: (-item[0], item[1]))[: int(self.params.get("core_holdings", 5))]]
        if not selected:
            selected = ["BIL"]
        weight = self.base_core / len(selected)
        return {symbol: weight for symbol in selected}

    def _satellite_targets(self, data: MarketDataView) -> dict[str, float]:
        rsi_period = int(self.params.get("sat_rsi_period", 10))
        price_spy = float(data.history("SPY", "close").iloc[-1])
        sma_spy_200 = simple_moving_average(data.history("SPY", "close"), 200)
        rsi_tqqq = wilder_rsi(data.history("TQQQ", "close"), rsi_period)
        target = None
        if price_spy > sma_spy_200:
            if wilder_rsi(data.history("QQQ", "close"), rsi_period) > 81 or wilder_rsi(data.history("SPY", "close"), rsi_period) > 80:
                target = "UVXY"
            elif rsi_tqqq > 85:
                target = "BSV"
            else:
                target = "TQQQ"
        else:
            if rsi_tqqq < 30:
                target = "TECL"
            elif wilder_rsi(data.history("SPY", "close"), rsi_period) < 30:
                target = "SPXL"
            elif wilder_rsi(data.history("UVXY", "close"), rsi_period) > 74:
                target = "UVXY"
            elif float(data.history("TQQQ", "close").iloc[-1]) > simple_moving_average(data.history("TQQQ", "close"), 20):
                target = "TECS" if wilder_rsi(data.history("SQQQ", "close"), rsi_period) < 34 else "TECL"
            else:
                target = "BSV"
        return {target: self.base_sat} if target else {}
