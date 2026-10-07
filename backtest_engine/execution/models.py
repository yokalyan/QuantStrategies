from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostModel:
    commission_per_share: float = 0.005
    min_commission: float = 1.0
    slippage_bps: float = 1.0

    def commission(self, shares: int) -> float:
        if shares == 0:
            return 0.0
        return max(abs(shares) * self.commission_per_share, self.min_commission)

    def slipped_price(self, side: int, open_price: float) -> float:
        return open_price * (1.0 + side * self.slippage_bps / 10_000.0)


@dataclass
class Fill:
    date: object
    symbol: str
    shares: int
    price: float
    commission: float
    reason: str

