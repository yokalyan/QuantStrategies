from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


@dataclass
class IntradayFill:
    datetime: pd.Timestamp
    symbol: str
    shares: int
    price: float
    reason: str


@dataclass
class OrbRecommendation:
    symbol: str
    session_date: pd.Timestamp
    opening_range_minutes: int
    direction: int
    or_open: float
    or_close: float
    or_high: float
    or_low: float
    or_mid: float
    or_range: float
    atr20: float
    ratio: float
    ratio_min: float
    ratio_max: float
    avg_opening_range: float
    max_range_valid: bool
    ratio_valid: bool
    capital: float
    risk_amount: float
    max_notional: float
    shares: int
    entry: float
    stop: float
    target: float
    breakeven_trigger: float
    profit_target_r: float
    breakeven_r: float
    risk_per_share: float
    atr_lookback: int = 20
    entry_cutoff_time: str = "10:30"
    flatten_time: str = "15:30"
    previous_close: float = float("nan")
    previous_close_direction: int = 0
    opening_range_direction: int = 0
    direction_mode: str = "opening_range"
    direction_agreement_valid: bool = True

    @property
    def can_trade(self) -> bool:
        return bool(self.direction != 0 and self.direction_agreement_valid and self.max_range_valid and self.ratio_valid and self.shares > 0)

    @property
    def order_side(self) -> str:
        return "BUY STOP" if self.direction > 0 else "SELL SHORT STOP"

    @property
    def exit_side(self) -> str:
        return "SELL" if self.direction > 0 else "BUY TO COVER"

    @property
    def direction_name(self) -> str:
        if self.direction > 0:
            return "bullish"
        if self.direction < 0:
            return "bearish"
        return "neutral"


def _flatten_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = [c[0].lower() for c in frame.columns]
    else:
        frame.columns = [str(c).lower() for c in frame.columns]
    return frame


def fetch_intraday(config_path: Path) -> None:
    import yfinance as yf

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    source = config["intraday_data"]
    symbol = config["symbol"]
    start = pd.Timestamp(source["start"])
    end = pd.Timestamp(source["end"])
    interval = source.get("interval", "1m")
    cache_dir = Path(source["cache_dir"])
    cache_dir.mkdir(parents=True, exist_ok=True)
    chunks = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + pd.Timedelta(days=7), end)
        frame = yf.download(symbol, start=cursor.date().isoformat(), end=chunk_end.date().isoformat(), interval=interval, auto_adjust=False, progress=False, threads=False)
        if not frame.empty:
            frame = _flatten_columns(frame.reset_index())
            dt_col = "datetime" if "datetime" in frame.columns else "date"
            frame = frame.rename(columns={dt_col: "datetime"})
            frame["datetime"] = pd.to_datetime(frame["datetime"])
            if frame["datetime"].dt.tz is not None:
                frame["datetime"] = frame["datetime"].dt.tz_convert("America/New_York").dt.tz_localize(None)
            chunks.append(frame[["datetime", "open", "high", "low", "close", "volume"]])
        cursor = chunk_end
    if not chunks:
        raise RuntimeError("No intraday data returned. Yahoo 1m data is usually limited to the last 30 days.")
    out = pd.concat(chunks).drop_duplicates("datetime").sort_values("datetime").reset_index(drop=True)
    out.to_parquet(cache_dir / f"{symbol}_{interval}.parquet", index=False)
    print(f"Fetched {len(out)} {interval} bars for {symbol}: {out['datetime'].min()} to {out['datetime'].max()}")


