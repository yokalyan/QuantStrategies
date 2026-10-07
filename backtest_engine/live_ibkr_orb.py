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
    manage_orders: bool


def run_live_ibkr_orb(settings: IbkrOrbSettings) -> None:
    try:
        from ib_insync import IB, LimitOrder, MarketOrder, Order, Stock
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

        trades = []
        for order in orders:
            trades.append(ib.placeOrder(contract, order))
            ib.sleep(0.25)
        print("Bracket submitted to IBKR.")
        if settings.manage_orders:
            _manage_day_orders(ib, contract, recommendation, trades, settings, Order, MarketOrder)
        else:
            print("Order manager disabled. Keep TWS/IB Gateway open and manage breakeven/flatten manually.")
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
    oca_group = f"ORB-{recommendation.symbol}-{recommendation.session_date.strftime('%Y%m%d')}-{parent_id}"

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
    take_profit.ocaGroup = oca_group
    take_profit.ocaType = 1
    take_profit.transmit = False

    stop_loss = order_cls()
    stop_loss.orderId = ib.client.getReqId()
    stop_loss.action = exit_action
    stop_loss.orderType = "STP"
    stop_loss.totalQuantity = recommendation.shares
    stop_loss.auxPrice = round(recommendation.stop, 2)
    stop_loss.parentId = parent_id
    stop_loss.tif = "DAY"
    stop_loss.ocaGroup = oca_group
    stop_loss.ocaType = 1
    stop_loss.transmit = True

    if account:
        for order in (parent, take_profit, stop_loss):
            order.account = account

    return [parent, take_profit, stop_loss]


def _manage_day_orders(ib, contract, recommendation: OrbRecommendation, trades, settings: IbkrOrbSettings, order_cls, market_order_cls) -> None:
    parent_trade, target_trade, stop_trade = trades
    stop_moved = False
    entry_cancelled = False
    flattened = False
    print("Order manager running: watching entry until 10:30, breakeven at 6R, flatten at 15:30 ET.")

    while True:
        ib.sleep(settings.poll_seconds)
        now = datetime.now(EASTERN)
        ib.reqOpenOrders()
        ib.sleep(0.25)

        if _is_terminal(parent_trade) and not _is_filled(parent_trade) and not entry_cancelled:
            print(f"{now.strftime('%H:%M:%S')} Entry order is terminal with status {parent_trade.orderStatus.status}. Stopping manager.")
            return

        if not _is_filled(parent_trade):
            if now.time() >= dtime(10, 30):
                print(f"{now.strftime('%H:%M:%S')} Entry not filled by 10:30. Cancelling bracket.")
                _cancel_trade_if_active(ib, parent_trade)
                _cancel_trade_if_active(ib, target_trade)
                _cancel_trade_if_active(ib, stop_trade)
                entry_cancelled = True
                return
            print(f"{now.strftime('%H:%M:%S')} Entry pending: {parent_trade.orderStatus.status}.")
            continue

        if _is_filled(target_trade) or _is_filled(stop_trade):
            print(f"{now.strftime('%H:%M:%S')} Exit detected. Target status={target_trade.orderStatus.status}; stop status={stop_trade.orderStatus.status}.")
            return

        latest_price = _latest_price(ib, contract)
        print(f"{now.strftime('%H:%M:%S')} Filled; latest {recommendation.symbol} price {latest_price:.2f}.")

        if (not stop_moved) and _breakeven_reached(recommendation, latest_price):
            print(f"{now.strftime('%H:%M:%S')} 6R reached. Moving stop to breakeven {recommendation.entry:.2f}.")
            replacement = _replace_stop_order(ib, contract, recommendation, stop_trade, settings.account, order_cls)
            stop_trade = replacement
            stop_moved = True

        if now.time() >= dtime(15, 30) and not flattened:
            print(f"{now.strftime('%H:%M:%S')} Flatten time reached. Cancelling exits and flattening position.")
            _cancel_trade_if_active(ib, target_trade)
            _cancel_trade_if_active(ib, stop_trade)
            _flatten_position(ib, contract, recommendation, settings.account, market_order_cls)
            flattened = True
            return


