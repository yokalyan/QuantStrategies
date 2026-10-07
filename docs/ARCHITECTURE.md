# Architecture

The engine is strategy-agnostic. A YAML config names a strategy module and parameters; the engine imports that strategy through the registry and never contains ticker-specific or strategy-specific rules.

## Layers

- `data`: Loads cached CSV/Parquet-style OHLCV bars or fetches yfinance bars into local Parquet cache.
- `strategy`: Defines `Strategy`, `MarketDataView`, and the registry. Strategies receive data physically truncated through the current decision date.
- `portfolio`: Tracks cash, positions, fills, and target-weight order generation.
- `execution`: Applies next-open fills, per-share commissions, and basis-point slippage.
- `sizing`: Reusable sizing utilities, including Kelly-style weight conversion.
- `analytics`: Computes return, risk, drawdown, benchmark, and trade statistics.
- `reporting`: Writes Markdown reports and CSV artifacts.
- `validation`: Static independence scan and data validation.

## Event Ordering

At decision date `t`, strategies only receive bars with dates `<= t`. Orders are stored and filled on the next available bar open at `t+1`. This structure prevents a strategy from seeing the fill bar when it decides.

## Reproducibility

Every run writes a config hash, Python version, dependency metadata, start/end dates, symbols, cost model, and data fingerprints next to the report.

