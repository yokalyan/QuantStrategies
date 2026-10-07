# Tech Momentum With GLD Sweep Spec

This strategy was implemented from the user's prose description. The pasted attachment for this turn repeated the prior Quad Ensemble code, so no matching source code was available for this strategy.

## Rules

- Universe: static large, liquid US technology equities listed in the config.
- Rebalance: monthly at the start of each month.
- Momentum: 90-day price momentum.
- Eligibility: positive momentum only.
- Selection: top 10 by 90-day momentum.
- Sizing: inverse 20-day realized volatility among selected names.
- Defensive asset: GLD.
- Stop: liquidate a holding if its unrealized loss since the latest monthly entry exceeds 2% of total portfolio value.
- Sweep: residual capital from fewer than 10 names or stop-outs is allocated to GLD daily.

## Assumptions

Because the matching source code was not provided, the implementation assumes:

- Start date: 2015-01-01.
- Starting capital: 100,000 USD.
- Benchmark: QQQ.
- Static universe rather than point-in-time large/liquid selection.
- Residual GLD sweep threshold: 1% of portfolio target capital.

## Fidelity Notes

The engine evaluates stops and sweeps daily with data visible through close of day `t` and fills targets at the next open. That keeps look-ahead prevention structural but may differ from any original platform scheduling.
