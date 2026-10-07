from __future__ import annotations

import math

from backtest_engine.indicators import simple_rsi
from backtest_engine.strategy import MarketDataView, Strategy, register_strategy


@register_strategy("tqqq_rsi_mean_reversion")
class TQQQRSIMeanReversion(Strategy):
    def target_weights(self, data: MarketDataView, current_weights: dict[str, float]) -> dict[str, float]:
        offensive = self.params.get("offensive_symbol", "TQQQ")
        defensive = self.params.get("defensive_symbol", "UVXY")
        period = int(self.params.get("rsi_period", 10))
        threshold = float(self.params.get("rsi_threshold", 79.0))
        rsi_value = simple_rsi(data.history(offensive, "close"), period)
        if not math.isfinite(rsi_value):
            return current_weights
        return {defensive if rsi_value > threshold else offensive: 1.0}
