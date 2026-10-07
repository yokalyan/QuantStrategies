from __future__ import annotations

import math

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from backtest_engine.strategy import MarketDataView, Strategy, register_strategy


@register_strategy("volatility_harvest_long_short")
class VolatilityHarvestLongShort(Strategy):
    def __init__(self, params: dict):
        super().__init__(params)
        self.model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        self.scaler = StandardScaler()
        self.trained = False
        self.last_train_month: tuple[int, int] | None = None
        self.last_short_week: tuple[int, int] | None = None
        self.short_entries: dict[str, dict[str, float]] = {}
        self.long_trail: dict[str, dict[str, float]] = {}
        self.selected_shorts: list[str] = []

    def target_weights(self, data: MarketDataView, current_weights: dict[str, float]) -> dict[str, float]:
        date = data.current_date
        if self.last_train_month != (date.year, date.month):
            self._train_model(data)
            self.last_train_month = (date.year, date.month)

        long_targets = self._long_targets(data)
        long_targets = self._apply_long_trails(data, long_targets)
        short_targets = self._short_targets(data, date)
        return {**long_targets, **short_targets}

    def _long_targets(self, data: MarketDataView) -> dict[str, float]:
        top = list(self.params.get("top_long_symbols", ["AAPL", "MSFT", "NVDA", "AMZN"]))
        long_gross = float(self.params.get("long_gross", 0.9))
        gld = self.params.get("gld_symbol", "GLD")
        vix = data.history(self.params.get("vix_symbol", "VIXCLS"), "close")
        spy = data.history(self.params.get("spy_symbol", "SPY"), "close")
        if len(vix) < 100 or len(spy) < 200:
            return {}

        current_vix = float(vix.iloc[-1])
        vix_sma20 = float(vix.iloc[-20:].mean())
        vix_p80 = float(np.percentile(vix.iloc[-100:], 80))
        spy_current = float(spy.iloc[-1])
        spy_sma50 = float(spy.iloc[-50:].mean())
        spy_sma200 = float(spy.iloc[-200:].mean())
        spy_5d_ret = float(spy.iloc[-1] / spy.iloc[-5] - 1.0)
        ml_bullish = self._ml_bullish(vix, spy)

        if current_vix > vix_p80 and spy_5d_ret < -0.03:
            weight = 1.0 if ml_bullish else 0.85
            return self._allocate_top(top, long_gross * weight, ml_bullish) | {gld: long_gross * (1.0 - weight)}
        if current_vix < 13 and spy_current > spy_sma50 * 1.05:
            return self._allocate_top(top, long_gross * 0.40, ml_bullish) | {gld: long_gross * 0.40}
        if 20 < current_vix < vix_sma20:
            weight = 0.85 if ml_bullish else 0.70
            return self._allocate_top(top, long_gross * weight, ml_bullish) | {gld: long_gross * (1.0 - weight)}
        if current_vix > vix_sma20 * 1.2:
            return {gld: long_gross * 0.50}
        if spy_current > spy_sma200:
            base = 0.90 if ml_bullish else 0.70
            return self._allocate_top(top, long_gross * base, ml_bullish) | {gld: long_gross * (1.0 - base)}
        return self._allocate_top(top, long_gross * 0.30, ml_bullish) | {gld: long_gross * 0.50}

    def _allocate_top(self, symbols: list[str], total_weight: float, ml_bullish: bool) -> dict[str, float]:
        if total_weight <= 0 or not symbols:
            return {}
        n = len(symbols)
        weights = np.array([total_weight / n] * n, dtype=float)
        if ml_bullish and float(self.params.get("ml_tilt", 0.25)) > 0 and n >= 2:
            extra = weights[0] * float(self.params.get("ml_tilt", 0.25))
            weights[0] += extra
            weights[1:] -= extra / float(n - 1)
        weights = self._cap_and_renormalize(
            weights,
            total_weight,
            float(self.params.get("top_weight_min", 0.0)),
            float(self.params.get("top_weight_max", 0.35)),
        )
        return {symbol: float(weight) for symbol, weight in zip(symbols, weights) if weight > 0}

    @staticmethod
    def _cap_and_renormalize(weights: np.ndarray, total: float, wmin: float, wmax: float) -> np.ndarray:
        w = weights.astype(float)
        if wmin > 0:
            w = np.maximum(w, wmin)
        if wmax > 0:
            w = np.minimum(w, wmax)
        for _ in range(10):
            diff = float(total - w.sum())
            if abs(diff) < 1e-8:
                break
            if diff > 0:
                idx = [i for i, value in enumerate(w) if wmax <= 0 or value < wmax - 1e-12]
            else:
                idx = [i for i, value in enumerate(w) if wmin <= 0 or value > wmin + 1e-12]
            if not idx:
                break
            w[idx] += diff / len(idx)
            if wmin > 0:
                w = np.maximum(w, wmin)
            if wmax > 0:
                w = np.minimum(w, wmax)
        return w

    def _apply_long_trails(self, data: MarketDataView, targets: dict[str, float]) -> dict[str, float]:
        top = set(self.params.get("top_long_symbols", []))
        adjusted = dict(targets)
        for symbol, target in list(targets.items()):
            if symbol not in top or target <= 0:
                continue
            price = float(data.history(symbol, "close").iloc[-1])
            state = self.long_trail.setdefault(symbol, {"high": price, "stage": 0.0, "target_w": target})
            state["target_w"] = target
            state["high"] = max(float(state["high"]), price)
            drawdown = (float(state["high"]) - price) / float(state["high"]) if state["high"] else 0.0
            stage = int(state["stage"])
            if stage == 0 and drawdown >= float(self.params.get("long_trail_1", 0.095)):
                adjusted[symbol] = target * (2.0 / 3.0)
                state.update({"stage": 1.0, "high": price})
            elif stage == 1 and drawdown >= float(self.params.get("long_trail_2", 0.07)):
                adjusted[symbol] = target * (1.0 / 3.0)
                state.update({"stage": 2.0, "high": price})
            elif stage == 2 and drawdown >= float(self.params.get("long_trail_3", 0.0485)):
                adjusted.pop(symbol, None)
                self.long_trail.pop(symbol, None)
        for symbol in list(self.long_trail):
            if symbol not in adjusted:
                self.long_trail.pop(symbol, None)
        return adjusted

    def _short_targets(self, data: MarketDataView, date: pd.Timestamp) -> dict[str, float]:
        self._risk_check_shorts(data)
        iso = date.isocalendar()
        if self.last_short_week != (iso.year, iso.week):
            self.selected_shorts = self._select_shorts(data)
            self.last_short_week = (iso.year, iso.week)
        if not self.selected_shorts:
            return {}
        weight = -abs(float(self.params.get("short_gross", 0.6))) / len(self.selected_shorts)
        targets = {}
        for symbol in self.selected_shorts:
            close = float(data.history(symbol, "close").iloc[-1])
            atr20 = self._atr(data, symbol, 20)
            if atr20 is None:
                continue
            self.short_entries.setdefault(symbol, {"entry_price": close, "entry_atr": atr20})
            targets[symbol] = weight
        return targets

    def _risk_check_shorts(self, data: MarketDataView) -> None:
        for symbol, info in list(self.short_entries.items()):
            close = data.history(symbol, "close")
            if close.empty:
                self.short_entries.pop(symbol, None)
                continue
            price = float(close.iloc[-1])
            if price - float(info["entry_price"]) > float(self.params.get("stop_atr", 2.0)) * float(info["entry_atr"]):
                self.short_entries.pop(symbol, None)
                if symbol in self.selected_shorts:
                    self.selected_shorts.remove(symbol)

    def _select_shorts(self, data: MarketDataView) -> list[str]:
        excluded = set(self.params.get("top_long_symbols", [])) | {self.params.get("spy_symbol", "SPY"), self.params.get("gld_symbol", "GLD")}
        scored = []
        for symbol in self.params.get("short_universe", []):
            if symbol in excluded:
                continue
            out = self._score_short(data, symbol)
            if out is None:
                continue
            score, ext_ok, mom_ok = out
            if score >= float(self.params.get("score_threshold", 0.85)) and ext_ok and mom_ok:
                scored.append((score, symbol))
        scored.sort(reverse=True)
        return [symbol for _, symbol in scored[: int(self.params.get("top_n", 1))]]

    def _score_short(self, data: MarketDataView, symbol: str) -> tuple[float, bool, bool] | None:
        close = data.history(symbol, "close")
        high = data.history(symbol, "high")
        low = data.history(symbol, "low")
        if len(close) < int(self.params.get("lookback_bars", 260)):
            return None
        hvals = []
        for n in self.params.get("n_list", [10, 10, 40, 60, 90, 100]):
            h = self._hurst_like(high, low, close, int(n), 0.01 + 0.0002 * int(n))
            if h is not None:
                hvals.append(h)
        if len(hvals) < 4:
            return None
        havg = float(sum(hvals) / len(hvals))
        agree = sum(1 for h in hvals if h > 0.6)
        atr20 = self._atr(data, symbol, 20)
        if atr20 is None or atr20 <= 0:
            return None
        close_now = float(close.iloc[-1])
        sma = float(close.iloc[-int(self.params.get("sma_len", 195)):].mean())
        close_5 = float(close.iloc[-5])
        ext_ok = (close_now - sma) > float(self.params.get("ext_k", 2.0)) * atr20
        mom_ok = (close_now - close_5) > float(self.params.get("mom_k", 1.75)) * atr20
        return havg + 0.02 * max(0, agree - 3), ext_ok, mom_ok

    def _atr(self, data: MarketDataView, symbol: str, n: int) -> float | None:
        high = data.history(symbol, "high")
        low = data.history(symbol, "low")
        close = data.history(symbol, "close")
        if len(close) < n + 1:
            return None
        total = 0.0
        for i in range(1, n + 1):
            hi = float(high.iloc[-i])
            lo = float(low.iloc[-i])
            cl = float(close.iloc[-i])
            total += max(hi - lo, abs(hi - cl), abs(lo - cl))
        return total / float(n)

    @staticmethod
    def _hurst_like(high: pd.Series, low: pd.Series, close: pd.Series, n: int, bump: float) -> float | None:
        if len(close) < n + 1:
            return None
        atr = 0.0
        for i in range(1, n + 1):
            hi = float(high.iloc[-i])
            lo = float(low.iloc[-i])
            cl = float(close.iloc[-i])
            atr += max(hi - lo, abs(hi - cl), abs(lo - cl))
        atr /= float(n)
        if atr <= 0:
            return None
        span = float(high.iloc[-n:].max() - low.iloc[-n:].min())
        if span <= 0:
            return None
        h = (math.log(span) - math.log(atr)) / math.log(float(n))
        return h + bump if h > 0.45 else h - bump

    def _train_model(self, data: MarketDataView) -> None:
        vix = data.history(self.params.get("vix_symbol", "VIXCLS"), "close").iloc[-800:]
        spy = data.history(self.params.get("spy_symbol", "SPY"), "close").iloc[-800:]
        if len(vix) < int(self.params.get("min_training", 504)) or len(spy) < int(self.params.get("min_training", 504)):
            return
        X, y = [], []
        for i in range(200, len(spy) - 21):
            feats = self._features(vix.iloc[:i], spy.iloc[:i])
            if feats is None:
                continue
            X.append(feats)
            y.append(1 if spy.iloc[i + 21] / spy.iloc[i] > 1.02 else 0)
        if len(X) < 100 or len(set(y)) < 2:
            return
        x_arr = np.array(X)
        y_arr = np.array(y)
        self.scaler.fit(x_arr)
        self.model.fit(self.scaler.transform(x_arr), y_arr)
        self.trained = True

    def _ml_bullish(self, vix: pd.Series, spy: pd.Series) -> bool:
        if not self.trained:
            return False
        feats = self._features(vix, spy)
        if feats is None:
            return False
        x = self.scaler.transform([feats])
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(x)[0]
            if len(probs) == 2:
                return float(probs[1]) > 0.6
        return bool(self.model.predict(x)[0] == 1)

    @staticmethod
    def _features(vix: pd.Series, spy: pd.Series) -> list[float] | None:
        if len(vix) < 50 or len(spy) < 200:
            return None
        current_vix = float(vix.iloc[-1])
        vix_sma20 = float(vix.iloc[-20:].mean())
        vix_sma50 = float(vix.iloc[-50:].mean())
        vix_std = float(vix.iloc[-20:].std(ddof=0))
        vix_zscore = (current_vix - vix_sma20) / vix_std if vix_std > 0 else 0.0
        vix_percentile = float((vix < current_vix).sum()) / float(len(vix))
        spy_current = float(spy.iloc[-1])
        spy_sma50 = float(spy.iloc[-50:].mean())
        spy_sma200 = float(spy.iloc[-200:].mean())
        spy_vol = float(spy.pct_change().iloc[-20:].std(ddof=0) * np.sqrt(252))
        return [
            current_vix,
            vix_zscore,
            vix_percentile,
            current_vix / vix_sma20 if vix_sma20 else 1.0,
            current_vix / vix_sma50 if vix_sma50 else 1.0,
            float(spy.iloc[-1] / spy.iloc[-5] - 1.0),
            float(spy.iloc[-1] / spy.iloc[-10] - 1.0),
            float(spy.iloc[-1] / spy.iloc[-20] - 1.0),
            spy_current / spy_sma50 if spy_sma50 else 1.0,
            spy_current / spy_sma200 if spy_sma200 else 1.0,
            spy_vol,
        ]
