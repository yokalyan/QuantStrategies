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
    off_hours_test: bool = False


def run_live_ibkr_orb(settings: IbkrOrbSettings) -> None:
    try:
        from ib_insync import IB, LimitOrder, MarketOrder, Order, Stock
    except ImportError as exc:
        raise RuntimeError("Install live dependencies first: python -m pip install '.[live]'") from exc

    if settings.off_hours_test:
        is_paper_port = settings.port in {7497, 4002}
        is_paper_account = bool(
            settings.account is not None
            and (settings.account.upper().startswith("DU") or settings.account.upper().startswith("DF"))
        )
        if not is_paper_port and not is_paper_account:
            raise RuntimeError(
                f"SAFETY BLOCK: --off-hours-test is restricted to paper trading only! "
                f"Connected port is {settings.port} and account is {settings.account}. "
                f"To use paper trading, connect to port 7497/4002 or configure a paper account."
            )

    config = yaml.safe_load(settings.config_path.read_text(encoding="utf-8"))
    symbol = config["symbol"]
    params = config["strategy"]["params"]
    opening_range_minutes = int(params.get("opening_range_minutes", 15))
    signal_at = _next_signal_time(opening_range_minutes, settings.signal_buffer_seconds)
    entry_cutoff = _parse_time_str(str(params.get("entry_cutoff_time", "10:30")), dtime(10, 30))
    flatten_time = _parse_time_str(str(params.get("flatten_time", "15:30")), dtime(15, 30))

    if settings.wait and not settings.off_hours_test:
        _wait_until(signal_at)

    ib = IB()
    print(f"Connecting to IBKR at {settings.host}:{settings.port} clientId={settings.client_id}...")
    ib.connect(settings.host, settings.port, clientId=settings.client_id, timeout=20)
    try:
        ib.reqMarketDataType(3)
        contract = Stock(symbol, "SMART", "USD")
        ib.qualifyContracts(contract)
        frame = _poll_ibkr_bars(ib, contract, opening_range_minutes, settings.poll_seconds, off_hours_test=settings.off_hours_test)
        recommendation = build_orb_recommendation(config, frame, None, settings.capital)
        print_orb_recommendation(recommendation)
        if not recommendation.can_trade:
            print("No order submitted.")
            return

        _print_live_order_warning(settings)
        now = datetime.now(EASTERN)
        if now.time() >= entry_cutoff:
            if settings.off_hours_test:
                print(f"[TEST MODE] Current time {now.strftime('%H:%M:%S')} is past {entry_cutoff.strftime('%H:%M')} ET, but --off-hours-test is active (paper mode). Proceeding.")
            else:
                print(f"NOTE: Current time {now.strftime('%H:%M:%S')} is past the {entry_cutoff.strftime('%H:%M')} ET entry window.")
                if settings.transmit:
                    print(f"Cannot transmit live/paper orders outside the entry window (until {entry_cutoff.strftime('%H:%M')} ET).")
                    return

        if settings.confirm:
            response = input("Type 'yes' to submit the bracket order: ").strip().lower()
            if response not in {"y", "yes"}:
                print("Confirmation not received. No order submitted.")
                return

        orders = _build_bracket_orders(ib, recommendation, settings.account, Order, LimitOrder)
        print("")
        print("Prepared IBKR bracket:")
        for order in orders:
            detail = _order_price_str(order)
            print(f"- {order.action} {order.totalQuantity} {order.orderType} {detail} transmit={order.transmit} parentId={order.parentId}")

        should_transmit = settings.transmit
        if not should_transmit:
            try:
                prompt_resp = input("Dry run mode: do you want to transmit this bracket to IBKR now? [y/N]: ").strip().lower()
                if prompt_resp in {"y", "yes"}:
                    should_transmit = True
                else:
                    print("Dry run only. No orders transmitted. (Use --transmit or type 'y' to send).")
                    return
            except (EOFError, KeyboardInterrupt):
                print("\nCancelled. No orders transmitted.")
                return

        trades = []
        for order in orders:
            trades.append(ib.placeOrder(contract, order))
            ib.sleep(0.25)
        print("Bracket submitted to IBKR.")
        if settings.manage_orders:
            _manage_day_orders(ib, contract, recommendation, trades, settings, Order, MarketOrder, entry_cutoff, flatten_time)
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


