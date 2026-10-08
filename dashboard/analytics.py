from __future__ import annotations

from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd


def compute_dashboard_analytics(results_dir: Path | str = "results/midpoint_stop_orb_intraday") -> dict[str, Any]:
    res_path = Path(results_dir)
    trades_path = res_path / "trades.csv"
    equity_path = res_path / "equity_curve.csv"

    if not trades_path.exists() or not equity_path.exists():
        return _empty_analytics()

    trades_df = pd.read_csv(trades_path)
    equity_df = pd.read_csv(equity_path)

    if trades_df.empty or equity_df.empty:
        return _empty_analytics()

    equity_df["date"] = pd.to_datetime(equity_df["date"])
    equity_df = equity_df.sort_values("date").reset_index(drop=True)

    curve = equity_df.set_index("date")["equity"].astype(float)
    start_capital = float(curve.iloc[0])
    current_equity = float(curve.iloc[-1])
    total_pnl = current_equity - start_capital
    total_return_pct = (current_equity / start_capital - 1.0) * 100.0

    # CAGR
    years = max((curve.index.max() - curve.index.min()).days / 365.25, 1e-4)
    cagr = ((current_equity / start_capital) ** (1.0 / years) - 1.0) * 100.0 if current_equity > 0 else 0.0

    # Drawdown
    cummax = curve.cummax()
    drawdown = (curve - cummax) / cummax
    max_drawdown = float(drawdown.min()) * 100.0

    # Sharpe ratio
    daily_returns = curve.pct_change().dropna()
    sharpe = float(daily_returns.mean() / daily_returns.std(ddof=1) * (252.0 ** 0.5)) if len(daily_returns) > 1 and daily_returns.std() > 0 else 0.0

    # Pair entry/exit trades to compute trade-level stats
    paired_trades = _pair_trades(trades_df)

    win_count = sum(1 for t in paired_trades if t["pnl"] > 0)
    loss_count = sum(1 for t in paired_trades if t["pnl"] < 0)
    total_trades = len(paired_trades)
    win_rate = (win_count / total_trades * 100.0) if total_trades > 0 else 0.0

    gross_profit = sum(t["pnl"] for t in paired_trades if t["pnl"] > 0)
    gross_loss = abs(sum(t["pnl"] for t in paired_trades if t["pnl"] < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

    # Downsampled equity curve for responsive charting (max ~350 points)
    equity_chart_data = _downsample_equity_curve(equity_df, max_points=350)

    # Monthly P&L
    monthly_pnl = _compute_monthly_pnl(paired_trades)

    # Weekly P&L (recent 52 weeks)
    weekly_pnl = _compute_weekly_pnl(paired_trades)

    # Day of Week P&L distribution
    day_of_week_stats = _compute_day_of_week_stats(paired_trades)

    # Recent trades (last 50)
    recent_trades = list(reversed(paired_trades[-50:]))

    return {
        "summary": {
            "start_date": str(curve.index.min().strftime("%Y-%m-%d")),
            "end_date": str(curve.index.max().strftime("%Y-%m-%d")),
            "start_capital": round(start_capital, 2),
            "current_equity": round(current_equity, 2),
            "total_pnl": round(total_pnl, 2),
            "total_return_pct": round(total_return_pct, 2),
            "cagr_pct": round(cagr, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "total_trades": total_trades,
            "win_rate_pct": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "win_count": win_count,
            "loss_count": loss_count,
        },
        "equity_curve": equity_chart_data,
        "monthly_pnl": monthly_pnl,
        "weekly_pnl": weekly_pnl,
        "day_of_week": day_of_week_stats,
        "recent_trades": recent_trades,
    }


def _pair_trades(trades_df: pd.DataFrame) -> list[dict[str, Any]]:
    trades = trades_df.copy()
    trades["datetime"] = pd.to_datetime(trades["datetime"])
    trades = trades.sort_values("datetime").reset_index(drop=True)

    paired: list[dict[str, Any]] = []
    current_entry: dict[str, Any] | None = None

    for _, row in trades.iterrows():
        reason = str(row["reason"])
        shares = int(row["shares"])
        price = float(row["price"])
        dt = row["datetime"]

        if "entry" in reason:
            current_entry = {
                "entry_time": dt.strftime("%Y-%m-%d %H:%M"),
                "date": dt.strftime("%Y-%m-%d"),
                "weekday": dt.strftime("%A"),
                "symbol": str(row["symbol"]),
                "shares": shares,
                "direction": "LONG" if shares > 0 else "SHORT",
                "entry_price": round(price, 2),
            }
        elif current_entry is not None:
            entry_shares = current_entry["shares"]
            exit_price = round(price, 2)
            # P&L = shares * (exit - entry) if long, or (-shares) * (entry - exit) if short
            # Since entry_shares is positive for long, negative for short:
            pnl = entry_shares * (exit_price - current_entry["entry_price"])
            pnl_pct = ((exit_price / current_entry["entry_price"] - 1.0) * (1 if entry_shares > 0 else -1)) * 100.0

            paired.append({
                "entry_time": current_entry["entry_time"],
                "exit_time": dt.strftime("%Y-%m-%d %H:%M"),
                "date": current_entry["date"],
                "weekday": current_entry["weekday"],
                "symbol": current_entry["symbol"],
                "direction": current_entry["direction"],
                "shares": abs(entry_shares),
                "entry_price": current_entry["entry_price"],
                "exit_price": exit_price,
                "reason": reason,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
            })
            current_entry = None

    return paired


def _downsample_equity_curve(df: pd.DataFrame, max_points: int = 350) -> list[dict[str, Any]]:
    n = len(df)
    if n <= max_points:
        step = 1
    else:
        step = int(np.ceil(n / max_points))

    sampled = df.iloc[::step].copy()
    if sampled.iloc[-1]["date"] != df.iloc[-1]["date"]:
        sampled = pd.concat([sampled, df.iloc[[-1]]]).drop_duplicates("date")

    return [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "equity": round(float(row["equity"]), 2),
        }
        for _, row in sampled.iterrows()
    ]


def _compute_monthly_pnl(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not trades:
        return []
    df = pd.DataFrame(trades)
    df["dt"] = pd.to_datetime(df["date"])
    df["month"] = df["dt"].dt.strftime("%Y-%m")

    grouped = df.groupby("month")["pnl"].sum().reset_index()
    # Sort chronologically and take last 36 months if very long
    grouped = grouped.sort_values("month")
    if len(grouped) > 48:
        grouped = grouped.tail(48)

    return [
        {
            "month": row["month"],
            "pnl": round(float(row["pnl"]), 2),
        }
        for _, row in grouped.iterrows()
    ]


def _compute_weekly_pnl(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not trades:
        return []
    df = pd.DataFrame(trades)
    df["dt"] = pd.to_datetime(df["date"])
    df["week"] = df["dt"].dt.strftime("%Y-W%W")

    grouped = df.groupby("week")["pnl"].sum().reset_index().sort_values("week")
    # Take last 52 weeks
    grouped = grouped.tail(52)

    return [
        {
            "week": row["week"],
            "pnl": round(float(row["pnl"]), 2),
        }
        for _, row in grouped.iterrows()
    ]


def _compute_day_of_week_stats(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    if not trades:
        return [{"day": d, "pnl": 0.0, "trades": 0, "win_rate": 0.0, "avg_pnl": 0.0} for d in weekdays]

    df = pd.DataFrame(trades)
    stats = []
    for day in weekdays:
        sub = df[df["weekday"] == day]
        if sub.empty:
            stats.append({"day": day, "pnl": 0.0, "trades": 0, "win_rate": 0.0, "avg_pnl": 0.0})
            continue

        pnl = float(sub["pnl"].sum())
        count = len(sub)
        wins = int((sub["pnl"] > 0).sum())
        win_rate = round(wins / count * 100.0, 1)
        avg_pnl = round(pnl / count, 2)
        stats.append({
            "day": day,
            "pnl": round(pnl, 2),
            "trades": count,
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
        })
    return stats


def _empty_analytics() -> dict[str, Any]:
    return {
        "summary": {
            "start_date": "N/A",
            "end_date": "N/A",
            "start_capital": 5000.0,
            "current_equity": 5000.0,
            "total_pnl": 0.0,
            "total_return_pct": 0.0,
            "cagr_pct": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown_pct": 0.0,
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "win_count": 0,
            "loss_count": 0,
        },
        "equity_curve": [],
        "monthly_pnl": [],
        "weekly_pnl": [],
        "day_of_week": [{"day": d, "pnl": 0.0, "trades": 0, "win_rate": 0.0, "avg_pnl": 0.0} for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]],
        "recent_trades": [],
    }
