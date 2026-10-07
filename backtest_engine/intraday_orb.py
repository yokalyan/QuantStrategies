from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml


@dataclass
class IntradayFill:
    datetime: pd.Timestamp
    symbol: str
    shares: int
    price: float
    reason: str


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
    frame["date"] = frame["datetime"].dt.date
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
    for session, day in frame.groupby("date", sort=True):
        day = day.set_index("datetime").between_time("09:30", "15:59").reset_index()
        if len(day) < 10:
            continue
        first = day.iloc[:5]
        or_high = float(first["high"].max())
        or_low = float(first["low"].min())
        or_mid = (or_high + or_low) / 2.0
        or_dir = 1 if float(first.iloc[-1]["close"]) >= float(first.iloc[0]["open"]) else -1
        current_range = or_high - or_low
        opening_ranges.append(current_range)
        if len(opening_ranges) >= 20:
            avg_range = sum(opening_ranges[-20:]) / min(20, len(opening_ranges))
            range_valid = current_range <= 2.0 * avg_range
        else:
            range_valid = True
        traded_today = False
        for _, bar in day.iloc[5:].iterrows():
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
                if ts.time() >= pd.Timestamp("15:30").time():
                    should_exit = True
                if should_exit:
                    cash += qty * price
                    fills.append(IntradayFill(ts, symbol, -qty, price, "exit"))
                    qty = 0
                    traded_today = True
                    entry_price = stop_price = target_price = initial_risk = None
                    be_triggered = False
                    continue
            if qty == 0 and (not traded_today) and range_valid and pd.Timestamp("09:35").time() <= ts.time() < pd.Timestamp("10:30").time():
                direction = 0
                if or_dir > 0 and price > or_high:
                    direction = 1
                elif or_dir < 0 and price < or_low:
                    direction = -1
                if direction:
                    risk_share = abs(price - or_mid)
                    if risk_share > 0:
                        equity = cash
                        size = int((equity * risk_per_trade) / risk_share)
                        size = min(size, int((equity * max_leverage) / price))
                        if size > 0:
                            qty = direction * size
                            cash -= qty * price
                            entry_price = price
                            stop_price = or_mid
                            initial_risk = risk_share
                            target_price = price + direction * profit_target_r * risk_share
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
        "- The local file covered the reported start/end dates in the metrics, which may be shorter than the source code's requested end date.",
        "- The backtest implements the pasted close-based stop/target checks.",
        "- No fees are applied, matching the pasted zero-fee model.",
    ]
    (out_dir / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(out_dir)
    return out_dir


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
