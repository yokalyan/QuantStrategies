# Strategy Research Review

This memo reviews the independent backtests currently saved in `results/`. It is not investment advice; it is a research triage note about which ideas deserve more work and which results look mostly like leverage, data-mining, or bull-market exposure.

## Executive Verdict

The strongest-looking headline curves are mostly the strategies with concentrated leveraged ETF exposure and volatility/inverse ETF switching. Those may contain useful tactical ideas, but the raw strategies are not production-ready: the best returns come with high turnover, embedded leverage, dependence on 2020-2026 market structure, and in several cases static/survivorship-biased universes.

The ideas worth studying further are not the full recipes. The reusable pieces are: regime-gated momentum, inverse-volatility sizing, residual defensive allocation, explicit volatility targeting, and ensemble diversification across independent signals. The full-window ORB result is now more modest than the 2021-2025 slice, which is exactly why long-window testing matters.

## Headline Metrics

| Strategy | CAGR | Vol | Sharpe | Max DD | Calmar | Beta | Trades/Fills | Costs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Quad Ensemble | 189.1% | 52.7% | 2.28 | -34.0% | 5.57 | 1.30 | 6985 | $103,511 |
| Advanced Hybrid Rotation | 48.0% | 29.6% | 1.48 | -24.6% | 1.95 | 0.76 | 9483 | $112,205 |
| Conditional Sector Rotation | 97.6% | 59.3% | 1.44 | -53.2% | 1.83 | 1.65 | 615 | $10,943,065 |
| Tech Momentum GLD Sweep | 32.4% | 25.2% | 1.24 | -40.9% | 0.79 | 0.96 | 22501 | $27,014 |
| Volatility Harvest Long/Short | 20.8% | 18.2% | 1.13 | -29.5% | 0.71 | 0.68 | 11542 | $22,282 |
| Omniscient Paradox | 51.5% | 50.4% | 1.08 | -47.8% | 1.08 | 0.64 | 942 | $51,547 |
| QQQ Kelly Momentum Leaders | 20.1% | 20.2% | 1.01 | -32.9% | 0.61 | 0.71 | 3079 | $8,130 |
| TQQQ RSI Mean Reversion | 34.9% | 74.1% | 0.78 | -81.5% | 0.43 | 0.92 | 209 | $1,716 |
| Macro Factor Rotation | 10.4% | 14.8% | 0.75 | -23.6% | 0.44 | 0.34 | 209 | $415 |
| Midpoint Stop ORB Intraday | 11.1% | n/a | 0.55 | -59.4% | n/a | n/a | 6278 | $0 |

Note: Midpoint Stop ORB Intraday now uses the provided local one-minute file from 2010-02-11 through 2025-06-02. The longer test is much weaker than the earlier 2021-2025 slice, with 11.1% CAGR, 0.55 Sharpe, and -59.4% max drawdown.

## Stress Windows

| Strategy | COVID Window | 2022 Rate Bear | 2023-2026 Bull/AI Window |
| --- | ---: | ---: | ---: |
| Advanced Hybrid Rotation | 27.2% | -14.3% | 343.8% |
| Conditional Sector Rotation | -1.3% | 79.3% | 1142.5% |
| Macro Factor Rotation | -0.3% | -7.6% | 80.6% |
| Midpoint Stop ORB Intraday | -3.9% | 25.8% | 114.5% |
| Omniscient Paradox | 3.2% | 80.1% | 426.2% |
| QQQ Kelly Momentum Leaders | -7.3% | -30.5% | 102.1% |
| Quad Ensemble | -14.1% | 310.8% | 6848.2% |
| TQQQ RSI Mean Reversion | -25.4% | -79.5% | 721.9% |
| Tech Momentum GLD Sweep | -0.7% | -35.0% | 330.2% |
| Volatility Harvest Long/Short | 11.9% | -26.5% | 230.7% |

## Strategy-by-Strategy Read

### Midpoint Stop ORB Intraday
The full 2010-2025 file changes the conclusion. The 2021-2025 slice looked strong, but the full test is only about 11% CAGR with Sharpe 0.55 and a -59% drawdown. It still has positive expectancy over many trades, but the edge is regime-dependent and early years were rough. Worth studying as an intraday signal, not adoptable as-is.
Recent annual returns: 2021: 35.0%, 2022: 25.8%, 2023: 12.2%, 2024: 63.1%, 2025: 13.7%.

### Macro Factor Rotation
This is the most intellectually plausible as a diversified tactical allocator, but the results are modest. That is not a bad sign: lower beta, lower drawdown, and realistic return profile make it a better candidate for serious research than the extreme leveraged ETF systems.
Recent annual returns: 2022: -7.6%, 2023: 19.9%, 2024: 19.1%, 2025: 33.7%, 2026: -5.7%.

