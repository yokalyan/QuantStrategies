# QQQ Kelly Momentum Leaders Baseline

## Metrics
- `total_return`: 763.67%
- `cagr`: 20.13%
- `annual_volatility`: 20.25%
- `sharpe`: 1.010
- `sortino`: 1.249
- `calmar`: 0.612
- `max_drawdown`: -32.91%
- `max_drawdown_duration_days`: 546.00
- `best_day`: 11.46%
- `worst_day`: -12.49%
- `number_of_trades`: 3079.00
- `total_costs`: 8130.11
- `beta`: 0.710
- `alpha`: 6.15%
- `correlation`: 0.768

## Assumptions And Caveats
- QuantConnect page returned only a terminal shell; original rules and source metrics were unavailable.
- Universe is static and survivorship-biased.
- Signals use adjusted daily yfinance prices and next-open fills.

## Gates
**STAGE 0 GATE: CONDITIONAL PASS** Real yfinance data was reachable and cached. The condition is that yfinance is not an institutional point-in-time source and is used with adjusted bars.
**STAGE 1 GATE: CONDITIONAL PASS** The original QuantConnect page did not expose strategy rules, so this run is an assumption-based implementation. Results must not be described as a reproduction of source performance.
**STAGE 2-6 GATE: CONDITIONAL PASS** The engine, tests, and baseline run completed independently. Remaining unresolved issue is source-rule fidelity.
