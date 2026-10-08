from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime, time as dtime, timedelta
from pathlib import Path
import threading
import time
from typing import Any, Callable
from zoneinfo import ZoneInfo
import pandas as pd
import yaml

from backtest_engine.intraday_orb import OrbRecommendation, build_orb_recommendation
from backtest_engine.live_ibkr_orb import (
    EASTERN,
    _bars_to_frame,
    _breakeven_reached,
    _build_bracket_orders,
    _cancel_trade_if_active,
    _flatten_position,
    _is_filled,
    _is_terminal,
    _latest_price,
    _order_price_str,
    _parse_time_str,
    _poll_ibkr_bars,
    _replace_stop_order,
)


class StrategyRunner:
    def __init__(self, config_path: Path | str = "configs/midpoint_stop_orb_intraday.yaml"):
        self.config_path = Path(config_path)
        self.is_running = False
        self.stop_requested = False
        self.thread: threading.Thread | None = None
        self.ib: Any = None
        self.contract: Any = None
        self.trades: list[Any] = []
        self.account: str | None = None
        self.state: dict[str, Any] = self._default_state()
        self.logs: list[dict[str, str]] = []
        self.callbacks: list[Callable[[dict[str, Any]], None]] = []
        self.overrides: dict[str, Any] = {}

    def _default_state(self) -> dict[str, Any]:
        return {
            "status": "STOPPED",  # STOPPED, CONNECTING, POLLING, READY, IN_TRADE, FLATTENED, ERROR
            "symbol": "TQQQ",
            "ibkr_connected": False,
            "last_price": None,
            "recommendation": None,
            "orders": [],
            "position": {"shares": 0, "avg_cost": 0.0, "unrealized_pnl": 0.0},
            "mode": "DRY_RUN",
            "next_action": "Review settings, connect to IBKR, then run a dry check.",
            "schedule": {},
            "error": None,
            "last_updated": None,
        }

    def reset(self) -> bool:
        if self.is_running and self.thread and self.thread.is_alive():
            self.log("WARN", "Reset refused while the strategy worker is active. Stop or kill first.")
            self.state["next_action"] = "Stop or kill the active worker before resetting the session."
            self._notify({"type": "state", "data": self.state})
            return False
        self.state = self._default_state()
        self.trades = []
        self.contract = None
        self.account = None
        self.logs = []
        self._notify({"type": "state", "data": self.state})
        self._notify({"type": "clear_logs", "data": {}})
        return True

    def register_callback(self, cb: Callable[[dict[str, Any]], None]) -> None:
        if cb not in self.callbacks:
            self.callbacks.append(cb)

    def unregister_callback(self, cb: Callable[[dict[str, Any]], None]) -> None:
        if cb in self.callbacks:
            self.callbacks.remove(cb)

    def log(self, level: str, message: str) -> None:
        entry = {
            "time": datetime.now(EASTERN).strftime("%H:%M:%S"),
            "level": level,
            "message": message,
        }
        self.logs.append(entry)
        if len(self.logs) > 500:
            self.logs = self.logs[-500:]
        self._notify({"type": "log", "data": entry})

    def _notify(self, payload: dict[str, Any]) -> None:
        for cb in list(self.callbacks):
            try:
                cb(payload)
            except Exception:
                pass

    def get_status(self) -> dict[str, Any]:
        return {
            "is_running": self.is_running,
            "state": self.state,
            "logs": self.logs[-100:],
        }

    def start(self, overrides: dict[str, Any] | None = None) -> bool:
        if self.thread and self.thread.is_alive():
            if not self.stop_requested:
                return False
            # Wait for dying thread to terminate cleanly
            self.thread.join(timeout=3.0)
            if self.thread.is_alive():
                self.log("WARN", "Previous worker thread is still finalizing, please retry in 1 second...")
                return False

        self.stop_requested = False
        self.is_running = True
        self.overrides = overrides or {}
        self.state["status"] = "STARTING"
        self.state["error"] = None
        self.state["mode"] = "TRANSMIT" if bool(self.overrides.get("transmit", False)) else "DRY_RUN"
        self.state["next_action"] = "Connecting to IBKR."
        self.state["last_updated"] = datetime.now(EASTERN).strftime("%Y-%m-%d %H:%M:%S")
        self._notify({"type": "state", "data": self.state})

        self.thread = threading.Thread(
            target=self._run_loop,
            args=(self.overrides,),
            daemon=True,
        )
        self.thread.start()
        return True

    def stop(self) -> bool:
        self.stop_requested = True
        ib = self.ib
        if ib:
            try:
                ib.disconnect()
            except Exception:
                pass
        self.state["status"] = "STOPPING"
        self.state["next_action"] = "Graceful stop requested. Cleaning up orders and socket..."
        self.state["last_updated"] = datetime.now(EASTERN).strftime("%Y-%m-%d %H:%M:%S")
        self.log("WARN", "Graceful stop requested by user.")
        self._notify({"type": "state", "data": self.state})
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        self.is_running = False
        self.state["status"] = "STOPPED"
        self.state["next_action"] = "Strategy execution stopped."
        self._notify({"type": "state", "data": self.state})
        return True

    def kill(self) -> bool:
        self.stop_requested = True
        ib = self.ib
        if ib:
            try:
                ib.disconnect()
            except Exception:
                pass
            try:
                if hasattr(ib, "client") and ib.client:
                    ib.client.disconnect()
            except Exception:
                pass
        self.ib = None
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        self.is_running = False
        self.state["status"] = "KILLED"
        self.state["ibkr_connected"] = False
        self.state["next_action"] = "Connection forcibly closed."
        self.state["last_updated"] = datetime.now(EASTERN).strftime("%Y-%m-%d %H:%M:%S")
        self.log("ERROR", "Emergency kill executed. Thread terminated and connection closed.")
        self._notify({"type": "state", "data": self.state})
        return True

    def restart(self, overrides: dict[str, Any] | None = None) -> bool:
        if self.is_running and self.thread and self.thread.is_alive():
            self.kill()
            self.thread.join(timeout=5)
        self.is_running = False
        self.stop_requested = False
        self.state = self._default_state()
        self.trades = []
        self.contract = None
        self.account = None
        self.logs = []
        self.log("INFO", "Restarting strategy worker with current dashboard settings.")
        return self.start(overrides or {})

    def flatten_now(self) -> bool:
        from ib_insync import IB, MarketOrder, Stock

        # 1. Active session flatten
        if self.ib and self.ib.isConnected() and self.contract:
            try:
                for t in self.trades:
                    _cancel_trade_if_active(self.ib, t)
                rec = None
                try:
                    rec = self._recommendation_obj()
                except Exception:
                    pass
                _flatten_position(self.ib, self.contract, rec, self.account, MarketOrder)
                self.state["status"] = "FLATTEN_REQUESTED"
                self.state["next_action"] = "Flatten order submitted. Verify final position in IBKR."
                self.log("WARN", "Manual flatten submitted via active session.")
                self._notify({"type": "state", "data": self.state})
                return True
            except Exception as exc:
                self.state["error"] = str(exc)
                self.log("ERROR", f"Manual flatten failed: {exc}")
                self._notify({"type": "state", "data": self.state})
                return False

        overrides = getattr(self, "overrides", {}) or {}
        host = overrides.get("host", "127.0.0.1")
        port = int(overrides.get("port", 7497))
        account = overrides.get("account")
        symbol = self.state.get("symbol", "TQQQ")

        self.log("WARN", f"Executing direct emergency flatten on {host}:{port} for {symbol}...")
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        ib = IB()
        try:
            ib.connect(host, port, clientId=96, timeout=4)
            contract = Stock(symbol, "SMART", "USD")
            ib.qualifyContracts(contract)

            # Cancel open orders for symbol
            for trade in ib.openTrades():
                if trade.contract.symbol == symbol and not trade.isDone():
                    ib.cancelOrder(trade.order)

            ib.reqPositions()
            ib.sleep(0.5)
            pos_size = 0
            for pos in ib.positions():
                if pos.contract.symbol == symbol:
                    pos_size += int(pos.position)
            if pos_size != 0:
                action = "SELL" if pos_size > 0 else "BUY"
                mkt_order = MarketOrder(action, abs(pos_size))
                mkt_order.tif = "DAY"
                if account:
                    mkt_order.account = account
                ib.placeOrder(contract, mkt_order)
                ib.sleep(0.5)
                self.log("WARN", f"Submitted market {action} {abs(pos_size)} {symbol} to flatten position.")
            else:
                self.log("INFO", f"No open position found for {symbol} to flatten.")

            ib.disconnect()
            self.state["status"] = "FLATTENED"
            self.state["next_action"] = "Emergency flatten executed. Verify position in IBKR."
            self.log("SUCCESS", f"Emergency flatten completed on IBKR for {symbol}.")
            self._notify({"type": "state", "data": self.state})
            return True
        except Exception as exc:
            try:
                ib.disconnect()
            except Exception:
                pass
            self.log("ERROR", f"Emergency flatten failed: {exc}")
            return False

    def _recommendation_obj(self) -> OrbRecommendation:
        rec = self.state.get("recommendation") or {}
        if not rec:
            raise RuntimeError("No recommendation is available for flatten context.")
        data = {k: v for k, v in rec.items() if k in OrbRecommendation.__dataclass_fields__}
        data["session_date"] = pd.Timestamp(data["session_date"])
        return OrbRecommendation(**data)

    def _run_loop(self, overrides: dict[str, Any]) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ib = None
        try:
            from ib_insync import IB, LimitOrder, MarketOrder, Order, Stock
        except ImportError as exc:
            self.state["status"] = "ERROR"
            self.state["error"] = "ib_insync is not installed"
            self.log("ERROR", "ib_insync is not installed. Run pip install '.[live]'")
            self.is_running = False
            return

        try:
            config = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
            params = config["strategy"]["params"]

            # Apply UI overrides
            if "opening_range_minutes" in overrides:
                params["opening_range_minutes"] = int(overrides["opening_range_minutes"])
            if "or_atr_min" in overrides:
                params["or_atr_min"] = float(overrides["or_atr_min"])
            if "or_atr_max" in overrides:
                params["or_atr_max"] = float(overrides["or_atr_max"])
            if "capital" in overrides:
                config["signal_capital"] = float(overrides["capital"])
            if "atr_lookback" in overrides:
                params["atr_lookback"] = int(overrides["atr_lookback"])
            if "risk_per_trade" in overrides:
                params["risk_per_trade"] = float(overrides["risk_per_trade"])
            if "profit_target_r" in overrides:
                params["profit_target_r"] = float(overrides["profit_target_r"])
            if "breakeven_r" in overrides:
                params["breakeven_r"] = float(overrides["breakeven_r"])

            symbol = config.get("symbol", "TQQQ")
            self.state["symbol"] = symbol
            capital = float(config.get("signal_capital", 5000.0))
            opening_range_minutes = int(params.get("opening_range_minutes", 15))
            entry_cutoff = _parse_time_str(str(params.get("entry_cutoff_time", "10:30")), dtime(10, 30))
            flatten_time = _parse_time_str(str(params.get("flatten_time", "15:30")), dtime(15, 30))
            poll_seconds = int(overrides.get("poll_seconds", 60))
            host = overrides.get("host", "127.0.0.1")
            port = int(overrides.get("port", 7497))
            client_id = int(overrides.get("client_id", 45))
            off_hours_test = bool(overrides.get("off_hours_test", False))
            account = overrides.get("account") or None
            transmit = bool(overrides.get("transmit", False))
            self.account = account

            # Safety check
            if off_hours_test:
                is_paper_port = port in {7497, 4002}
                is_paper_account = bool(account and (account.upper().startswith("DU") or account.upper().startswith("DF")))
                if not is_paper_port and not is_paper_account:
                    raise RuntimeError(f"SAFETY BLOCK: Off-Hours Testing mode is strictly forbidden on Live Port {port} or Live accounts! Use Paper Port 7497/4002 or disable Off-Hours Test.")

            self.state["status"] = "CONNECTING"
            self.state["ibkr_connected"] = False
            self.state["mode"] = "TRANSMIT" if transmit else "DRY_RUN"
            self.state["next_action"] = "Connecting to IBKR socket."
            self.state["schedule"] = {
                "opening_range": f"09:30 + {opening_range_minutes}m",
                "entry_cutoff": entry_cutoff.strftime("%H:%M"),
                "flatten": flatten_time.strftime("%H:%M"),
                "poll_seconds": poll_seconds,
                "off_hours_test": off_hours_test,
            }
            self.log("INFO", f"Connecting to IBKR at {host}:{port} clientId={client_id}...")
            self._notify({"type": "state", "data": self.state})

            connected = False
            last_conn_err = None
            base_client_id = client_id
            curr_client_id = base_client_id
            max_connect_attempts = int(overrides.get("connect_attempts", 3))

            for attempt in range(1, max_connect_attempts + 1):
                if self.stop_requested:
                    return

                # Fresh IB instance per attempt prevents reusing closed or broken sockets
                ib = IB()
                self.ib = ib

                try:
                    self.log("INFO", f"Connecting to IBKR at {host}:{port} clientId={curr_client_id} (attempt {attempt}/{max_connect_attempts})...")
                    ib.connect(host, port, clientId=curr_client_id, timeout=4)
                    connected = True
                    client_id = curr_client_id
                    break
                except Exception as e:
                    last_conn_err = e
                    # Unconditionally disconnect broken instance so the TCP socket is never left hanging
                    try:
                        ib.disconnect()
                    except Exception:
                        pass
                    self.ib = None

                    err_str = str(e).lower()
                    if "client id is already in use" in err_str or "326" in err_str or "peer closed" in err_str:
                        self.log("WARN", f"Client ID {curr_client_id} in use, auto-switching to clientId={curr_client_id + 1}...")
                        curr_client_id += 1
                        for _ in range(5):
                            if self.stop_requested:
                                return
                            time.sleep(0.1)
                        continue
                    if isinstance(e, (ConnectionRefusedError, TimeoutError, OSError)):
                        self.state["next_action"] = (
                            f"IBKR socket not accepting connections on {host}:{port}. "
                            f"Retrying ({attempt}/{max_connect_attempts})... Click Cancel to abort."
                        )
                        self.log("WARN", f"IBKR socket not ready on {host}:{port} (attempt {attempt}/{max_connect_attempts})...")
                        self._notify({"type": "state", "data": self.state})
                        curr_client_id += 1
                        for _ in range(12):
                            if self.stop_requested:
                                return
                            time.sleep(0.1)
                        continue
                    break

            if not connected:
                if isinstance(last_conn_err, (ConnectionRefusedError, OSError)):
                    raise ConnectionError(
                        f"IBKR port {port} is closed. TWS or IB Gateway is not running or API access is disabled on {host}:{port}. "
                        f"In TWS, open File -> Global Configuration -> API -> Settings -> check 'Enable ActiveX and Socket Clients'."
                    ) from last_conn_err
                elif isinstance(last_conn_err, TimeoutError):
                    raise TimeoutError(
                        f"Timed out connecting to IBKR at {host}:{port}. "
                        f"Check that TWS/Gateway API settings have 'Enable ActiveX and Socket Clients' checked."
                    ) from last_conn_err
                else:
                    raise ConnectionError(f"Unable to connect to IBKR at {host}:{port}: {last_conn_err}") from last_conn_err

            self.state["ibkr_connected"] = True
            ib.reqMarketDataType(3)  # Enable delayed market data fallback

            contract = Stock(symbol, "SMART", "USD")
            ib.qualifyContracts(contract)
            self.contract = contract

            self.state["status"] = "POLLING"
            self.state["next_action"] = "Waiting for enough minute bars to compute the signal."
            self.log("INFO", f"Connected to IBKR! Qualified {symbol} contract. Polling minute bars (OR={opening_range_minutes}m)...")
            self._notify({"type": "state", "data": self.state})

            frame = _poll_ibkr_bars(ib, contract, opening_range_minutes, poll_seconds, off_hours_test=off_hours_test)
            rec = build_orb_recommendation(config, frame, None, capital)
            rec_dict = asdict(rec)
            rec_dict["session_date"] = str(rec.session_date.date())
            rec_dict["can_trade"] = bool(rec.can_trade)
            rec_dict["order_side"] = str(rec.order_side)
            rec_dict["exit_side"] = str(rec.exit_side)
            rec_dict["direction_name"] = str(rec.direction_name)
            self.state["recommendation"] = rec_dict

            self.log("INFO", f"Signal computed: {rec.direction_name.upper()} | OR: [{rec.or_low:.2f} - {rec.or_high:.2f}] Mid: {rec.or_mid:.2f}")
            self.log("INFO", f"ATR: {rec.atr20:.4f} | Ratio: {rec.ratio:.4f} (Band: {rec.ratio_min}-{rec.ratio_max})")

            if not rec.can_trade:
                self.state["status"] = "STAND_DOWN"
                self.state["next_action"] = "No trade today. Review signal diagnostics and stand down."
                self.log("WARN", "Strategy decision: STAND DOWN (no trade today based on filters).")
                self._notify({"type": "state", "data": self.state})
                return

            self.log("SUCCESS", f"Trade Qualified! Direction: {rec.order_side} {rec.shares} {symbol} @ {rec.entry:.2f} | Stop: {rec.stop:.2f} | Target: {rec.target:.2f}")

            # Build orders
            orders = _build_bracket_orders(ib, rec, account, Order, LimitOrder)
            parent, target, stop = orders

            order_list_repr = [
                {"action": parent.action, "type": parent.orderType, "qty": parent.totalQuantity, "price": rec.entry, "role": "Parent Entry STP", "status": "Submitting"},
                {"action": target.action, "type": target.orderType, "qty": target.totalQuantity, "price": rec.target, "role": "Take Profit LMT", "status": "Submitting"},
                {"action": stop.action, "type": stop.orderType, "qty": stop.totalQuantity, "price": rec.stop, "role": "Stop Loss STP", "status": "Submitting"},
            ]
            self.state["orders"] = order_list_repr
            if not transmit:
                self.state["status"] = "READY_DRY_RUN"
                self.state["next_action"] = "Dry run complete. Review the bracket. Enable transmit when ready to place orders."
                self.log("INFO", "Dry-run mode: bracket prepared but not submitted to IBKR.")
                self._notify({"type": "state", "data": self.state})
                return

            self.state["status"] = "BRACKET_SUBMITTED"
            self.state["next_action"] = "Bracket submitted. Monitoring entry until cutoff."
            self._notify({"type": "state", "data": self.state})

            trades = []
            for order in orders:
                trades.append(ib.placeOrder(contract, order))
                ib.sleep(0.25)
            self.trades = trades

            parent_trade, target_trade, stop_trade = trades
            self.log("SUCCESS", "Bracket order placed in IBKR. Active trade manager engaged.")

            # Management loop
            ticker = ib.reqMktData(contract, "", False, False)
            stop_moved = False
            entry_cancelled = False
            flattened = False

            while not self.stop_requested:
                now = datetime.now(EASTERN)
                ib.reqOpenOrders()
                ib.sleep(0.25)

                # Update order representations
                for idx, t in enumerate(trades):
                    if idx < len(order_list_repr):
                        order_list_repr[idx]["status"] = t.orderStatus.status
                self.state["orders"] = order_list_repr

                # Read price
                price = _latest_price(ib, contract, ticker)
                if pd.notna(price) and price > 0:
                    self.state["last_price"] = round(price, 2)

                # Check if parent is terminal and not filled
                if _is_terminal(parent_trade) and not _is_filled(parent_trade) and not entry_cancelled:
                    self.state["status"] = "TERMINAL"
                    self.log("WARN", f"Parent order became terminal ({parent_trade.orderStatus.status}). Manager stopping.")
                    break

                # Pending entry check
                if not _is_filled(parent_trade):
                    self.state["status"] = "PENDING_ENTRY"
                    self.state["next_action"] = f"Entry pending. Will cancel at {entry_cutoff.strftime('%H:%M')} ET if unfilled."
                    if (not off_hours_test) and now.time() >= entry_cutoff:
                        self.log("WARN", f"Entry window cutoff ({entry_cutoff.strftime('%H:%M')} ET) reached. Cancelling bracket.")
                        _cancel_trade_if_active(ib, parent_trade)
                        _cancel_trade_if_active(ib, target_trade)
                        _cancel_trade_if_active(ib, stop_trade)
                        entry_cancelled = True
                        self.state["status"] = "CANCELLED"
                        self.state["next_action"] = "Entry window expired. Bracket cancelled."
                        break
                    self._notify({"type": "state", "data": self.state})
                    ib.sleep(poll_seconds)
                    continue

                # Trade is active
                self.state["status"] = "IN_TRADE"
                self.state["next_action"] = "Position is active. Monitoring 6R breakeven trigger and flatten time."
                fill_price = float(parent_trade.orderStatus.avgFillPrice or rec.entry)
                current_pnl = 0.0
                if self.state["last_price"]:
                    mult = 1 if rec.direction > 0 else -1
                    current_pnl = rec.shares * (self.state["last_price"] - fill_price) * mult

                self.state["position"] = {
                    "shares": rec.shares * rec.direction,
                    "avg_cost": round(fill_price, 2),
                    "unrealized_pnl": round(current_pnl, 2),
                }

                # Check if exit filled
                if _is_filled(target_trade):
                    self.log("SUCCESS", f"TARGET HIT! Take profit limit order filled at {target_trade.orderStatus.avgFillPrice:.2f} (+10R).")
                    self.state["status"] = "EXIT_PROFIT"
                    self.state["next_action"] = "Target filled. Verify position is flat in IBKR."
                    break
                if _is_filled(stop_trade):
                    self.log("WARN", f"STOP HIT! Stop loss order filled at {stop_trade.orderStatus.avgFillPrice:.2f}.")
                    self.state["status"] = "EXIT_STOP"
                    self.state["next_action"] = "Stop filled. Verify position is flat in IBKR."
                    break

                # 6R Breakeven Trigger
                if (not stop_moved) and self.state["last_price"] and _breakeven_reached(rec, self.state["last_price"]):
                    breakeven_price = round(fill_price, 2)
                    self.log("SUCCESS", f"+6R Reached! Moving stop loss to breakeven ({breakeven_price:.2f}).")
                    replacement = _replace_stop_order(ib, contract, rec, stop_trade, account, Order, breakeven_price)
                    stop_trade = replacement
                    self.trades = [parent_trade, target_trade, stop_trade]
                    stop_moved = True
                    self.state["next_action"] = "Breakeven stop is active. Continue monitoring target/stop/flatten."

                # 15:30 EOD Flatten
                if (not off_hours_test) and now.time() >= flatten_time and not flattened:
                    self.log("INFO", f"EOD Flatten time ({flatten_time.strftime('%H:%M')} ET) reached. Flattening position at market.")
                    _cancel_trade_if_active(ib, target_trade)
                    _cancel_trade_if_active(ib, stop_trade)
                    _flatten_position(ib, contract, rec, account, MarketOrder)
                    flattened = True
                    self.state["status"] = "FLATTENED"
                    self.state["next_action"] = "Flatten submitted. Verify final position in IBKR."
                    break

                self._notify({"type": "state", "data": self.state})
                ib.sleep(poll_seconds)

        except Exception as exc:
            self.state["status"] = "ERROR"
            self.state["error"] = str(exc)
            self.state["next_action"] = "Resolve the error, verify IBKR state, then restart if safe."
            self.log("ERROR", f"Strategy error: {exc}")
        finally:
            if ib:
                try:
                    ib.disconnect()
                except Exception:
                    pass
                try:
                    if hasattr(ib, "client") and ib.client:
                        ib.client.disconnect()
                except Exception:
                    pass
            if self.ib is ib:
                self.ib = None
            self.state["ibkr_connected"] = False
            self.is_running = False
            if self.state["status"] not in {"ERROR", "STAND_DOWN", "FLATTENED", "READY_DRY_RUN", "KILLED", "EXIT_PROFIT", "EXIT_STOP", "CANCELLED"}:
                self.state["status"] = "STOPPED"
                self.state["next_action"] = "Execution cycle stopped."
            self.trades = []
            self.contract = None
            self.account = None
            self.log("INFO", "Strategy execution cycle finished.")
            self._notify({"type": "state", "data": self.state})


# Global singleton instance
runner = StrategyRunner()