def _poll_ibkr_bars(ib, contract, opening_range_minutes: int, poll_seconds: int, off_hours_test: bool = False) -> pd.DataFrame:
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
        if off_hours_test:
            regular = frame[(frame["datetime"].dt.time >= dtime(9, 30)) & (frame["datetime"].dt.time <= dtime(15, 59))]
            if not regular.empty:
                sessions = list(regular.groupby(regular["datetime"].dt.normalize()))
                for session_date, day_bars in reversed(sessions):
                    if len(day_bars) >= opening_range_minutes:
                        print(f"[TEST MODE] Using completed session ({session_date.date()}) with {len(day_bars)} bars for off-hours testing.")
                        return frame
            raise RuntimeError(f"Could not find a historical session with at least {opening_range_minutes} completed regular-session bars.")

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


def _parse_time_str(val: str, default: dtime) -> dtime:
    try:
        parts = [int(p) for p in val.strip().split(":")]
        return dtime(parts[0], parts[1])
    except Exception:
        return default


def _manage_day_orders(ib, contract, recommendation: OrbRecommendation, trades, settings: IbkrOrbSettings, order_cls, market_order_cls, entry_cutoff: dtime = dtime(10, 30), flatten_time: dtime = dtime(15, 30)) -> None:
    parent_trade, target_trade, stop_trade = trades
    stop_moved = False
    entry_cancelled = False
    flattened = False
    if settings.off_hours_test:
        print(f"[TEST MODE] Order manager running with --off-hours-test: wall-clock {entry_cutoff.strftime('%H:%M')} entry expiry and {flatten_time.strftime('%H:%M')} flatten are bypassed.")
    else:
        print(f"Order manager running: watching entry until {entry_cutoff.strftime('%H:%M')}, breakeven at 6R, flatten at {flatten_time.strftime('%H:%M')} ET.")
    ticker = ib.reqMktData(contract, "", False, False)

    try:
        while True:
            now = datetime.now(EASTERN)
            ib.reqOpenOrders()
            ib.sleep(0.25)

            if _is_terminal(parent_trade) and not _is_filled(parent_trade) and not entry_cancelled:
                print(f"{now.strftime('%H:%M:%S')} Entry order is terminal with status {parent_trade.orderStatus.status}. Stopping manager.")
                return

            if not _is_filled(parent_trade):
                if (not settings.off_hours_test) and now.time() >= entry_cutoff:
                    print(f"{now.strftime('%H:%M:%S')} Entry not filled by {entry_cutoff.strftime('%H:%M')}. Cancelling bracket.")
                    _cancel_trade_if_active(ib, parent_trade)
                    _cancel_trade_if_active(ib, target_trade)
                    _cancel_trade_if_active(ib, stop_trade)
                    entry_cancelled = True
                    return
                print(f"{now.strftime('%H:%M:%S')} Entry pending: {parent_trade.orderStatus.status}.")
                ib.sleep(settings.poll_seconds)
                continue

            if _is_filled(target_trade) or _is_filled(stop_trade):
                print(f"{now.strftime('%H:%M:%S')} Exit detected. Target status={target_trade.orderStatus.status}; stop status={stop_trade.orderStatus.status}.")
                return

            latest_price = _latest_price(ib, contract, ticker)
            if pd.notna(latest_price) and latest_price > 0:
                print(f"{now.strftime('%H:%M:%S')} Filled; latest {recommendation.symbol} price {latest_price:.2f}.")

            if (not stop_moved) and _breakeven_reached(recommendation, latest_price):
                breakeven_price = round(getattr(parent_trade.orderStatus, "avgFillPrice", None) or recommendation.entry, 2)
                print(f"{now.strftime('%H:%M:%S')} 6R reached. Moving stop to breakeven {breakeven_price:.2f}.")
                replacement = _replace_stop_order(ib, contract, recommendation, stop_trade, settings.account, order_cls, breakeven_price)
                stop_trade = replacement
                stop_moved = True

            if (not settings.off_hours_test) and now.time() >= flatten_time and not flattened:
                print(f"{now.strftime('%H:%M:%S')} Flatten time reached ({flatten_time.strftime('%H:%M')} ET). Cancelling exits and flattening position.")
                _cancel_trade_if_active(ib, target_trade)
                _cancel_trade_if_active(ib, stop_trade)
                _flatten_position(ib, contract, recommendation, settings.account, market_order_cls)
                flattened = True
                return

            ib.sleep(settings.poll_seconds)
    finally:
        ib.cancelMktData(contract)


