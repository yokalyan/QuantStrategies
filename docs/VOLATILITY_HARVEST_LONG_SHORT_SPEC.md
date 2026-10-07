# Volatility Harvest ML Long Short Spec

This strategy was translated from pasted sample code and prose into the independent engine.

## Long Sleeve

The original code selects the four largest U.S. equities by market capitalization each month. The independent version uses the configured basket `AAPL, MSFT, NVDA, AMZN` as the large-cap long sleeve. Gross long exposure defaults to 90%.

The long sleeve uses VIX and SPY regime rules:

- VIX spike plus SPY 5-day drop: mostly long equities, or fully long equities if ML bullish.
- Very low VIX plus extended SPY: reduced equity exposure and GLD exposure.
- VIX above 20 but below its 20-day average: moderate equity exposure.
- VIX more than 20% above its 20-day average: GLD only.
- SPY above its 200-day average: normal risk-on allocation.
- Otherwise: defensive reduced equity and GLD allocation.

A random forest classifier is retrained monthly from VIX/SPY features and a 21-day SPY forward-return label. A bullish prediction tilts the top-symbol allocation toward the first configured long symbol.

## Short Sleeve

The original scans a broad fundamental universe. The independent version scans the configured static liquid universe. Each week, candidates must satisfy:

- Multi-horizon Hurst-style score at or above `0.85`.
- Price extension above a 195-day SMA by more than `2.0 * ATR20`.
- Five-day momentum greater than `1.75 * ATR20`.

The top candidate is shorted at the configured short gross exposure, default 60%. Short entries exit on a `2.0 * entry ATR` adverse move.

## Execution Difference

The sample schedules multiple intraday checks. The independent engine evaluates once per daily bar with data visible through the close and fills at the next open to maintain structural no-look-ahead behavior.

## Fidelity Notes

Fundamental universe selection, margin availability, borrow constraints, market-on-open scheduling, and Interactive Brokers margin modeling are not reproduced. Those differences can materially change short availability, leverage, and turnover.
