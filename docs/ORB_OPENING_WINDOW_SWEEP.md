# ORB Opening Window Sweep

This note compares TQQQ midpoint-stop opening-range breakout variants on the local one-minute file from 2010-02-11 through 2025-06-02. The test keeps the same core mechanics: opening-candle direction, breakout before 10:30 ET, midpoint stop, 10R target, 6R breakeven trigger, 0.6% risk, and 4x notional cap.

## Main Result

Five minutes is not uniquely special. It is the most aggressive version and has strong raw upside, but the 15-minute window produced the best return/drawdown balance in this sweep. It kept most of the upside while cutting the unfiltered 5-minute drawdown sharply.

| OR window | Best tested OR/ATR20 band | Trades | Total return | CAGR | Sharpe | Max DD | Win rate | Profit factor |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 min | 0.20-0.35 | 1,010 | 153.2% | 6.3% | 0.535 | -36.9% | 26.2% | 1.232 |
| 10 min | 0.30-0.55 | 693 | 115.6% | 5.1% | 0.645 | -14.5% | 35.5% | 1.289 |
| 15 min | 0.20-0.35 | 1,322 | 183.9% | 7.1% | 0.611 | -18.7% | 31.3% | 1.199 |
| 20 min | 0.30-0.55 | 1,168 | 144.7% | 6.0% | 0.637 | -16.3% | 37.0% | 1.197 |
| 30 min | 0.40-0.70 | 779 | 68.7% | 3.5% | 0.542 | -14.1% | 42.4% | 1.220 |

## Unfiltered Baselines

Without the OR/ATR20 filter, shorter windows have higher return but much deeper drawdowns:

| OR window | Trades | Total return | CAGR | Sharpe | Max DD | Win rate | Profit factor |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 min | 3,118 | 327.6% | 10.0% | 0.514 | -60.0% | 23.3% | 1.160 |
| 10 min | 2,858 | 329.2% | 10.0% | 0.586 | -42.5% | 28.5% | 1.170 |
| 15 min | 2,643 | 295.4% | 9.4% | 0.610 | -36.8% | 31.1% | 1.162 |
| 20 min | 2,507 | 151.2% | 6.2% | 0.475 | -45.1% | 33.6% | 1.122 |
| 30 min | 2,237 | 138.6% | 5.8% | 0.503 | -39.1% | 37.0% | 1.126 |

## Interpretation

The five-minute window captures the earliest imbalance and gives the tightest midpoint stop. That creates large R-multiple upside when the early move extends, but it also causes many false starts and severe equity swings.

Longer windows wait for more information. The entry is later and the range is wider, so raw convexity falls, but signal quality improves: win rate rises, profit factor improves, and drawdown tends to compress. The 15-minute variant is the selected default because it produced materially higher return than 10 or 20 minutes while keeping drawdown below 20%.

The OR/ATR20 filter must scale with the opening window. A 5-minute opening range that is 20-35% of ATR is already meaningful; a 30-minute opening range in that same band is often too quiet. The best 30-minute tests shifted to 40-70% of ATR.

## Practical Takeaway

The default live command now uses the 15-minute opening range with the `0.20-0.35` OR/ATR20 band. This means the signal should be run after the 09:44 ET bar is available, with entries allowed from 09:45 until before 10:30. The current implementation honors `opening_range_minutes`, so changing the config to `5`, `10`, `20`, or `30` changes both the signal sheet and backtest behavior.
