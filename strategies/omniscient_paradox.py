from __future__ import annotations

import math

from backtest_engine.indicators import momentum_return, realized_volatility, simple_moving_average, wilder_rsi
from backtest_engine.strategy import MarketDataView, Strategy, register_strategy


@register_strategy("omniscient_paradox")
class OmniscientParadox(Strategy):
    def __init__(self, params: dict):
        super().__init__(params)
        self.current_holding: str | None = None

    def target_weights(self, data: MarketDataView, current_weights: dict[str, float]) -> dict[str, float]:
        candidates = list(self.params.get("candidates", ["SOXL", "TECL", "TQQQ", "FAS", "ERX", "UUP", "TMF"]))
        safe = self.params.get("safe_symbol", "BIL")
        spy_symbol = self.params.get("spy_symbol", "SPY")
        scores = self._scores(data, candidates)
        if not scores:
            return current_weights

        best_asset, best_score = max(scores.items(), key=lambda item: (item[1], item[0]))
        target_asset = self.current_holding
        confidence_threshold = float(self.params.get("confidence_threshold", 0.10))
        if self.current_holding is None:
            target_asset = best_asset if best_score > 0 else safe
        else:
            current_score = scores.get(self.current_holding, -999.0)
            if self.current_holding == safe:
                if best_score > float(self.params.get("safe_exit_score", 0.02)):
                    target_asset = best_asset
            elif best_score > current_score * (1.0 + confidence_threshold):
                target_asset = best_asset
            elif current_score < float(self.params.get("cash_trigger_score", -0.02)):
                target_asset = safe

        if not self._spy_trending(data, spy_symbol) and target_asset != safe:
            uup = self.params.get("dollar_symbol", "UUP")
            uup_score = scores.get(uup, -999.0)
            target_score = scores.get(target_asset, -999.0)
            if uup_score > 0 and uup_score > target_score:
                target_asset = uup
            elif target_score < 0:
                target_asset = safe

        target_weight = self._target_weight(data, target_asset, safe)
        self.current_holding = target_asset
        if target_asset == safe:
            return {safe: 1.0}
        if not target_asset or target_weight <= 0:
            return {}
        weights = {target_asset: target_weight}
        remainder = 1.0 - target_weight
        if remainder > float(self.params.get("safe_remainder_threshold", 0.10)):
            weights[safe] = remainder
        return weights

    def _scores(self, data: MarketDataView, candidates: list[str]) -> dict[str, float]:
        scores: dict[str, float] = {}
        for symbol in candidates:
            close = data.history(symbol, "close")
            fast = momentum_return(close, int(self.params.get("roc_fast", 9)))
            med = momentum_return(close, int(self.params.get("roc_med", 21)))
            slow = momentum_return(close, int(self.params.get("roc_slow", 63)))
            vol = realized_volatility(close, int(self.params.get("vol_lookback", 21)))
            rsi = wilder_rsi(close, int(self.params.get("rsi_period", 14)))
            sma = simple_moving_average(close, int(self.params.get("sma_period", 50)))
            price = float(close.iloc[-1]) if len(close) else float("nan")
            if not all(math.isfinite(value) for value in [fast, med, slow, vol, rsi, sma, price]):
                continue
            if vol == 0:
                vol = 1.0
            weighted_momentum = (
                fast * float(self.params.get("fast_weight", 0.5))
                + med * float(self.params.get("med_weight", 0.3))
                + slow * float(self.params.get("slow_weight", 0.2))
            )
            risk_adjusted = weighted_momentum / vol
            trend_score = 1.0 if price > sma else float(self.params.get("below_sma_discount", 0.5))
            rsi_penalty = 1.0
            if rsi > float(self.params.get("rsi_overbought", 85)) or rsi < float(self.params.get("rsi_oversold", 30)):
                rsi_penalty = float(self.params.get("rsi_penalty", 0.9))
            scores[symbol] = risk_adjusted * trend_score * rsi_penalty
        return scores

    def _spy_trending(self, data: MarketDataView, spy_symbol: str) -> bool:
        close = data.history(spy_symbol, "close")
        sma = simple_moving_average(close, int(self.params.get("spy_sma_period", 200)))
        if not math.isfinite(sma) or close.empty:
            return False
        return float(close.iloc[-1]) > sma

    def _target_weight(self, data: MarketDataView, target_asset: str | None, safe: str) -> float:
        if target_asset is None:
            return 0.0
        if target_asset == safe:
            return 1.0
        close = data.history(target_asset, "close")
        vol = realized_volatility(close, int(self.params.get("lookback_vol", 20)))
        if not math.isfinite(vol) or vol <= 0:
            return 1.0
        return min(1.0, float(self.params.get("target_vol", 0.80)) / vol)
