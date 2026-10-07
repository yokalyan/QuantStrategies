# Conditional Sector Rotation Baseline

## Metrics
- `total_return`: 2312034.70%
- `cagr`: 97.60%
- `annual_volatility`: 59.35%
- `sharpe`: 1.443
- `sortino`: 2.024
- `calmar`: 1.833
- `max_drawdown`: -53.25%
- `max_drawdown_duration_days`: 252.00
- `best_day`: 38.84%
- `worst_day`: -25.65%
- `number_of_trades`: 615.00
- `total_costs`: 10943064.76
- `beta`: 1.649
- `alpha`: 60.27%
- `correlation`: 0.459

## Assumptions And Caveats
- The pasted sample was translated as a specification; no external engine code is imported.
- Daily decisions use adjusted close values through the decision date and fill at the next open.
- The strategy holds 100% in one selected ETF; no leverage or margin borrowing beyond each ETF's embedded leverage is modeled.
- yfinance adjusted OHLCV data may differ from the source platform data and leveraged ETF corporate-action handling.

## Gates
**STAGE 1 GATE: PASS** The pasted code fully specifies the ticker universe, indicators, thresholds, and target-selection tree. Fill behavior is translated to next-open execution to preserve independent no-look-ahead timing.
**STAGE 2-6 GATE: CONDITIONAL PASS** The independent engine ran this strategy without external engine dependencies. Results are data-vendor dependent and should not be reconciled to the source platform without its exact backtest output.
