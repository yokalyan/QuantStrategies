# TQQQ RSI Mean Reversion Baseline

## Metrics
- `total_return`: 570.20%
- `cagr`: 34.90%
- `annual_volatility`: 74.09%
- `sharpe`: 0.780
- `sortino`: 1.053
- `calmar`: 0.428
- `max_drawdown`: -81.49%
- `max_drawdown_duration_days`: 744.00
- `best_day`: 35.24%
- `worst_day`: -34.46%
- `number_of_trades`: 209.00
- `total_costs`: 1715.51
- `beta`: 0.921
- `alpha`: 3.77%
- `correlation`: 0.919

## Assumptions And Caveats
- The pasted sample was translated as a specification; no external engine code is imported.
- The sample uses simple 10-day RSI, so this implementation uses simple average gains/losses rather than Wilder smoothing.
- The sample schedules shortly after market open; this independent engine decides with daily data through the close and fills at the next open to avoid look-ahead.
- The pasted code sets cash to 25000 despite a comment saying 10K; the numeric code value is used.
- Source summary metrics are recorded as reference only and not used for tuning.

## Gates
**STAGE 1 GATE: PASS** The pasted code fully specifies the universe, RSI period, threshold, daily binary target, start/end dates, and starting capital.
**STAGE 2-6 GATE: CONDITIONAL PASS** The strategy ran on independent yfinance adjusted data with next-open execution. Differences from the source summary can come from data vendor, timing, fees, slippage, and adjustment conventions.
