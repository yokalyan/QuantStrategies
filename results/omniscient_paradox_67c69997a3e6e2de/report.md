# The Omniscient Paradox Baseline

## Metrics
- `total_return`: 2406.56%
- `cagr`: 51.49%
- `annual_volatility`: 50.35%
- `sharpe`: 1.082
- `sortino`: 1.376
- `calmar`: 1.077
- `max_drawdown`: -47.80%
- `max_drawdown_duration_days`: 424.00
- `best_day`: 15.66%
- `worst_day`: -19.01%
- `number_of_trades`: 942.00
- `total_costs`: 51547.15
- `beta`: 0.644
- `alpha`: 42.93%
- `correlation`: 0.246

## Assumptions And Caveats
- The pasted sample was translated as a specification; no external engine code is imported.
- Minute-resolution scheduling near the close is approximated with daily close decisions and next-open fills.
- The sample's daily STD indicator is interpreted as realized return volatility to match the provided strategy description.
- BIL is used as the safe/cash-like asset and may also receive leftover capital after volatility targeting.
- Leveraged ETF returns are from yfinance adjusted OHLCV and may differ from the source platform's normalization.

## Gates
**STAGE 1 GATE: PASS** The pasted code and prose specify the universe, composite ROC score, volatility scaling, SMA discount, RSI penalty, SPY regime filter, hysteresis, safe asset, and volatility-targeted sizing.
**STAGE 2-6 GATE: CONDITIONAL PASS** The strategy ran through the independent daily engine with next-open execution. Differences from the source platform are expected because minute scheduling and data normalization are approximated.
