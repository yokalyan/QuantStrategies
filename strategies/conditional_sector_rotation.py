from __future__ import annotations

import math

from backtest_engine.indicators import simple_moving_average, wilder_rsi
from backtest_engine.strategy import MarketDataView, Strategy, register_strategy


@register_strategy("conditional_sector_rotation")
class ConditionalSectorRotation(Strategy):
    def target_weights(self, data: MarketDataView, current_weights: dict[str, float]) -> dict[str, float]:
        rsi_period = int(self.params.get("rsi_period", 10))
        spy_sma_period = int(self.params.get("spy_sma_period", 200))
        qqq_sma_period = int(self.params.get("qqq_sma_period", 20))
        tqqq_sma_period = int(self.params.get("tqqq_sma_period", 20))

        close = {symbol: data.history(symbol, "close") for symbol in data.symbols()}
        required = ["SPY", "QQQ", "TQQQ", "UVXY", "TECL", "SPXL", "SQQQ", "TECS", "BSV"]
        if any(symbol not in close for symbol in required):
            missing = sorted(set(required) - set(close))
            raise ValueError(f"Conditional sector rotation missing symbols: {missing}")

        price_spy = float(close["SPY"].iloc[-1])
        price_qqq = float(close["QQQ"].iloc[-1])
        price_tqqq = float(close["TQQQ"].iloc[-1])
        rsi = {symbol: wilder_rsi(close[symbol], rsi_period) for symbol in required}
        sma_spy_200 = simple_moving_average(close["SPY"], spy_sma_period)
        sma_qqq_20 = simple_moving_average(close["QQQ"], qqq_sma_period)
        sma_tqqq_20 = simple_moving_average(close["TQQQ"], tqqq_sma_period)
        values = [price_spy, price_qqq, price_tqqq, sma_spy_200, sma_qqq_20, sma_tqqq_20, *rsi.values()]
        if not all(math.isfinite(value) for value in values):
            return current_weights

        target = self._select_target(price_spy, price_qqq, price_tqqq, sma_spy_200, sma_qqq_20, sma_tqqq_20, rsi)
        return {target: 1.0}

    def _select_target(
        self,
        price_spy: float,
        price_qqq: float,
        price_tqqq: float,
        sma_spy_200: float,
        sma_qqq_20: float,
        sma_tqqq_20: float,
        rsi: dict[str, float],
    ) -> str:
        if price_spy > sma_spy_200:
            if rsi["QQQ"] > 81:
                return "UVXY"
            if rsi["SPY"] > 80:
                return "UVXY"
            return "TQQQ"

        if rsi["TQQQ"] < 30:
            return "TECL"
        if rsi["SPY"] < 30:
            return "SPXL"
        if rsi["UVXY"] > 74:
            if rsi["UVXY"] > 84:
                if price_qqq > sma_qqq_20:
                    if rsi["SQQQ"] < 31:
                        return "TECS"
                    return "TECL"
                return self._max_rsi_asset(["TECS", "BSV"], rsi)
            return "UVXY"

        if price_tqqq > sma_tqqq_20:
            if rsi["SQQQ"] < 34:
                return "TECS"
            return "TECL"
        return self._max_rsi_asset(["TECS", "BSV"], rsi)

    @staticmethod
    def _max_rsi_asset(symbols: list[str], rsi: dict[str, float]) -> str:
        return max(symbols, key=lambda symbol: (rsi[symbol], symbol))
