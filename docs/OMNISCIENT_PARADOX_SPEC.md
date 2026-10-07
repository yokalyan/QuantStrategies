# The Omniscient Paradox Spec

This strategy was translated from pasted sample code and prose into the independent engine.

## Universe

Risk candidates: SOXL, TECL, TQQQ, FAS, ERX, UUP, TMF.  
Safe/cash-like asset: BIL.  
Regime asset: SPY.

## Signal

For each risk candidate, compute:

- 9-day rate of change.
- 21-day rate of change.
- 63-day rate of change.
- 21-day realized volatility.
- 14-day Wilder RSI.
- 50-day simple moving average.

Composite momentum is `0.5 * fast + 0.3 * medium + 0.2 * slow`. The score is composite momentum divided by realized volatility, multiplied by a 50-day trend score of `1.0` when price is above SMA and `0.5` otherwise. If RSI is above 85 or below 30, the score is multiplied by `0.9`.

## Rotation Logic

The strategy generally holds one risk ETF or BIL. If no current holding exists, it buys the best positive-scoring asset, otherwise BIL. If currently in BIL, it exits only when the best score is above `0.02`. If currently in a risk asset, it rotates only when the best asset beats the current score by 10%, or moves to BIL when the current score is below `-0.02`.

If SPY is below its 200-day SMA, the selected risk asset is overridden by UUP when UUP has a positive score and beats the selected asset. If the selected asset has a negative score, the strategy moves to BIL.

## Sizing

Risk assets are sized to `target_vol / realized_volatility`, capped at 100%. If more than 10% of the portfolio remains after volatility targeting, the remainder is allocated to BIL. BIL itself receives a 100% target weight when selected.

## Fidelity Notes

The sample schedules trades five minutes before the close using minute-resolution subscriptions. The independent engine uses daily close decisions and fills at the next open to keep look-ahead prevention structural. The sample's `STD` indicator is interpreted here as realized return volatility because that matches the supplied strategy description.
