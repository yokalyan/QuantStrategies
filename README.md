# Independent Quant Strategy Backtester

This project is independent of QuantConnect and LEAN. It uses a small pure-Python event backtest engine, local data caching, and strategy plug-ins.

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python -m backtest_engine.cli fetch configs/qqq_kelly_momentum_leaders.yaml
python -m backtest_engine.cli run configs/qqq_kelly_momentum_leaders.yaml
pytest
```

Additional strategy configs:

```bash
python -m backtest_engine.cli fetch configs/conditional_sector_rotation.yaml
python -m backtest_engine.cli run configs/conditional_sector_rotation.yaml
python -m backtest_engine.cli fetch configs/macro_factor_rotation.yaml
python -m backtest_engine.cli run configs/macro_factor_rotation.yaml
python -m backtest_engine.cli fetch configs/omniscient_paradox.yaml
python -m backtest_engine.cli run configs/omniscient_paradox.yaml
```

The first `fetch` uses yfinance and writes Parquet files under `data/cache`. After that, the backtest runs from local cache with `data_source.mode: cache`.

## Data Schema

Cached Parquet files contain one file per symbol named `<SYMBOL>.parquet` with columns:

`date, open, high, low, close, volume`

Prices are yfinance `auto_adjust=True` prices, so OHLC prices are split/dividend adjusted. Volume is vendor-provided volume.

## Baseline Caveat

The QuantConnect strategy page returned a JavaScript terminal shell without the strategy rules. The included QQQ Kelly momentum strategy is therefore an explicitly marked assumption-based reconstruction from the title, not a verified reproduction of the source strategy.
