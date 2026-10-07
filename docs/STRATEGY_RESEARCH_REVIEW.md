# Strategy Research Review

This memo reviews the independent backtests currently saved in `results/`. It is not investment advice; it is a research triage note about which ideas deserve more work and which results look mostly like leverage, data-mining, or bull-market exposure.

## Executive Verdict

The strongest-looking headline curves are mostly the strategies with concentrated leveraged ETF exposure and volatility/inverse ETF switching. Those may contain useful tactical ideas, but the raw strategies are not production-ready: the best returns come with high turnover, embedded leverage, dependence on 2020-2026 market structure, and in several cases static/survivorship-biased universes.

The ideas worth studying further are not the full recipes. The reusable pieces are: regime-gated momentum, inverse-volatility sizing, residual defensive allocation, explicit volatility targeting, ensemble diversification across independent signals, and now the opening-range intraday pattern tested on real minute data. The least convincing pieces are binary UVXY switches, extreme leveraged ETF concentration, and strategies whose performance depends on one narrow threshold.

## Headline Metrics

| Strategy | CAGR | Vol | Sharpe | Max DD | Calmar | Beta | Trades/Fills | Costs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Quad Ensemble | 189.1% | 52.7% | 2.28 | -34.0% | 5.57 | 1.30 | 6985 | $103,511 |
| Advanced Hybrid Rotation | 48.0% | 29.6% | 1.48 | -24.6% | 1.95 | 0.76 | 9483 | $112,205 |
| Conditional Sector Rotation | 97.6% | 59.3% | 1.44 | -53.2% | 1.83 | 1.65 | 615 | $10,943,065 |
| Midpoint Stop ORB Intraday | 34.3% | n/a | 1.34 | -16.1% | n/a | n/a | 1774 | $0 |
| Tech Momentum GLD Sweep | 32.4% | 25.2% | 1.24 | -40.9% | 0.79 | 0.96 | 22501 | $27,014 |
| Volatility Harvest Long/Short | 20.8% | 18.2% | 1.13 | -29.5% | 0.71 | 0.68 | 11542 | $22,282 |
| Omniscient Paradox | 51.5% | 50.4% | 1.08 | -47.8% | 1.08 | 0.64 | 942 | $51,547 |
| QQQ Kelly Momentum Leaders | 20.1% | 20.2% | 1.01 | -32.9% | 0.61 | 0.71 | 3079 | $8,130 |
| TQQQ RSI Mean Reversion | 34.9% | 74.1% | 0.78 | -81.5% | 0.43 | 0.92 | 209 | $1,716 |
| Macro Factor Rotation | 10.4% | 14.8% | 0.75 | -23.6% | 0.44 | 0.34 | 209 | $415 |

Note: Midpoint Stop ORB Intraday uses the provided local one-minute file and covers 2021-01-04 through 2025-06-02, so it is more comparable than the earlier tiny Yahoo sample but still needs spread/slippage modeling.

## Stress Windows

| Strategy | COVID Window | 2022 Rate Bear | 2023-2026 Bull/AI Window |
| --- | ---: | ---: | ---: |
| Advanced Hybrid Rotation | 27.2% | -14.3% | 343.8% |
| Conditional Sector Rotation | -1.3% | 79.3% | 1142.5% |
| Macro Factor Rotation | -0.3% | -7.6% | 80.6% |
| Midpoint Stop ORB Intraday | n/a | 25.8% | 114.4% |
| Omniscient Paradox | 3.2% | 80.1% | 426.2% |
| QQQ Kelly Momentum Leaders | -7.3% | -30.5% | 102.1% |
| Quad Ensemble | -14.1% | 310.8% | 6848.2% |
| TQQQ RSI Mean Reversion | -25.4% | -79.5% | 721.9% |
| Tech Momentum GLD Sweep | -0.7% | -35.0% | 330.2% |
| Volatility Harvest Long/Short | 11.9% | -26.5% | 230.7% |

## Strategy-by-Strategy Read

### Quad Ensemble
Very high headline performance, but also a classic danger zone: many leveraged, inverse, volatility, and short-volatility products with layered RSI/SMA thresholds. The concept of combining independent sleeves is good; the exact recipe is likely overfit. The eye-catching CAGR is not a clean alpha estimate because the strategy is structurally long convexity to tech/semis and short-vol/risk-on in a period that rewarded those exposures.
Recent annual returns: 2022: 310.8%, 2023: 229.9%, 2024: 392.0%, 2025: 111.4%, 2026: 111.7%.

### Conditional Sector Rotation
A high-octane leveraged ETF decision tree. It may exploit some real short-term mean-reversion/regime behavior, but the enormous return and 53% drawdown say this is closer to a tactical leveraged product timing system than a durable all-weather strategy. Needs walk-forward threshold testing before trusting anything.
Recent annual returns: 2022: 79.3%, 2023: 134.8%, 2024: 70.7%, 2025: 91.2%, 2026: 73.1%.

### Advanced Hybrid Rotation
One of the more interesting frameworks. The core/satellite split and SPY volatility targeting are useful design ideas. Still, the satellite is another leveraged ETF timing tree, and the high trade count/costs show implementation friction matters.
Recent annual returns: 2022: -14.3%, 2023: 65.1%, 2024: 36.1%, 2025: 51.5%, 2026: 32.0%.

### Omniscient Paradox
The reusable part is risk-adjusted momentum plus hysteresis and a safe asset. The current version remains dominated by leveraged ETFs and has nearly 48% drawdown, so it is not conservative, but its lower market correlation suggests it is worth studying as a component rather than a standalone allocation.
Recent annual returns: 2022: 80.1%, 2023: 103.5%, 2024: 45.4%, 2025: -18.1%, 2026: 125.1%.

