from __future__ import annotations

from backtest_engine.indicators import momentum_return, realized_volatility
from backtest_engine.strategy import MarketDataView, Strategy, register_strategy


@register_strategy("tech_momentum_gld_sweep")
class TechMomentumGLDSweep(Strategy):
    def __init__(self, params: dict):
        super().__init__(params)
        self.last_rebalance_month: tuple[int, int] | None = None
        self.targets: dict[str, float] = {}
        self.entry_prices: dict[str, float] = {}

    def target_weights(self, data: MarketDataView, current_weights: dict[str, float]) -> dict[str, float]:
        month_key = (data.current_date.year, data.current_date.month)
        if self.last_rebalance_month != month_key:
            self.targets = self._monthly_targets(data)
            self.entry_prices = {
                symbol: float(data.history(symbol, "close").iloc[-1])
                for symbol, weight in self.targets.items()
                if symbol != self.params.get("defensive_symbol", "GLD") and weight > 0
            }
            self.last_rebalance_month = month_key
        self._apply_stops(data)
        return self._with_defensive_sweep()

    def _monthly_targets(self, data: MarketDataView) -> dict[str, float]:
        universe = list(self.params["universe"])
        momentum_lookback = int(self.params.get("momentum_lookback", 90))
        vol_lookback = int(self.params.get("volatility_lookback", 20))
        top_n = int(self.params.get("top_n", 10))
        scored: list[tuple[float, str, float]] = []
        for symbol in universe:
            close = data.history(symbol, "close")
            if len(close) <= max(momentum_lookback, vol_lookback):
                continue
            momentum = momentum_return(close, momentum_lookback)
            if momentum <= 0:
                continue
            vol = realized_volatility(close, vol_lookback)
            if vol <= 0:
                continue
            scored.append((momentum, symbol, vol))
        leaders = sorted(scored, key=lambda item: (-item[0], item[1]))[:top_n]
        inv_vol = {symbol: 1.0 / vol for _, symbol, vol in leaders}
        total = sum(inv_vol.values())
        if total <= 0:
            return {}
        equity_budget = float(self.params.get("equity_budget", 1.0))
        return {symbol: equity_budget * value / total for symbol, value in inv_vol.items()}

    def _apply_stops(self, data: MarketDataView) -> None:
        stop_loss_portfolio = float(self.params.get("stop_loss_portfolio", 0.02))
        defensive = self.params.get("defensive_symbol", "GLD")
        for symbol in list(self.targets):
            if symbol == defensive:
                continue
            entry = self.entry_prices.get(symbol)
            if entry is None or entry <= 0:
                continue
            price = float(data.history(symbol, "close").iloc[-1])
            position_weight = self.targets.get(symbol, 0.0)
            portfolio_loss = position_weight * max(0.0, 1.0 - price / entry)
            if portfolio_loss > stop_loss_portfolio:
                self.targets.pop(symbol, None)
                self.entry_prices.pop(symbol, None)

    def _with_defensive_sweep(self) -> dict[str, float]:
        defensive = self.params.get("defensive_symbol", "GLD")
        sweep_threshold = float(self.params.get("sweep_threshold", 0.01))
        targets = {symbol: weight for symbol, weight in self.targets.items() if weight > 0}
        residual = max(0.0, 1.0 - sum(targets.values()))
        if residual >= sweep_threshold:
            targets[defensive] = targets.get(defensive, 0.0) + residual
        return targets
