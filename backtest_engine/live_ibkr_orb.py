from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, time as dtime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yaml

from backtest_engine.intraday_orb import OrbRecommendation, build_orb_recommendation, print_orb_recommendation


EASTERN = ZoneInfo("America/New_York")


@dataclass
class IbkrOrbSettings:
    config_path: Path
    capital: float | None
    host: str
    port: int
    client_id: int
    account: str | None
    confirm: bool
    transmit: bool
    wait: bool
    poll_seconds: int
    signal_buffer_seconds: int


def run_live_ibkr_orb(settings: IbkrOrbSettings) -> None:
    try:
        from ib_insync import IB, LimitOrder, Order, Stock
    except ImportError as exc:
        raise RuntimeError("Install live dependencies first: python -m pip install '.[live]'") from exc

    config = yaml.safe_load(settings.config_path.read_text(encoding="utf-8"))
    symbol = config["symbol"]
    params = config["strategy"]["params"]
    opening_range_minutes = int(params.get("opening_range_minutes", 15))
    signal_at = _next_signal_time(opening_range_minutes, settings.signal_buffer_seconds)

    if settings.wait:
        _wait_until(signal_at)

    ib = IB()
    print(f"Connecting to IBKR at {settings.host}:{settings.port} clientId={settings.client_id}...")
    ib.connect(settings.host, settings.port, clientId=settings.client_id, timeout=20)
    try:
        contract = Stock(symbol, "SMART", "USD")
        ib.qualifyContracts(contract)
        frame = _poll_ibkr_bars(ib, contract, opening_range_minutes, settings.poll_seconds)
        recommendation = build_orb_recommendation(config, frame, None, settings.capital)
        print_orb_recommendation(recommendation)
        if not recommendation.can_trade:
            print("No order submitted.")
            return

        _print_live_order_warning(settings)
        if settings.confirm:
            expected = f"YES {recommendation.symbol} {recommendation.shares}"
            response = input(f"Type '{expected}' to submit the bracket order: ").strip()
            if response != expected:
                print("Confirmation did not match. No order submitted.")
                return

        orders = _build_bracket_orders(ib, recommendation, settings.account, Order, LimitOrder)
        print("")
        print("Prepared IBKR bracket:")
        for order in orders:
            detail = getattr(order, "lmtPrice", None) or getattr(order, "auxPrice", None)
            print(f"- {order.action} {order.totalQuantity} {order.orderType} {detail} transmit={order.transmit} parentId={order.parentId}")

        if not settings.transmit:
            print("Dry run only. Re-run with --transmit to send orders after confirmation.")
            return

        for order in orders:
            ib.placeOrder(contract, order)
            ib.sleep(0.25)
        print("Bracket submitted to IBKR. Keep TWS/IB Gateway and this terminal open until you verify order state.")
    finally:
        ib.disconnect()


def _next_signal_time(opening_range_minutes: int, buffer_seconds: int) -> datetime:
    now = datetime.now(EASTERN)
    signal = datetime.combine(now.date(), dtime(9, 30), EASTERN) + timedelta(minutes=opening_range_minutes, seconds=buffer_seconds)
    return signal


def _wait_until(signal_at: datetime) -> None:
    while True:
        now = datetime.now(EASTERN)
        seconds = (signal_at - now).total_seconds()
        if seconds <= 0:
            return
        sleep_for = min(max(seconds, 1), 30)
        print(f"Waiting until {signal_at.strftime('%H:%M:%S %Z')} for completed opening range...")
        time.sleep(sleep_for)


def _poll_ibkr_bars(ib, contract, opening_range_minutes: int, poll_seconds: int) -> pd.DataFrame:
    min_completed_time = (pd.Timestamp.now(tz=EASTERN).normalize() + pd.Timedelta(hours=9, minutes=30 + opening_range_minutes - 1)).time()
    while True:
        bars = ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr="40 D",
            barSizeSetting="1 min",
            whatToShow="TRADES",
            useRTH=True,
            formatDate=1,
            keepUpToDate=False,
        )
        frame = _bars_to_frame(bars)
        today = pd.Timestamp.now(tz=EASTERN).normalize().tz_localize(None)
        today_bars = frame[frame["datetime"].dt.normalize() == today]
        if len(today_bars) >= opening_range_minutes and today_bars["datetime"].max().time() >= min_completed_time:
            return frame
        print(f"Waiting for {opening_range_minutes} completed regular-session bars from IBKR...")
        time.sleep(poll_seconds)


def _bars_to_frame(bars) -> pd.DataFrame:
    rows = []
    for bar in bars:
        dt = pd.Timestamp(bar.date)
        if dt.tzinfo is not None:
            dt = dt.tz_convert(EASTERN).tz_localize(None)
        rows.append(
            {
                "datetime": dt.to_pydatetime(),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": float(bar.volume),
            }
        )
    if not rows:
        raise RuntimeError("IBKR returned no historical bars.")
    return pd.DataFrame(rows).sort_values("datetime").reset_index(drop=True)


def _build_bracket_orders(ib, recommendation: OrbRecommendation, account: str | None, order_cls, limit_order_cls):
    parent_id = ib.client.getReqId()
    action = "BUY" if recommendation.direction > 0 else "SELL"
    exit_action = "SELL" if recommendation.direction > 0 else "BUY"

    parent = order_cls()
    parent.orderId = parent_id
    parent.action = action
    parent.orderType = "STP"
    parent.totalQuantity = recommendation.shares
    parent.auxPrice = round(recommendation.entry, 2)
    parent.tif = "DAY"
    parent.transmit = False

    take_profit = limit_order_cls(exit_action, recommendation.shares, round(recommendation.target, 2))
    take_profit.orderId = ib.client.getReqId()
    take_profit.parentId = parent_id
    take_profit.tif = "DAY"
    take_profit.transmit = False

    stop_loss = order_cls()
    stop_loss.orderId = ib.client.getReqId()
    stop_loss.action = exit_action
    stop_loss.orderType = "STP"
    stop_loss.totalQuantity = recommendation.shares
    stop_loss.auxPrice = round(recommendation.stop, 2)
    stop_loss.parentId = parent_id
    stop_loss.tif = "DAY"
    stop_loss.transmit = True

    if account:
        for order in (parent, take_profit, stop_loss):
            order.account = account

    return [parent, take_profit, stop_loss]


def _print_live_order_warning(settings: IbkrOrbSettings) -> None:
    mode = "TRANSMIT ENABLED" if settings.transmit else "DRY RUN"
    port_hint = "paper" if settings.port in {7497, 4002} else "live"
    print("")
    print(f"IBKR mode: {mode}; connected port looks like {port_hint}.")
    print("This creates a DAY stop-entry bracket. Breakeven stop moves and 15:30 flattening still require monitoring.")
