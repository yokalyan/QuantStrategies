from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import platform
from pathlib import Path

import pandas as pd
import yaml

from backtest_engine.analytics import compute_metrics
from backtest_engine.data import DataPortal, FredProvider, YFinanceProvider
from backtest_engine.execution import CostModel
from backtest_engine.portfolio import Portfolio
from backtest_engine.reporting import write_report
from backtest_engine.strategy import MarketDataView, get_strategy
from backtest_engine.validation import scan_for_forbidden_terms
from backtest_engine.intraday_orb import fetch_intraday, orb_signal, run_intraday_orb


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def import_strategy(module_name: str) -> None:
    importlib.import_module(module_name)


def all_symbols(config: dict) -> list[str]:
    symbols = list(dict.fromkeys(config["universe"]["symbols"] + config.get("factors", []) + [config["benchmark"]]))
    return symbols


def asset_symbols(config: dict) -> list[str]:
    return list(dict.fromkeys(config["universe"]["symbols"] + [config["benchmark"]]))


def fetch(config_path: Path) -> None:
    config = load_config(config_path)
    cache_dir = Path(config["data_source"]["cache_dir"])
    factors = config.get("factors", [])
    yf_symbols = [symbol for symbol in asset_symbols(config) if symbol not in factors]
    if yf_symbols:
        YFinanceProvider(cache_dir).fetch(yf_symbols, config["start"], config["end"])
    if factors:
        FredProvider(cache_dir).fetch(factors, config["start"], config["end"])
    print(f"Fetched {len(yf_symbols)} market symbols and {len(factors)} factors into {cache_dir}")


def session_dates(bars: dict[str, pd.DataFrame], benchmark: str) -> list[pd.Timestamp]:
    return list(bars[benchmark]["date"])


def price_map(bars: dict[str, pd.DataFrame], date: pd.Timestamp, field: str) -> dict[str, float]:
    prices = {}
    for symbol, frame in bars.items():
        if "date" in frame.columns:
            row = frame[frame["date"] == date]
            if not row.empty:
                prices[symbol] = float(row.iloc[0][field])
        elif date in frame.index:
            prices[symbol] = float(frame.at[date, field])
    return prices


def benchmark_curve(bars: pd.DataFrame, starting_capital: float) -> pd.DataFrame:
    first = float(bars.iloc[0]["open"])
    shares = starting_capital / first
    return pd.DataFrame({"date": bars["date"], "equity": shares * bars["close"]})


