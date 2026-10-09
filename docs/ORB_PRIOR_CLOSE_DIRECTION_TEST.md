# ORB Prior-Close Direction Test

This test checks whether the TQQQ midpoint-stop ORB should continue using the opening-range candle direction, require agreement with the prior regular-session close, or replace the opening candle direction with the move from the prior close to the opening-range close.

Data and shared settings:

- Data: local TQQQ one-minute file from 2010-02-11 through 2025-06-02.
- Opening range: first 15 regular-session minutes.
- Entry window: after the opening range through before 10:30 ET.
- OR/ATR20 filter: `0.20 < opening_range / ATR20 <= 0.35`.
- Stop: opening-range midpoint.
- Target: 10R.
- Breakeven move: 6R.
- Risk: 0.6% of equity, with 4x notional cap.
- Fees/slippage: not modeled.

## Direction Modes

| Mode | Rule |
| --- | --- |
| `opening_range` | Existing behavior. Long only if the opening-range candle closes above its open; short only if it closes below its open. |
| `previous_close_agreement` | Trade only if the opening-range candle direction agrees with the move from the prior regular-session close to the opening-range close. |
| `previous_close` | Use the move from the prior regular-session close to the opening-range close as the trade direction. |

The two edge cases motivating the test behave as follows:

- Prior close `85`, opening-range open `80`, opening-range close `80.50`: opening-range candle is bullish, but prior-close direction is bearish. `previous_close_agreement` skips it; `previous_close` treats it as bearish.
- Prior close `85`, opening-range open `88`, opening-range close `86`: opening-range candle is bearish, but prior-close direction is bullish. `previous_close_agreement` skips it; `previous_close` treats it as bullish.

## Results

| Mode | Total Return | CAGR | Sharpe | Max DD | Entries | Long Entries | Short Entries | Win Rate | Avg PnL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `opening_range` | 183.9% | 7.1% | 0.61 | -18.7% | 1,322 | 679 | 643 | 31.3% | $139 |
| `previous_close_agreement` | 123.0% | 5.4% | 0.58 | -16.1% | 831 | 476 | 355 | 32.4% | $148 |
| `previous_close` | 211.7% | 7.7% | 0.69 | -15.7% | 1,132 | 647 | 485 | 31.9% | $187 |

## Period Slices

| Mode | Period | Return | CAGR | Sharpe | Max DD |
| --- | --- | ---: | ---: | ---: | ---: |
| `opening_range` | 2010-2014 | 24.7% | 4.6% | 0.43 | -18.7% |
| `previous_close_agreement` | 2010-2014 | 28.8% | 5.3% | 0.58 | -10.6% |
| `previous_close` | 2010-2014 | 21.4% | 4.1% | 0.39 | -14.5% |
| `opening_range` | 2015-2020 | 33.0% | 4.9% | 0.46 | -14.3% |
| `previous_close_agreement` | 2015-2020 | 25.4% | 3.9% | 0.44 | -16.1% |
| `previous_close` | 2015-2020 | 45.4% | 6.4% | 0.60 | -15.7% |
| `opening_range` | 2021-2025 | 71.3% | 13.0% | 0.99 | -13.8% |
| `previous_close_agreement` | 2021-2025 | 38.1% | 7.6% | 0.77 | -14.9% |
| `previous_close` | 2021-2025 | 76.6% | 13.8% | 1.13 | -10.6% |

## Read-Through

The strict agreement filter improves the worst drawdown versus the baseline, but it removes too many trades and lowers total return, CAGR, and Sharpe. It is more conservative, not better overall.

The `previous_close` replacement is more promising. It reduces trade count, improves average PnL, improves Sharpe, improves max drawdown, and slightly improves return. The improvement appears because disagreement days are not simply bad days to skip. In the baseline, disagreement trades had lower expectancy than agreement trades. When direction is flipped to prior-close direction, the disagreement subset improved materially in this historical sample.

This is worth studying further, but not yet enough to declare durable alpha. The next checks should be walk-forward validation, slippage/spread modeling, and separate gap-up/gap-down diagnostics before changing live defaults.
