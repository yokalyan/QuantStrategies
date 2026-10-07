# Midpoint Stop Opening Range Breakout Intraday Spec

This strategy was translated from pasted sample code into a dedicated independent intraday runner.

## Rules

- Symbol: TQQQ.
- Start/end in source code: 2021-01-01 to 2026-06-01.
- Opening range: first five one-minute bars, 09:30 through 09:34.
- Direction: long when the opening range closes bullish, short when bearish.
- Entry window: 09:35 through before 10:30.
- Long entry: close breaks above opening range high.
- Short entry: close breaks below opening range low.
- Guardrail: skip if opening range exceeds 2x the rolling 20-session average opening range.
- Stop: opening range midpoint.
- Profit target: 10R.
- Breakeven: move stop to entry after 6R.
- Risk: 0.6% of equity per trade.
- Leverage cap: 4x notional.
- Flatten: 30 minutes before close.

## Data Limitation

The independent yfinance source only provided recent one-minute data. It did not provide the full source period. The saved baseline therefore runs on the available recent complete minute-data window and should not be interpreted as a 2021-2026 strategy backtest.
