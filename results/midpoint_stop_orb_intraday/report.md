# Midpoint Stop Opening Range Breakout Intraday Baseline

## Metrics
- `start`: 2021-01-04
- `end`: 2025-06-02
- `total_return`: 2.673658
- `cagr`: 0.343384
- `sharpe`: 1.344752
- `max_drawdown`: -0.160643
- `number_of_fills`: 1774

## Caveats
- This run uses the configured local one-minute bar file when `source_file` is present; otherwise it falls back to the limited yfinance intraday cache.
- The local file covered the reported start/end dates in the metrics, which may be shorter than the source code's requested end date.
- The backtest implements the pasted close-based stop/target checks.
- No fees are applied, matching the pasted zero-fee model.
