# Midpoint Stop Opening Range Breakout Intraday Baseline

## Metrics
- `start`: 2010-02-11
- `end`: 2025-06-02
- `total_return`: 1.905276
- `cagr`: 0.072172
- `sharpe`: 0.5186
- `max_drawdown`: -0.348311
- `number_of_fills`: 2856

## Caveats
- This run uses the configured local one-minute bar file when `source_file` is present; otherwise it falls back to the limited yfinance intraday cache.
- Opening range uses the first 5 regular-session minutes.
- Opening range / ATR20 filter: 0.15 < ratio <= 0.25.
- The local file covered the reported start/end dates in the metrics, which may be shorter than the source code's requested end date.
- The backtest implements the pasted close-based stop/target checks.
- No fees are applied, matching the pasted zero-fee model.
