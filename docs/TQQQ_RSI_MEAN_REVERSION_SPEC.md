# TQQQ RSI Mean Reversion Spec

This strategy was translated from pasted sample code and prose into the independent engine.

## Rules

- Start date: 2020-01-01.
- End date: 2026-05-12.
- Starting capital: 25,000 USD, following the code value.
- Universe: TQQQ and UVXY.
- Signal: 10-day simple RSI of TQQQ.
- If TQQQ RSI is greater than 79, target 100% UVXY.
- Otherwise target 100% TQQQ.
- Rebalance daily.

## Source Summary Metrics

The pasted comments report annualized return of 84.3%, Sharpe ratio of 1.27, and max drawdown of -81.7%. These are reference values only; the independent backtest is not tuned to match them.

## Fidelity Notes

The sample schedules shortly after market open using the platform's daily indicator state. The independent engine uses data visible through close of day `t` and fills at the next open. This is a conservative no-look-ahead translation and may differ materially from same-morning execution.