def _replace_stop_order(ib, contract, recommendation: OrbRecommendation, stop_trade, account: str | None, order_cls, stop_price: float | None = None):
    _cancel_trade_if_active(ib, stop_trade)
    ib.sleep(1)
    replacement = order_cls()
    replacement.orderId = ib.client.getReqId()
    replacement.action = "SELL" if recommendation.direction > 0 else "BUY"
    replacement.orderType = "STP"
    replacement.totalQuantity = recommendation.shares
    target_stop = stop_price if stop_price is not None else round(recommendation.entry, 2)
    replacement.auxPrice = round(target_stop, 2)
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
    symbol = getattr(contract, "symbol", "")
    total = 0
    for position in ib.positions():
        pos_con_id = getattr(position.contract, "conId", None)
        pos_symbol = getattr(position.contract, "symbol", "")
        if (con_id and pos_con_id == con_id) or (symbol and pos_symbol == symbol):
            total += int(position.position)
    return total


def _latest_price(ib, contract, ticker=None) -> float:
    if ticker is not None:
        price = ticker.marketPrice()
        if price is not None and pd.notna(price) and price > 0:
            return float(price)
        if getattr(ticker, "last", None) and pd.notna(ticker.last) and ticker.last > 0:
            return float(ticker.last)
        if getattr(ticker, "close", None) and pd.notna(ticker.close) and ticker.close > 0:
            return float(ticker.close)
    else:
        ticker = ib.reqMktData(contract, "", False, False)
        ib.sleep(2)
        price = ticker.marketPrice()
        ib.cancelMktData(contract)
        if price is not None and pd.notna(price) and price > 0:
            return float(price)
    try:
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
    except Exception as exc:
        print(f"Warning: could not fetch latest price fallback: {exc}")
        return float("nan")


def _breakeven_reached(recommendation: OrbRecommendation, latest_price: float) -> bool:
    if pd.isna(latest_price) or latest_price <= 0:
        return False
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


def _order_price_str(order) -> str:
    parts = []
    lmt = getattr(order, "lmtPrice", None)
    aux = getattr(order, "auxPrice", None)
    if lmt is not None and lmt < 1e300 and lmt > 0:
        parts.append(f"lmt={lmt:.2f}")
    if aux is not None and aux < 1e300 and aux > 0:
        parts.append(f"aux={aux:.2f}")
    return " ".join(parts) if parts else "MKT"


def _print_live_order_warning(settings: IbkrOrbSettings) -> None:
    mode = "TRANSMIT ENABLED" if settings.transmit else "DRY RUN"
    port_hint = "paper" if settings.port in {7497, 4002} else "live"
    print("")
    print(f"IBKR mode: {mode}; connected port looks like {port_hint}.")
    if settings.off_hours_test:
        print("[TEST MODE] --off-hours-test is active: timing windows (09:45 wait, 10:30 cancel, 15:30 flatten) are relaxed for testing.")
    elif settings.manage_orders:
        print("After submission this process must remain running to manage 10:30 entry expiry, 6R stop move, and 15:30 flatten.")
    else:
        print("Order manager disabled. Breakeven stop moves and 15:30 flattening require manual handling.")