def run_intraday_orb(config_path: Path) -> Path:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    symbol = config["symbol"]
    source = config["intraday_data"]
    params = config["strategy"]["params"]
    if source.get("source_file"):
        frame = pd.read_csv(
            source["source_file"],
            names=["datetime", "open", "high", "low", "close", "volume"],
            parse_dates=["datetime"],
        )
        if source.get("start"):
            frame = frame[frame["datetime"] >= pd.Timestamp(source["start"])]
        if source.get("end"):
            frame = frame[frame["datetime"] < pd.Timestamp(source["end"])]
    else:
        frame = pd.read_parquet(Path(source["cache_dir"]) / f"{symbol}_{source.get('interval', '1m')}.parquet")
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["date"] = frame["datetime"].dt.normalize()
    regular_frame = frame[(frame["datetime"].dt.time >= pd.Timestamp("09:30").time()) & (frame["datetime"].dt.time <= pd.Timestamp("15:59").time())]
    daily = regular_frame.groupby("date").agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
    atr_lookback = int(params.get("atr_lookback", 20))
    entry_cutoff_str = str(params.get("entry_cutoff_time", "10:30"))
    flatten_str = str(params.get("flatten_time", "15:30"))
    entry_cutoff_time = pd.Timestamp(entry_cutoff_str).time()
    flatten_time = pd.Timestamp(flatten_str).time()
    atr_by_date = _daily_atr(daily, atr_lookback)
    cash = float(config["starting_capital"])
    qty = 0
    entry_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    initial_risk: float | None = None
    be_triggered = False
    fills: list[IntradayFill] = []
    equity_rows = []
    opening_ranges: list[float] = []
    risk_per_trade = float(params.get("risk_per_trade", 0.006))
    max_leverage = float(params.get("max_leverage", 4.0))
    profit_target_r = float(params.get("profit_target_r", 10.0))
    breakeven_r = float(params.get("breakeven_r", 6.0))
    opening_range_minutes = int(params.get("opening_range_minutes", 5))
    ratio_min = params.get("or_atr_min")
    ratio_max = params.get("or_atr_max")
    ratio_min = float(ratio_min) if ratio_min is not None else None
    ratio_max = float(ratio_max) if ratio_max is not None else None
    direction_mode = str(params.get("direction_mode", "opening_range"))
    for session, day in regular_frame.groupby("date", sort=True):
        day = day.set_index("datetime").between_time("09:30", "15:59").reset_index()
        if len(day) < opening_range_minutes + 5:
            continue
        first = day.iloc[:opening_range_minutes]
        or_high = float(first["high"].max())
        or_low = float(first["low"].min())
        or_mid = (or_high + or_low) / 2.0
        or_open = float(first.iloc[0]["open"])
        or_close = float(first.iloc[-1]["close"])
        opening_range_direction = 1 if or_close >= or_open else -1
        previous_close = _previous_regular_close(daily, pd.Timestamp(session))
        direction, direction_agreement_valid = _resolve_orb_direction(direction_mode, opening_range_direction, previous_close, or_close)
        current_range = or_high - or_low
        if len(opening_ranges) >= atr_lookback:
            avg_range = sum(opening_ranges[-atr_lookback:]) / min(atr_lookback, len(opening_ranges))
            range_valid = current_range <= 2.0 * avg_range
        else:
            range_valid = True
        atr_val = atr_by_date.get(session)
        if ratio_min is not None and ratio_max is not None:
            ratio = current_range / atr_val if pd.notna(atr_val) and atr_val > 0 else float("nan")
            atr_range_valid = ratio_min < ratio <= ratio_max
        else:
            atr_range_valid = True
        opening_ranges.append(current_range)
        traded_today = False
        for _, bar in day.iloc[opening_range_minutes:].iterrows():
            ts = bar["datetime"]
            price = float(bar["close"])
            equity = cash + qty * price
            if qty != 0:
                long = qty > 0
                assert entry_price is not None and stop_price is not None and target_price is not None and initial_risk is not None
                if not be_triggered:
                    if long and price >= entry_price + breakeven_r * initial_risk:
                        stop_price = entry_price
                        be_triggered = True
                    elif (not long) and price <= entry_price - breakeven_r * initial_risk:
                        stop_price = entry_price
                        be_triggered = True
                should_exit = (long and (price <= stop_price or price >= target_price)) or ((not long) and (price >= stop_price or price <= target_price))
                if ts.time() >= flatten_time:
                    should_exit = True
                if should_exit:
                    cash += qty * price
                    fills.append(IntradayFill(ts, symbol, -qty, price, "exit"))
                    qty = 0
                    traded_today = True
                    entry_price = stop_price = target_price = initial_risk = None
                    be_triggered = False
                    continue
            earliest_entry_time = (pd.Timestamp("09:30") + pd.Timedelta(minutes=opening_range_minutes)).time()
            if qty == 0 and (not traded_today) and direction_agreement_valid and range_valid and atr_range_valid and earliest_entry_time <= ts.time() < entry_cutoff_time:
                entry_direction = 0
                if direction > 0 and price > or_high:
                    entry_direction = 1
                elif direction < 0 and price < or_low:
                    entry_direction = -1
                if entry_direction:
                    risk_share = abs(price - or_mid)
                    if risk_share > 0:
                        equity = cash
                        size = int((equity * risk_per_trade) / risk_share)
                        size = min(size, int((equity * max_leverage) / price))
                        if size > 0:
                            qty = entry_direction * size
                            cash -= qty * price
                            entry_price = price
                            stop_price = or_mid
                            initial_risk = risk_share
                            target_price = price + entry_direction * profit_target_r * risk_share
                            be_triggered = False
                            traded_today = True
                            fills.append(IntradayFill(ts, symbol, qty, price, "entry"))
        last_price = float(day.iloc[-1]["close"])
        if qty != 0:
            ts = day.iloc[-1]["datetime"]
            cash += qty * last_price
            fills.append(IntradayFill(ts, symbol, -qty, last_price, "forced_eod"))
            qty = 0
        equity_rows.append({"date": pd.Timestamp(session), "equity": cash})

    equity = pd.DataFrame(equity_rows)
    trades = pd.DataFrame([fill.__dict__ for fill in fills])
    out_dir = Path(config["output_dir"]) / "midpoint_stop_orb_intraday"
    out_dir.mkdir(parents=True, exist_ok=True)
    equity.to_csv(out_dir / "equity_curve.csv", index=False)
    trades.to_csv(out_dir / "trades.csv", index=False)
    metrics = _metrics(equity, len(fills))
    (out_dir / "metrics.yaml").write_text(yaml.safe_dump(metrics, sort_keys=False), encoding="utf-8")
    report = [
        "# Midpoint Stop Opening Range Breakout Intraday Baseline",
        "",
        "## Metrics",
        *[f"- `{k}`: {v}" for k, v in metrics.items()],
        "",
        "## Caveats",
        "- This run uses the configured local one-minute bar file when `source_file` is present; otherwise it falls back to the limited yfinance intraday cache.",
        f"- Opening range uses the first {opening_range_minutes} regular-session minutes.",
        f"- Direction mode: {direction_mode}.",
        f"- Opening range / ATR20 filter: {ratio_min} < ratio <= {ratio_max}." if ratio_min is not None and ratio_max is not None else "- Opening range / ATR20 filter is disabled.",
        "- The local file covered the reported start/end dates in the metrics, which may be shorter than the source code's requested end date.",
        "- The backtest implements the pasted close-based stop/target checks.",
        "- No fees are applied, matching the pasted zero-fee model.",
    ]
    (out_dir / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(out_dir)
    return out_dir


def orb_signal(config_path: Path, session_date: str | None = None, capital: float | None = None) -> None:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    symbol = config["symbol"]
    source = config["intraday_data"]
    capital = float(capital if capital is not None else config.get("signal_capital", config["starting_capital"]))
    frame = _load_intraday_frame(source, symbol)
    recommendation = build_orb_recommendation(config, frame, session_date, capital)
    print_orb_recommendation(recommendation)


def build_orb_recommendation(config: dict[str, Any], frame: pd.DataFrame, session_date: str | pd.Timestamp | None = None, capital: float | None = None) -> OrbRecommendation:
    symbol = config["symbol"]
    params = config["strategy"]["params"]
    capital = float(capital if capital is not None else config.get("signal_capital", config["starting_capital"]))
    frame = frame.copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["date"] = frame["datetime"].dt.normalize()
    frame = frame.sort_values("datetime")
    target_date = pd.Timestamp(session_date).normalize() if session_date else frame["date"].max()
    regular = frame[(frame["datetime"].dt.time >= pd.Timestamp("09:30").time()) & (frame["datetime"].dt.time <= pd.Timestamp("15:59").time())]
    day = regular[regular["date"] == target_date]
    opening_range_minutes = int(params.get("opening_range_minutes", 5))
    if len(day) < opening_range_minutes:
        raise RuntimeError(f"Need at least {opening_range_minutes} regular-session minute bars for {target_date.date()}; found {len(day)}")

    atr_lookback = int(params.get("atr_lookback", 20))
    entry_cutoff_time = str(params.get("entry_cutoff_time", "10:30"))
    flatten_time = str(params.get("flatten_time", "15:30"))

    daily = regular.groupby("date").agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
    atr = _atr_before_session(daily, target_date, atr_lookback)
    previous_opening_ranges = _previous_opening_ranges(regular, target_date, atr_lookback, opening_range_minutes)
    first = day.iloc[:opening_range_minutes]
    or_high = float(first["high"].max())
    or_low = float(first["low"].min())
    or_mid = (or_high + or_low) / 2.0
    or_open = float(first.iloc[0]["open"])
    or_close = float(first.iloc[-1]["close"])
    or_range = or_high - or_low
    opening_range_direction = 1 if or_close >= or_open else -1
    previous_close = _previous_regular_close(daily, target_date)
    direction_mode = str(params.get("direction_mode", "opening_range"))
    direction, direction_agreement_valid = _resolve_orb_direction(direction_mode, opening_range_direction, previous_close, or_close)
    previous_close_direction = _direction_from_previous_close(previous_close, or_close)
    ratio = or_range / atr if atr and atr > 0 else float("nan")
    avg_opening_range = sum(previous_opening_ranges) / len(previous_opening_ranges) if previous_opening_ranges else float("nan")
    max_range_valid = True if not previous_opening_ranges else or_range <= 2.0 * avg_opening_range
    ratio_min = float(params.get("or_atr_min", 0.15))
    ratio_max = float(params.get("or_atr_max", 0.25))
    ratio_valid = ratio_min < ratio <= ratio_max
    entry_buffer = float(params.get("entry_buffer", 0.0))
    entry = or_high + entry_buffer if direction >= 0 else or_low - entry_buffer
    stop = or_mid
    risk_per_share = abs(entry - stop)
    risk_amount = capital * float(params.get("risk_per_trade", 0.006))
    max_notional = capital * float(params.get("max_leverage", 4.0))
    shares_by_risk = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
    shares_by_notional = int(max_notional / entry) if entry > 0 else 0
    shares = max(0, min(shares_by_risk, shares_by_notional))
    profit_target_r = float(params.get("profit_target_r", 10.0))
    breakeven_r = float(params.get("breakeven_r", 6.0))
    target = entry + direction * profit_target_r * risk_per_share if direction != 0 else entry
    breakeven_trigger = entry + direction * breakeven_r * risk_per_share if direction != 0 else entry

    return OrbRecommendation(
        symbol=symbol,
        session_date=target_date,
        opening_range_minutes=opening_range_minutes,
        direction=direction,
        or_open=or_open,
        or_close=or_close,
        or_high=or_high,
        or_low=or_low,
        or_mid=or_mid,
        or_range=or_range,
        previous_close=previous_close,
        previous_close_direction=previous_close_direction,
        opening_range_direction=opening_range_direction,
        direction_mode=direction_mode,
        direction_agreement_valid=direction_agreement_valid,
        atr20=atr,
        ratio=ratio,
        ratio_min=ratio_min,
        ratio_max=ratio_max,
        avg_opening_range=avg_opening_range,
        max_range_valid=max_range_valid,
        ratio_valid=ratio_valid,
        capital=capital,
        risk_amount=risk_amount,
        max_notional=max_notional,
        shares=shares,
        entry=entry,
        stop=stop,
        target=target,
        breakeven_trigger=breakeven_trigger,
        profit_target_r=profit_target_r,
        breakeven_r=breakeven_r,
        risk_per_share=risk_per_share,
        atr_lookback=atr_lookback,
        entry_cutoff_time=entry_cutoff_time,
        flatten_time=flatten_time,
    )


def print_orb_recommendation(recommendation: OrbRecommendation) -> None:
    print(f"ORB signal for {recommendation.symbol} on {recommendation.session_date.date()} ({recommendation.opening_range_minutes}-minute opening range)")
    opening_direction = "bullish" if recommendation.opening_range_direction > 0 else "bearish" if recommendation.opening_range_direction < 0 else "neutral"
    print(f"Opening candle: {opening_direction} ({recommendation.or_open:.2f} -> {recommendation.or_close:.2f})")
    if pd.notna(recommendation.previous_close):
        prev_dir = "bullish" if recommendation.previous_close_direction > 0 else "bearish" if recommendation.previous_close_direction < 0 else "flat"
        print(f"Prior close direction: {prev_dir} ({recommendation.previous_close:.2f} -> {recommendation.or_close:.2f}); mode: {recommendation.direction_mode}")
    print(f"Selected trade direction: {recommendation.direction_name}")
    print(f"Opening range high/low/mid: {recommendation.or_high:.2f} / {recommendation.or_low:.2f} / {recommendation.or_mid:.2f}")
    print(f"Opening range: {recommendation.or_range:.4f}")
    print(f"ATR{recommendation.atr_lookback} before session: {recommendation.atr20:.4f}")
    print(f"OR/ATR{recommendation.atr_lookback}: {recommendation.ratio:.4f} (required {recommendation.ratio_min:.2f} < ratio <= {recommendation.ratio_max:.2f})")
    if pd.notna(recommendation.avg_opening_range):
        print(f"{recommendation.atr_lookback}-session avg opening range: {recommendation.avg_opening_range:.4f}; 2x guard valid: {recommendation.max_range_valid}")
    print(f"Capital basis: ${recommendation.capital:,.2f}; risk budget: ${recommendation.risk_amount:,.2f}; max notional: ${recommendation.max_notional:,.2f}")
    print("")
    if not recommendation.can_trade:
        print("Recommendation: NO TRADE")
        if not recommendation.max_range_valid:
            print(f"- Opening range failed the 2x historical {recommendation.atr_lookback}-session opening-range guardrail.")
        if not recommendation.ratio_valid:
            print(f"- Opening range / ATR{recommendation.atr_lookback} is outside the tested {recommendation.ratio_min:.2f}-{recommendation.ratio_max:.2f} band.")
        if not recommendation.direction_agreement_valid:
            print("- Opening range direction does not agree with the prior-close direction filter.")
        if recommendation.shares <= 0:
            print("- Position size computed to zero shares.")
        return
    print("Recommendation: PREPARE CONTINGENT OR BRACKET ORDER")
    print(f"1. Entry: {recommendation.order_side} {recommendation.shares} {recommendation.symbol} @ {recommendation.entry:.2f}, valid until {recommendation.entry_cutoff_time} ET.")
    print(f"2. Initial stop: {recommendation.exit_side} {recommendation.shares} {recommendation.symbol} @ {recommendation.stop:.2f}.")
    print(f"3. Profit target: {recommendation.exit_side} {recommendation.shares} {recommendation.symbol} @ {recommendation.target:.2f} ({recommendation.profit_target_r:.1f}R).")
    print(f"4. Breakeven trigger: if price reaches {recommendation.breakeven_trigger:.2f} ({recommendation.breakeven_r:.1f}R), move stop to entry {recommendation.entry:.2f}.")
    print(f"5. Flatten any open position at {recommendation.flatten_time} ET.")
    print(f"Estimated risk/share: ${recommendation.risk_per_share:.2f}; estimated total risk: ${recommendation.risk_per_share * recommendation.shares:,.2f}; notional: ${recommendation.entry * recommendation.shares:,.2f}.")


def _load_intraday_frame(source: dict[str, Any], symbol: str) -> pd.DataFrame:
    if source.get("source_file"):
        frame = pd.read_csv(
            source["source_file"],
            names=["datetime", "open", "high", "low", "close", "volume"],
            parse_dates=["datetime"],
        )
        if source.get("start"):
            frame = frame[frame["datetime"] >= pd.Timestamp(source["start"])]
        if source.get("end"):
            frame = frame[frame["datetime"] < pd.Timestamp(source["end"])]
        return frame
    return pd.read_parquet(Path(source["cache_dir"]) / f"{symbol}_{source.get('interval', '1m')}.parquet")


def _atr_before_session(daily: pd.DataFrame, session_date: pd.Timestamp, lookback: int = 20) -> float:
    previous = daily[daily.index < session_date].copy()
    if len(previous) < lookback:
        return float("nan")
    return float(_true_range(previous).iloc[-lookback:].mean())


def _previous_regular_close(daily: pd.DataFrame, session_date: pd.Timestamp) -> float:
    previous = daily[daily.index < session_date]
    if previous.empty:
        return float("nan")
    return float(previous.iloc[-1]["close"])


def _direction_from_previous_close(previous_close: float, or_close: float) -> int:
    if pd.isna(previous_close):
        return 0
    if or_close > previous_close:
        return 1
    if or_close < previous_close:
        return -1
    return 0


def _resolve_orb_direction(direction_mode: str, opening_range_direction: int, previous_close: float, or_close: float) -> tuple[int, bool]:
    previous_close_direction = _direction_from_previous_close(previous_close, or_close)
    if direction_mode == "opening_range":
        return opening_range_direction, True
    if direction_mode == "previous_close":
        return previous_close_direction, previous_close_direction != 0
    if direction_mode == "previous_close_agreement":
        agreement = previous_close_direction != 0 and previous_close_direction == opening_range_direction
        return opening_range_direction if agreement else 0, agreement
    raise ValueError(f"Unsupported ORB direction_mode: {direction_mode}")


def _atr20_before_session(daily: pd.DataFrame, session_date: pd.Timestamp) -> float:
    return _atr_before_session(daily, session_date, 20)


def _daily_atr(daily: pd.DataFrame, lookback: int = 20) -> pd.Series:
    return _true_range(daily).rolling(lookback).mean().shift(1)


def _daily_atr20(daily: pd.DataFrame) -> pd.Series:
    return _daily_atr(daily, 20)


def _true_range(daily: pd.DataFrame) -> pd.Series:
    prev_close = daily["close"].shift(1)
    tr = pd.concat(
        [
            daily["high"] - daily["low"],
            (daily["high"] - prev_close).abs(),
            (daily["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _previous_opening_ranges(frame: pd.DataFrame, session_date: pd.Timestamp, count: int, opening_range_minutes: int = 5) -> list[float]:
    ranges: list[float] = []
    previous = frame[frame["date"] < session_date]
    for _, day in previous.groupby("date", sort=True):
        first = day.iloc[:opening_range_minutes]
        if len(first) >= opening_range_minutes:
            ranges.append(float(first["high"].max() - first["low"].min()))
    return ranges[-count:]


def _metrics(equity: pd.DataFrame, fill_count: int) -> dict[str, float | int | str]:
    if equity.empty:
        return {"total_return": "n/a", "number_of_fills": fill_count}
    curve = equity.set_index("date")["equity"].astype(float)
    daily = curve.pct_change().dropna()
    total_return = float(curve.iloc[-1] / curve.iloc[0] - 1.0) if len(curve) > 1 else 0.0
    years = max((curve.index.max() - curve.index.min()).days / 365.25, 1e-9)
    cagr = float((curve.iloc[-1] / curve.iloc[0]) ** (1.0 / years) - 1.0) if len(curve) > 1 else 0.0
    max_dd = float((curve / curve.cummax() - 1.0).min())
    sharpe = float(daily.mean() / daily.std(ddof=1) * (252 ** 0.5)) if len(daily) > 1 and daily.std(ddof=1) > 0 else 0.0
    return {
        "start": str(curve.index.min().date()),
        "end": str(curve.index.max().date()),
        "total_return": round(total_return, 6),
        "cagr": round(cagr, 6),
        "sharpe": round(sharpe, 6),
        "max_drawdown": round(max_dd, 6),
        "number_of_fills": fill_count,
    }