def _replace_stop_order(ib, contract, recommendation: OrbRecommendation, stop_trade, account: str | None, order_cls):
    _cancel_trade_if_active(ib, stop_trade)
    ib.sleep(1)
    replacement = order_cls()
    replacement.orderId = ib.client.getReqId()
    replacement.action = "SELL" if recommendation.direction > 0 else "BUY"
    replacement.orderType = "STP"
    replacement.totalQuantity = recommendation.shares
    replacement.auxPrice = round(recommendation.entry, 2)
    replacement.tif = "DAY"
    replacement.ocaGroup = stop_trade.order.ocaGroup
    replacement.ocaType = getattr(stop_trade.order, "ocaType", 1) or 1
    replacement.transmit = True
    if account:
        replacement.account = account
    new_trade = ib.placeOrder(contract, replacement)
    ib.sleep(0.25)
    return new_trade


def _flatten_position(ib, contract, recommendation: OrbRecommendation, account: str | None, market_order_cls) -> None:
    ib.reqPositions()
    ib.sleep(1)
    position_size = _position_size_for_contract(ib, contract)
    if position_size == 0:
        print("No open position found to flatten.")
        return
    action = "SELL" if position_size > 0 else "BUY"
    order = market_order_cls(action, abs(position_size))
    order.tif = "DAY"
    if account:
        order.account = account
    trade = ib.placeOrder(contract, order)
    ib.sleep(1)
    print(f"Flatten order submitted: {action} {abs(position_size)} {recommendation.symbol}; status={trade.orderStatus.status}.")


def _position_size_for_contract(ib, contract) -> int:
    con_id = getattr(contract, "conId", None)
    total = 0
    for position in ib.positions():
        if getattr(position.contract, "conId", None) == con_id:
            total += int(position.position)
    return total


def _latest_price(ib, contract) -> float:
    ticker = ib.reqMktData(contract, "", False, False)
    ib.sleep(2)
    price = ticker.marketPrice()
    ib.cancelMktData(contract)
    if price is not None and pd.notna(price) and price > 0:
        return float(price)
    bars = ib.reqHistoricalData(
        contract,
        endDateTime="",
        durationStr="1 D",
        barSizeSetting="1 min",
        whatToShow="TRADES",
        useRTH=True,
        formatDate=1,
        keepUpToDate=False,
    )
    frame = _bars_to_frame(bars)
    return float(frame.iloc[-1]["close"])


def _breakeven_reached(recommendation: OrbRecommendation, latest_price: float) -> bool:
    if recommendation.direction > 0:
        return latest_price >= recommendation.breakeven_trigger
    return latest_price <= recommendation.breakeven_trigger


def _is_filled(trade) -> bool:
    return trade.orderStatus.status == "Filled" or float(trade.orderStatus.remaining or 0) == 0 and float(trade.orderStatus.filled or 0) > 0


def _is_terminal(trade) -> bool:
    return trade.orderStatus.status in {"Filled", "Cancelled", "ApiCancelled", "Inactive"}


def _cancel_trade_if_active(ib, trade) -> None:
    if not _is_terminal(trade):
        ib.cancelOrder(trade.order)
        ib.sleep(0.5)


def _print_live_order_warning(settings: IbkrOrbSettings) -> None:
    mode = "TRANSMIT ENABLED" if settings.transmit else "DRY RUN"
    port_hint = "paper" if settings.port in {7497, 4002} else "live"
    print("")
    print(f"IBKR mode: {mode}; connected port looks like {port_hint}.")
    if settings.manage_orders:
        print("After submission this process must remain running to manage 10:30 entry expiry, 6R stop move, and 15:30 flatten.")
    else:
        print("Order manager disabled. Breakeven stop moves and 15:30 flattening require manual handling.")
