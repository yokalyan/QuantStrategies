from __future__ import annotations

import math

from backtest_engine.indicators import annualized_mean_return, annualized_volatility, momentum_return
from backtest_engine.sizing import bounded_kelly_weights
from backtest_engine.strategy import MarketDataView, Strategy, register_strategy


@register_strategy("qqq_kelly_momentum_leaders")
class QQQKellyMomentumLeaders(Strategy):
    def target_weights(self, data: MarketDataView, current_weights: dict[str, float]) -> dict[str, float]:
        momentum_lookback = int(self.params["momentum_lookback"])
        kelly_lookback = int(self.params["kelly_lookback"])
        volatility_lookback = int(self.params["volatility_lookback"])
        top_n = int(self.params["top_n"])
        scores: dict[str, float] = {}
        for symbol in data.symbols():
            if symbol == self.params.get("benchmark_symbol", "QQQ"):
                continue
            close = data.history(symbol, "close")
            mom = momentum_return(close, momentum_lookback)
            mean = annualized_mean_return(close, kelly_lookback)
            vol = annualized_volatility(close, volatility_lookback)
            if not all(math.isfinite(x) for x in (mom, mean, vol)) or mom <= self.params["min_momentum"]:
                continue
            variance = vol * vol
            if variance <= 0:
                continue
            scores[symbol] = mean / variance
        leaders = dict(sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:top_n])
        return bounded_kelly_weights(
            leaders,
            fraction=float(self.params["kelly_fraction"]),
            max_position_weight=float(self.params["max_position_weight"]),
            max_gross_exposure=float(self.params["max_gross_exposure"]),
        )

