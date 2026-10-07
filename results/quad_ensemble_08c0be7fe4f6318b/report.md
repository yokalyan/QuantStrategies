# Quad Ensemble Tactical Allocation Baseline

## Metrics
- `total_return`: 130337.72%
- `cagr`: 189.11%
- `annual_volatility`: 52.67%
- `sharpe`: 2.283
- `sortino`: 3.423
- `calmar`: 5.569
- `max_drawdown`: -33.96%
- `max_drawdown_duration_days`: 96.00
- `best_day`: 41.80%
- `worst_day`: -18.11%
- `number_of_trades`: 6985.00
- `total_costs`: 103511.21
- `beta`: 1.304
- `alpha`: 98.91%
- `correlation`: 0.496

## Assumptions And Caveats
- The pasted sample was translated as a specification; no external engine code is imported.
- Each of the four sleeves contributes up to a 25% target budget and overlapping positions are summed.
- Same-day market-on-open order handling is approximated as close-of-day signal evaluation with next-open fills.
- Date-based live checks for SVIX and UVIX are preserved; missing early histories naturally keep those proxies unavailable.
- Cash sleeve output is represented by returning no target for that sleeve.

## Gates
**STAGE 1 GATE: PASS** The pasted code specifies all four sleeves, indicators, thresholds, dates, universe, and 25% budget aggregation.
**STAGE 2-6 GATE: CONDITIONAL PASS** The strategy ran on independent yfinance adjusted data with next-open execution. Differences from the source platform are expected because scheduling, symbol history availability, and fill mechanics differ.