### Tech Momentum GLD Sweep
Conceptually clean: cross-sectional momentum, inverse-vol sizing, and GLD residual allocation. The static tech universe introduces survivorship bias, and the trade count is too high because stops/sweeps alter targets daily. Worth rebuilding with point-in-time membership and lower turnover constraints.
Recent annual returns: 2022: -35.0%, 2023: 53.5%, 2024: 38.5%, 2025: 33.5%, 2026: 53.7%.

### Volatility Harvest Long/Short
The long/short framing is promising, but the independent version had to replace QuantConnect fundamentals with static universes. The Hurst/ATR short sleeve is worth studying separately, especially as a risk overlay, but borrow availability, short fees, and margin modeling are missing.
Recent annual returns: 2022: -26.5%, 2023: 51.0%, 2024: 60.4%, 2025: 23.3%, 2026: 12.2%.

### QQQ Kelly Momentum Leaders
Decent risk-adjusted result, but the original source rules were unavailable, so this is an assumed reconstruction. Kelly-style sizing from noisy return estimates is fragile; inverse-vol or capped rank weights may be more robust.
Recent annual returns: 2022: -30.5%, 2023: 19.4%, 2024: 45.9%, 2025: 17.5%, 2026: 0.7%.

### Macro Factor Rotation
This is the most intellectually plausible as a diversified tactical allocator, but the results are modest. That is not a bad sign: lower beta, lower drawdown, and realistic return profile make it a better candidate for serious research than the extreme leveraged ETF systems.
Recent annual returns: 2022: -7.6%, 2023: 19.9%, 2024: 19.1%, 2025: 33.7%, 2026: -5.7%.

### TQQQ RSI Mean Reversion
Simple, transparent, and brutally risky. The max drawdown around -81% confirms the key issue: binary switching between TQQQ and UVXY can work spectacularly sometimes and still be uninvestable for many users. Useful as a signal study, not as a full strategy.
Recent annual returns: 2022: -79.5%, 2023: 155.2%, 2024: 118.5%, 2025: 41.1%, 2026: 11.5%.

### Midpoint Stop ORB Intraday
Now materially more interesting because the provided 1-minute file allowed a 2021-2025 run: about 34% CAGR, Sharpe 1.34, and -16% max drawdown before spread/slippage. This is one of the few ideas here that is not just daily leveraged ETF beta. It still needs bid/ask spread, market impact, stop execution using high/low path assumptions, and validation on other leveraged ETFs or QQQ/SPY before calling it robust.
Recent annual returns: 2021: 35.1%, 2022: 25.8%, 2023: 12.2%, 2024: 63.1%, 2025: 13.7%.

## What Looks Like Real Alpha?

Possible alpha exists in components, not in most raw end-to-end recipes. Cross-sectional momentum with inverse-vol sizing has prior support and the tech/GLD strategy is the cleanest expression here, although it needs point-in-time validation. Regime filters using long moving averages and volatility targeting appear useful mostly because they control exposure. The macro factor model may have weak but diversifying signal. The ORB intraday strategy is also worth studying now that it has a multi-year minute-bar result, but microstructure costs could erase a meaningful part of it.

The most suspicious “alpha” is binary switching into UVXY/UVIX based on RSI thresholds. Volatility ETPs decay, have path-dependent behavior, and can be extremely sensitive to one or two crash periods. If the signal only works at RSI 79/81/85 and fails nearby, it is probably tuned noise.

## What Will Likely Fail In A Bear Market?

Anything structurally leaning on TQQQ, SOXL, TECL, short-volatility, or high-beta tech will likely suffer in prolonged bear or sideways markets unless the defensive switch is both timely and cheap. The TQQQ RSI strategy already shows the warning: huge return but an -81% drawdown. Strategies with 30-50% drawdowns while using daily data and optimistic fills can be materially worse live.

The best bear-market candidates are not necessarily the highest-return systems. Macro Factor Rotation, Volatility Harvest Long/Short, the ORB intraday pattern, and parts of Advanced Hybrid Rotation have explicit diversification, hedging, or flat-by-close behavior. They still need realistic costs, borrow assumptions, and out-of-sample testing.

## Improvements To Prioritize

1. Add walk-forward testing and parameter grids for RSI thresholds, SMA lengths, lookbacks, ORB R-multiples, and rebalance timing. Do not trust a single threshold.
2. Add out-of-sample splits: 2015-2019 design, 2020-2022 stress, 2023-2026 validation where data permits.
3. Replace static universes with point-in-time or at least frozen-at-start universes to estimate survivorship bias.
4. Model ETF borrow/financing, margin interest, short availability, spreads, and market impact for leveraged/inverse/volatility ETPs.
5. Reduce turnover with no-trade bands, monthly lockouts, signal persistence requirements, or target drift bands.
6. Convert the best full strategies into reusable overlays: volatility target, trend gate, inverse-vol sizing, GLD/BIL residual sleeve, and crash-risk throttle.
7. For ORB, replay entries/exits with high/low-aware stop/target sequencing and add spread/slippage per fill.

## Worth Studying Further

Most worth deeper study: Midpoint Stop ORB Intraday, Macro Factor Rotation, Tech Momentum GLD Sweep, Advanced Hybrid Rotation, and the Omniscient Paradox scoring framework. Use them as idea libraries, not production systems.

Worth studying only as signals/overlays: TQQQ RSI Mean Reversion, Conditional Sector Rotation, Quad Ensemble volatility/overbought sleeves, and the UVXY switch branches.

Least trustworthy as-is: any strategy whose headline result comes mainly from layered leveraged ETF exposure, static universes, and tightly tuned RSI thresholds. They can be useful research prompts, but someone should not allocate capital to them without a much harsher validation stack.
