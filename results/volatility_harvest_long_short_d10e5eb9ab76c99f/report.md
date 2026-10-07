# Volatility Harvest ML Long Short Baseline

## Metrics
- `total_return`: 823.75%
- `cagr`: 20.82%
- `annual_volatility`: 18.23%
- `sharpe`: 1.132
- `sortino`: 1.422
- `calmar`: 0.705
- `max_drawdown`: -29.51%
- `max_drawdown_duration_days`: 382.00
- `best_day`: 8.56%
- `worst_day`: -8.90%
- `number_of_trades`: 11542.00
- `total_costs`: 22281.98
- `beta`: 0.682
- `alpha`: 10.74%
- `correlation`: 0.655

## Assumptions And Caveats
- The pasted sample was translated as a specification; no external engine code is imported.
- QuantConnect coarse/fine fundamentals are replaced by config-supplied top long symbols and a static liquid short universe.
- CBOE VIX custom data is represented by FRED VIXCLS.
- Intraday scheduled long, short, and risk checks are approximated through one daily decision with next-open fills.
- Margin availability and borrow constraints are not modeled; target gross sleeves are applied directly through signed target weights.

## Gates
**STAGE 1 GATE: CONDITIONAL PASS** The pasted code specifies the long regime rules, ML features, short Hurst/ATR filters, and stop logic, but its fundamental universe construction must be approximated independently.
**STAGE 2-6 GATE: CONDITIONAL PASS** The strategy ran on independent yfinance/FRED data with static universes and next-open execution. Results should be read as an independent approximation, not a platform reconciliation.
