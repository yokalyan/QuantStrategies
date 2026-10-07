# Advanced Hybrid Rotation Baseline

## Metrics
- `total_return`: 1315.26%
- `cagr`: 48.02%
- `annual_volatility`: 29.65%
- `sharpe`: 1.477
- `sortino`: 2.020
- `calmar`: 1.952
- `max_drawdown`: -24.60%
- `max_drawdown_duration_days`: 375.00
- `best_day`: 9.34%
- `worst_day`: -9.79%
- `number_of_trades`: 9483.00
- `total_costs`: 112204.56
- `beta`: 0.759
- `alpha`: 31.39%
- `correlation`: 0.513

## Assumptions And Caveats
- The pasted sample was translated as a specification; no external engine code is imported.
- Weekly core rebalance is implemented as every five trading sessions inside the daily engine loop.
- The sample's SPY volatility targeting dynamically scales core and satellite budgets; this implementation applies that scaling before each daily target calculation.
- QC logging and holdings diagnostics are omitted because they do not affect portfolio rules.
- Some thematic ETFs have shorter yfinance history; they become eligible only once enough local history exists.

## Gates
**STAGE 1 GATE: PASS** The pasted code specifies the core universe, momentum/trend filters, satellite RSI tree, volatility target, capital split, start date, and capital.
**STAGE 2-6 GATE: CONDITIONAL PASS** The strategy ran on independent yfinance adjusted data with next-open execution. Differences from the source platform may come from data availability, timing, fees, and indicator conventions.
