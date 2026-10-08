from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import time
from typing import Any
import pandas as pd
import yaml


def backfill_from_ibkr(
    symbol: str = "TQQQ",
    start_date: str = "2025-06-03",
    end_date: str | None = None,
    host: str = "127.0.0.1",
    port: int = 7497,
    client_id: int = 49,
    output_file: str | Path = "data/intraday/TQQQ_1m_backfill.csv",
) -> Path:
    """
    Free method 1 (Recommended): Download 1-minute historical bars directly from IBKR
    for missing sessions between start_date and today.
    """
    from ib_insync import IB, Stock, util

    ib = IB()
    print(f"Connecting to IBKR at {host}:{port} (clientId={client_id})...")
    ib.connect(host, port, clientId=client_id, timeout=10)
    ib.reqMarketDataType(3)

    contract = Stock(symbol, "SMART", "USD")
    ib.qualifyContracts(contract)

    start_dt = pd.Timestamp(start_date)
    end_dt = pd.Timestamp(end_date) if end_date else pd.Timestamp.now()
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    trading_days = pd.date_range(start_dt, end_dt, freq="B")
    all_bars = []

    print(f"Backfilling {symbol} 1-minute bars across {len(trading_days)} business days...")

    for day in trading_days:
        date_str = day.strftime("%Y%m%d")
        end_time_str = f"{date_str} 16:00:00 US/Eastern"
        try:
            bars = ib.reqHistoricalData(
                contract,
                endDateTime=end_time_str,
                durationStr="1 D",
                barSizeSetting="1 min",
                whatToShow="TRADES",
                useRTH=True,
                formatDate=1,
            )
            if bars:
                df = util.df(bars)
                df["datetime"] = pd.to_datetime(df["date"])
                df = df[["datetime", "open", "high", "low", "close", "volume"]]
                all_bars.append(df)
                print(f"[{day.strftime('%Y-%m-%d')}] Retrieved {len(df)} 1-minute bars.")
            else:
                print(f"[{day.strftime('%Y-%m-%d')}] No bars returned (market holiday/weekend).")
            ib.sleep(0.5)  # Pace queries to respect IBKR pacing violations
        except Exception as e:
            print(f"[{day.strftime('%Y-%m-%d')}] Warning: {e}")

    ib.disconnect()

    if all_bars:
        combined = pd.concat(all_bars).drop_duplicates("datetime").sort_values("datetime").reset_index(drop=True)
        combined.to_csv(output_path, index=False)
        print(f"Successfully saved {len(combined)} bars to {output_path}")
        return output_path
    else:
        print("No bars retrieved.")
        return output_path


def backfill_from_yfinance_trailing30(
    symbol: str = "TQQQ",
    output_file: str | Path = "data/intraday/TQQQ_1m_recent30d.csv",
) -> Path:
    """
    Free method 2: Download trailing 30 days of 1-minute bars from Yahoo Finance.
    (Yahoo free tier caps 1m bars to 7 days per request, within a 30 calendar day window).
    """
    import yfinance as yf

    print(f"Downloading trailing 30 days of 1m bars for {symbol} via yfinance (in 7-day chunks)...")
    end_dt = pd.Timestamp.now()
    start_dt = end_dt - pd.Timedelta(days=29)

    chunks = []
    cursor = start_dt
    while cursor < end_dt:
        chunk_end = min(cursor + pd.Timedelta(days=7), end_dt)
        df = yf.download(
            symbol,
            start=cursor.date().isoformat(),
            end=chunk_end.date().isoformat(),
            interval="1m",
            auto_adjust=False,
            progress=False,
        )
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0].lower() for c in df.columns]
            else:
                df.columns = [str(c).lower() for c in df.columns]
            df = df.reset_index()
            df.columns = [str(c).lower() for c in df.columns]
            dt_col = "datetime" if "datetime" in df.columns else "date"
            df = df.rename(columns={dt_col: "datetime"})
            df["datetime"] = pd.to_datetime(df["datetime"])
            if df["datetime"].dt.tz is not None:
                df["datetime"] = df["datetime"].dt.tz_convert("America/New_York").dt.tz_localize(None)
            chunks.append(df[["datetime", "open", "high", "low", "close", "volume"]].dropna())
        cursor = chunk_end

    if not chunks:
        raise RuntimeError("No 1m data returned by yfinance.")

    out = pd.concat(chunks).drop_duplicates("datetime").sort_values("datetime").reset_index(drop=True)
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"Saved {len(out)} 1-minute bars ({out['datetime'].min()} to {out['datetime'].max()}) to {out_path}")
    return out_path
