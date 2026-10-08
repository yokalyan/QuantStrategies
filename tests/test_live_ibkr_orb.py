from __future__ import annotations

import pandas as pd

from backtest_engine.intraday_orb import OrbRecommendation
from backtest_engine.live_ibkr_orb import _build_bracket_orders, _replace_stop_order


class FakeClient:
    def __init__(self):
        self.next_id = 100

    def getReqId(self):
        value = self.next_id
        self.next_id += 1
        return value


class FakeIB:
    def __init__(self):
        self.client = FakeClient()
        self.cancelled = []
        self.placed = []

    def cancelOrder(self, order):
        self.cancelled.append(order)

    def placeOrder(self, contract, order):
        self.placed.append(order)
        return FakeTrade(order)

    def sleep(self, seconds):
        return None


class FakeOrder:
    def __init__(self):
        self.orderId = 0
        self.action = ""
        self.orderType = ""
        self.totalQuantity = 0
        self.auxPrice = 0.0
        self.lmtPrice = 0.0
        self.parentId = 0
        self.tif = ""
        self.transmit = False
        self.ocaGroup = ""
        self.ocaType = 0
        self.account = ""


class FakeLimitOrder(FakeOrder):
    def __init__(self, action, total_quantity, limit_price):
        super().__init__()
        self.action = action
        self.totalQuantity = total_quantity
        self.orderType = "LMT"
        self.lmtPrice = limit_price


class FakeTrade:
    def __init__(self, order):
        self.order = order
        self.orderStatus = type("Status", (), {"status": "Submitted", "filled": 0, "remaining": order.totalQuantity})()


def recommendation() -> OrbRecommendation:
    return OrbRecommendation(
        symbol="TQQQ",
        session_date=pd.Timestamp("2024-01-03"),
        opening_range_minutes=15,
        direction=1,
        or_open=47.17,
        or_close=47.38,
        or_high=47.45,
        or_low=46.92,
        or_mid=47.18,
        or_range=0.5267,
        atr20=1.6573,
        ratio=0.3178,
        ratio_min=0.20,
        ratio_max=0.35,
        avg_opening_range=0.4942,
        max_range_valid=True,
        ratio_valid=True,
        capital=5000,
        risk_amount=30,
        max_notional=20000,
        shares=113,
        entry=47.45,
        stop=47.18,
        target=50.08,
        breakeven_trigger=49.03,
        profit_target_r=10,
        breakeven_r=6,
        risk_per_share=0.2633,
    )


def test_bracket_orders_use_oca_and_delayed_transmit():
    ib = FakeIB()
    orders = _build_bracket_orders(ib, recommendation(), "DU123", FakeOrder, FakeLimitOrder)

    parent, take_profit, stop_loss = orders
    assert parent.orderType == "STP"
    assert parent.auxPrice == 47.45
    assert parent.transmit is False
    assert take_profit.parentId == parent.orderId
    assert stop_loss.parentId == parent.orderId
    assert take_profit.ocaGroup == stop_loss.ocaGroup
    assert take_profit.ocaType == stop_loss.ocaType == 1
    assert take_profit.transmit is False
    assert stop_loss.transmit is True
    assert all(order.account == "DU123" for order in orders)


def test_replace_stop_cancels_old_stop_and_sends_breakeven_stop():
    ib = FakeIB()
    _, _, stop_loss = _build_bracket_orders(ib, recommendation(), None, FakeOrder, FakeLimitOrder)
    old_trade = FakeTrade(stop_loss)

    new_trade = _replace_stop_order(ib, object(), recommendation(), old_trade, None, FakeOrder)

    assert ib.cancelled == [stop_loss]
    assert new_trade.order.orderType == "STP"
    assert new_trade.order.auxPrice == 47.45
    assert new_trade.order.ocaGroup == stop_loss.ocaGroup
    assert new_trade.order.transmit is True


def test_replace_stop_uses_custom_fill_price():
    ib = FakeIB()
    _, _, stop_loss = _build_bracket_orders(ib, recommendation(), None, FakeOrder, FakeLimitOrder)
    old_trade = FakeTrade(stop_loss)

    new_trade = _replace_stop_order(ib, object(), recommendation(), old_trade, None, FakeOrder, stop_price=47.52)

    assert new_trade.order.auxPrice == 47.52


def test_position_size_matches_by_symbol_and_conid():
    from backtest_engine.live_ibkr_orb import _position_size_for_contract

    class FakePosition:
        def __init__(self, symbol, con_id, position):
            self.contract = type("Contract", (), {"symbol": symbol, "conId": con_id})()
            self.position = position

    class MockIB:
        def positions(self):
            return [
                FakePosition("TQQQ", 12345, 100),
                FakePosition("SPY", 99999, 50),
            ]

    ib = MockIB()
    contract_with_id = type("Contract", (), {"symbol": "TQQQ", "conId": 12345})()
    contract_without_id = type("Contract", (), {"symbol": "TQQQ", "conId": None})()

    assert _position_size_for_contract(ib, contract_with_id) == 100
    assert _position_size_for_contract(ib, contract_without_id) == 100


def test_breakeven_reached_condition():
    from backtest_engine.live_ibkr_orb import _breakeven_reached

    rec = recommendation()  # direction = 1 (bullish), breakeven_trigger = 49.03
    assert not _breakeven_reached(rec, float("nan"))
    assert not _breakeven_reached(rec, 48.50)
    assert _breakeven_reached(rec, 49.03)
    assert _breakeven_reached(rec, 49.50)

    # Bearish test
    rec_short = recommendation()
    rec_short.direction = -1
    rec_short.breakeven_trigger = 45.00
    assert not _breakeven_reached(rec_short, float("nan"))
    assert not _breakeven_reached(rec_short, 45.50)
    assert _breakeven_reached(rec_short, 45.00)
    assert _breakeven_reached(rec_short, 44.50)


def test_off_hours_safety_block_raises_on_live_account():
    import pytest
    from pathlib import Path
    from backtest_engine.live_ibkr_orb import IbkrOrbSettings, run_live_ibkr_orb

    # Live port 7496 with off_hours_test=True should raise RuntimeError
    live_settings = IbkrOrbSettings(
        config_path=Path("configs/midpoint_stop_orb_intraday.yaml"),
        capital=5000,
        host="127.0.0.1",
        port=7496,
        client_id=45,
        account="U1234567",
        confirm=False,
        transmit=False,
        wait=False,
        poll_seconds=10,
        signal_buffer_seconds=5,
        manage_orders=False,
        off_hours_test=True,
    )
    with pytest.raises(RuntimeError, match="SAFETY BLOCK"):
        run_live_ibkr_orb(live_settings)


def test_poll_ibkr_bars_off_hours_finds_recent_session():
    from datetime import datetime
    from backtest_engine.live_ibkr_orb import _poll_ibkr_bars

    class FakeBar:
        def __init__(self, dt_str, price):
            self.date = dt_str
            self.open = price
            self.high = price + 0.1
            self.low = price - 0.1
            self.close = price
            self.volume = 1000

    bars = []
    # Create 20 bars on a past day between 09:30 and 09:50
    for m in range(20):
        bars.append(FakeBar(f"2026-10-06 09:{30+m:02d}:00", 50.0))

    class MockIB:
        def reqHistoricalData(self, *args, **kwargs):
            return bars

    ib = MockIB()
    frame = _poll_ibkr_bars(ib, object(), opening_range_minutes=15, poll_seconds=1, off_hours_test=True)
    assert len(frame) == 20
    assert frame["datetime"].iloc[0].hour == 9