### Tech Momentum GLD Sweep
Conceptually clean: cross-sectional momentum, inverse-vol sizing, and GLD residual allocation. The static tech universe introduces survivorship bias, and the trade count is too high because stops/sweeps alter targets daily. Worth rebuilding with point-in-time membership and lower turnover constraints.
Recent annual returns: 2022: -35.0%, 2023: 53.5%, 2024: 38.5%, 2025: 33.5%, 2026: 53.7%.

### Advanced Hybrid Rotation
One of the more interesting frameworks. The core/satellite split and SPY volatility targeting are useful design ideas. Still, the satellite is another leveraged ETF timing tree, and the high trade count/costs show implementation friction matters.
Recent annual returns: 2022: -14.3%, 2023: 65.1%, 2024: 36.1%, 2025: 51.5%, 2026: 32.0%.

### Quad Ensemble
Very high headline performance, but also a classic danger zone: many leveraged, inverse, volatility, and short-volatility products with layered RSI/SMA thresholds. The concept of combining independent sleeves is good; the exact recipe is likely overfit.
Recent annual returns: 2022: 310.8%, 2023: 229.9%, 2024: 392.0%, 2025: 111.4%, 2026: 111.7%.

### Conditional Sector Rotation
A high-octane leveraged ETF decision tree. It may exploit some short-term regime behavior, but the enormous return and 53% drawdown say this is closer to a tactical leveraged product timing system than a durable all-weather strategy.
Recent annual returns: 2022: 79.3%, 2023: 134.8%, 2024: 70.7%, 2025: 91.2%, 2026: 73.1%.

### Omniscient Paradox
The reusable part is risk-adjusted momentum plus hysteresis and a safe asset. The current version remains dominated by leveraged ETFs and has nearly 48% drawdown, but its lower market correlation suggests it is worth studying as a component.
Recent annual returns: 2022: 80.1%, 2023: 103.5%, 2024: 45.4%, 2025: -18.1%, 2026: 125.1%.

### Volatility Harvest Long/Short
The long/short framing is promising, but the independent version had to replace QuantConnect fundamentals with static universes. The Hurst/ATR short sleeve is worth studying separately, especially as a risk overlay.
Recent annual returns: 2022: -26.5%, 2023: 51.0%, 2024: 60.4%, 2025: 23.3%, 2026: 12.2%.

### QQQ Kelly Momentum Leaders
Decent risk-adjusted result, but the original source rules were unavailable, so this is an assumed reconstruction. Kelly-style sizing from noisy return estimates is fragile.
Recent annual returns: 2022: -30.5%, 2023: 19.4%, 2024: 45.9%, 2025: 17.5%, 2026: 0.7%.

### TQQQ RSI Mean Reversion
Simple, transparent, and brutally risky. The max drawdown around -81% confirms the key issue: binary switching between TQQQ and UVXY can be uninvestable even when total return is high.
Recent annual returns: 2022: -79.5%, 2023: 155.2%, 2024: 118.5%, 2025: 41.1%, 2026: 11.5%.

## What Looks Like Real Alpha?

Possible alpha exists in components, not in most raw end-to-end recipes. Cross-sectional momentum with inverse-vol sizing has prior support. Regime filters and volatility targeting are useful mostly because they control exposure. The macro factor model may have weak but diversifying signal. The ORB signal has positive full-period expectancy but is much less compelling after expanding from 2021 to 2010, so it needs regime filters or parameter robustness before being taken seriously.

## What Will Likely Fail In A Bear Market?

Anything structurally leaning on TQQQ, SOXL, TECL, short-volatility, or high-beta tech will likely suffer in prolonged bear or sideways markets unless the defensive switch is both timely and cheap. The ORB also had a severe early-period drawdown, so flat-by-close does not automatically mean low risk.

## Improvements To Prioritize

1. Add walk-forward testing and parameter grids for RSI thresholds, SMA lengths, lookbacks, ORB R-multiples, and rebalance timing.
2. Add out-of-sample splits and avoid selecting the best slice after seeing results.
3. Replace static universes with point-in-time or at least frozen-at-start universes.
4. Model ETF borrow/financing, margin interest, short availability, spreads, and market impact.
5. For ORB, add spread/slippage, high/low-aware stop-target sequencing, and regime filters around volatility/liquidity.

## Worth Studying Further

Most worth deeper study: Macro Factor Rotation, Tech Momentum GLD Sweep, Advanced Hybrid Rotation, and selected components from Omniscient Paradox. ORB is worth studying as an intraday signal, but the full-period test demotes it from “promising” to “interesting but unstable.”

Least trustworthy as-is: strategies whose headline result comes mainly from layered leveraged ETF exposure, static universes, and tightly tuned RSI thresholds.
