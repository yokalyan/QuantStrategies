# Tech Momentum With GLD Sweep Baseline

## Metrics
- `total_return`: 2612.11%
- `cagr`: 32.41%
- `annual_volatility`: 25.19%
- `sharpe`: 1.244
- `sortino`: 1.672
- `calmar`: 0.793
- `max_drawdown`: -40.88%
- `max_drawdown_duration_days`: 536.00
- `best_day`: 9.63%
- `worst_day`: -8.68%
- `number_of_trades`: 22501.00
- `total_costs`: 27014.01
- `beta`: 0.957
- `alpha`: 12.06%
- `correlation`: 0.832

## Assumptions And Caveats
- The pasted attachment repeated the prior Quad Ensemble code, so this strategy is implemented from the user's prose specification.
- The large, liquid US technology universe is represented by a static config list and is not point-in-time.
- The stop loss is modeled as position target weight times loss since latest monthly entry; if that exceeds 2% of portfolio value, the symbol is removed until the next monthly rebalance.
- Daily GLD sweep allocates residual target capital to GLD whenever residual capital is at least 1%.
- Monthly rebalancing is implemented inside a daily strategy loop so daily stops and GLD sweeps can run.

## Gates
**STAGE 1 GATE: CONDITIONAL PASS** The prose specifies the core monthly momentum ranking, inverse-vol sizing, top-10 positive-momentum filter, 2% portfolio-loss stop, and GLD residual sweep. Exact code-level universe, dates, and sweep threshold were not provided and are documented assumptions.
**STAGE 2-6 GATE: CONDITIONAL PASS** The strategy ran independently on yfinance adjusted data. Results should be read as a prose-spec implementation rather than a source-code reconciliation.
