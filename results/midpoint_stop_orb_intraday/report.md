# Midpoint Stop Opening Range Breakout Intraday Baseline

## Metrics
- `start`: 2010-02-11
- `end`: 2025-06-02
- `total_return`: 3.974647
- `cagr`: 0.11052
- `sharpe`: 0.553601
- `max_drawdown`: -0.594367
- `number_of_fills`: 6278

## Caveats
- This run uses the configured local one-minute bar file when `source_file` is present; otherwise it falls back to the limited yfinance intraday cache.
- The local file covered the reported start/end dates in the metrics, which may be shorter than the source code's requested end date.
- The backtest implements the pasted close-based stop/target checks.
- No fees are applied, matching the pasted zero-fee model.
