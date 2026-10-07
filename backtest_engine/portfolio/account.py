from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from backtest_engine.execution import CostModel, Fill


@dataclass
class Portfolio:
    cash: float
    positions: dict[str, int] = field(default_factory=dict)
    fills: list[Fill] = field(default_factory=list)

    def value(self, prices: dict[str, float]) -> float:
        return self.cash + sum(shares * prices.get(symbol, 0.0) for symbol, shares in self.positions.items())

    def weights(self, prices: dict[str, float]) -> dict[str, float]:
        equity = self.value(prices)
        if equity <= 0:
            return {}
        return {s: sh * prices.get(s, 0.0) / equity for s, sh in self.positions.items() if sh != 0}

    def rebalance_to_targets(
        self,
        date: pd.Timestamp,
        open_prices: dict[str, float],
        targets: dict[str, float],
        cost_model: CostModel,
        whole_shares: bool = True,
    ) -> None:
        equity = self.value(open_prices)
        symbols = set(self.positions) | set(targets)
        orders: list[tuple[str, int]] = []
        for symbol in symbols:
            price = open_prices.get(symbol)
            if price is None or price <= 0:
                continue
            current_value = self.positions.get(symbol, 0) * price
            target_value = equity * targets.get(symbol, 0.0)
            raw_shares = (target_value - current_value) / price
            shares = int(raw_shares) if whole_shares else round(raw_shares)
            if shares != 0:
                orders.append((symbol, shares))
        sells = [(s, q) for s, q in orders if q < 0]
        buys = [(s, q) for s, q in orders if q > 0]
        for symbol, shares in sells + buys:
            self.apply_fill(date, symbol, shares, open_prices[symbol], cost_model, "rebalance")

    def apply_fill(self, date: pd.Timestamp, symbol: str, shares: int, open_price: float, cost_model: CostModel, reason: str) -> None:
        side = 1 if shares > 0 else -1
        price = cost_model.slipped_price(side, open_price)
        commission = cost_model.commission(shares)
        cash_delta = -(shares * price) - commission
        if shares > 0 and cash_delta + self.cash < -1e-6:
            affordable = int(max((self.cash - commission) / price, 0))
            if affordable <= 0:
                return
            shares = min(shares, affordable)
            commission = cost_model.commission(shares)
            cash_delta = -(shares * price) - commission
        self.cash += cash_delta
        self.positions[symbol] = self.positions.get(symbol, 0) + shares
        if self.positions[symbol] == 0:
            del self.positions[symbol]
        self.fills.append(Fill(date, symbol, shares, price, commission, reason))