def run(config_path: Path) -> Path:
    config = load_config(config_path)
    import_strategy(config["strategy"]["module"])
    cache_dir = Path(config["data_source"]["cache_dir"])
    bars = DataPortal(cache_dir).load(all_symbols(config), config["start"], config["end"])
    dates = session_dates(bars, config["benchmark"])
    bars = {symbol: frame.set_index("date", drop=False) for symbol, frame in bars.items()}
    portfolio = Portfolio(float(config["starting_capital"]))
    cost_model = CostModel(**config["cost_model"])
    strategy = get_strategy(config["strategy"]["name"], config["strategy"].get("params", {}))
    pending_targets: dict[str, float] | None = None
    equity_rows = []
    positions_rows = []
    rebalance_config = config.get("rebalance", {"frequency": "weekly", "weekday": 0})
    rebalance_frequency = rebalance_config.get("frequency", "weekly")
    rebalance_weekday = int(rebalance_config.get("weekday", 0))
    last_rebalance_week = None
    for i, date in enumerate(dates):
        open_prices = price_map(bars, date, "open")
        close_prices = price_map(bars, date, "close")
        if pending_targets is not None:
            portfolio.rebalance_to_targets(date, open_prices, pending_targets, cost_model, bool(config.get("whole_shares", True)))
            pending_targets = None
        equity_rows.append({"date": date, "equity": portfolio.value(close_prices), "cash": portfolio.cash})
        for symbol, shares in portfolio.positions.items():
            positions_rows.append({"date": date, "symbol": symbol, "shares": shares, "close": close_prices.get(symbol)})
        iso = date.isocalendar()
        if rebalance_frequency == "daily":
            should_rebalance = True
        elif rebalance_frequency == "weekly":
            should_rebalance = date.weekday() >= rebalance_weekday and last_rebalance_week != (iso.year, iso.week)
        elif rebalance_frequency == "monthly":
            previous_date = dates[i - 1] if i else None
            should_rebalance = previous_date is None or date.month != previous_date.month
        else:
            raise ValueError(f"Unsupported rebalance frequency: {rebalance_frequency}")
        if should_rebalance and i < len(dates) - 1:
            view = MarketDataView(bars, date)
            pending_targets = strategy.target_weights(view, portfolio.weights(close_prices))
            if rebalance_frequency == "weekly":
                last_rebalance_week = (iso.year, iso.week)
    equity = pd.DataFrame(equity_rows)
    trades = pd.DataFrame([fill.__dict__ for fill in portfolio.fills])
    positions = pd.DataFrame(positions_rows)
    costs = float(trades["commission"].sum()) if not trades.empty else 0.0
    bench = benchmark_curve(bars[config["benchmark"]], float(config["starting_capital"]))
    metrics = compute_metrics(equity, bench, len(portfolio.fills), costs)
    config_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()[:16]
    out_dir = Path(config["output_dir"]) / f"{config['strategy']['name']}_{config_hash}"
    out_dir.mkdir(parents=True, exist_ok=True)
    equity.to_csv(out_dir / "equity_curve.csv", index=False)
    trades.to_csv(out_dir / "trades.csv", index=False)
    positions.to_csv(out_dir / "positions.csv", index=False)
    bench.to_csv(out_dir / "benchmark_equity.csv", index=False)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    metadata = {
        "config_hash": config_hash,
        "python": platform.python_version(),
        "symbols": all_symbols(config),
        "cost_model": config["cost_model"],
        "timing": "decision at close t, fill next open",
        "rebalance": rebalance_config,
        "data": "yfinance auto_adjust=True cached parquet",
    }
    (out_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    report_config = config.get("report", {})
    gates = report_config.get(
        "gates",
        [
            "**STAGE GATE: CONDITIONAL PASS** Real yfinance data was used with adjusted bars, and the engine ran independently. Source-rule fidelity depends on the provided strategy specification.",
        ],
    )
    assumptions = report_config.get(
        "assumptions",
        [
            "Signals use adjusted daily yfinance prices and next-open fills.",
        ],
    )
    write_report(out_dir / "report.md", report_config.get("title", config["strategy"]["name"]), metrics, assumptions, gates)
    violations = scan_for_forbidden_terms(Path("."))
    if violations:
        (out_dir / "independence_violations.txt").write_text("\n".join(violations), encoding="utf-8")
    print(out_dir)
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("fetch", "run", "fetch-intraday", "run-intraday-orb"):
        p = sub.add_parser(name)
        p.add_argument("config", type=Path)
    signal_parser = sub.add_parser("orb-signal")
    signal_parser.add_argument("config", type=Path)
    signal_parser.add_argument("--date", dest="session_date")
    signal_parser.add_argument("--capital", type=float, default=None)
    live_parser = sub.add_parser("live-orb-ibkr")
    live_parser.add_argument("config", type=Path)
    live_parser.add_argument("--capital", type=float, default=None)
    live_parser.add_argument("--host", default="127.0.0.1")
    live_parser.add_argument("--port", type=int, default=7497)
    live_parser.add_argument("--client-id", type=int, default=45)
    live_parser.add_argument("--account", default=None)
    live_parser.add_argument("--no-confirm", action="store_true")
    live_parser.add_argument("--transmit", action="store_true")
    live_parser.add_argument("--no-wait", action="store_true")
    live_parser.add_argument("--poll-seconds", type=int, default=10)
    live_parser.add_argument("--signal-buffer-seconds", type=int, default=5)
    args = parser.parse_args()
    if args.cmd == "fetch":
        fetch(args.config)
    elif args.cmd == "run":
        run(args.config)
    elif args.cmd == "fetch-intraday":
        fetch_intraday(args.config)
    elif args.cmd == "run-intraday-orb":
        run_intraday_orb(args.config)
    elif args.cmd == "orb-signal":
        orb_signal(args.config, args.session_date, args.capital)
    elif args.cmd == "live-orb-ibkr":
        from backtest_engine.live_ibkr_orb import IbkrOrbSettings, run_live_ibkr_orb

        run_live_ibkr_orb(
            IbkrOrbSettings(
                config_path=args.config,
                capital=args.capital,
                host=args.host,
                port=args.port,
                client_id=args.client_id,
                account=args.account,
                confirm=not args.no_confirm,
                transmit=args.transmit,
                wait=not args.no_wait,
                poll_seconds=args.poll_seconds,
                signal_buffer_seconds=args.signal_buffer_seconds,
            )
        )


if __name__ == "__main__":
    main()
