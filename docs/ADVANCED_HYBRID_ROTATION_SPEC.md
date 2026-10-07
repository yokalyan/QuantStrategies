# Advanced Hybrid Rotation Spec

This strategy was translated from pasted sample code into the independent engine.

## Engines

The strategy combines two engines:

- All-weather core rotation, initially 60% of portfolio.
- Enhanced satellite strategy, initially 40% of portfolio.

SPY realized volatility scales both budgets daily. Core exposure is reduced when volatility is above the 15% target and is not levered above its base budget. Satellite exposure is scaled by the same target-vol ratio, capped by the configured 1.0 leverage cap.

## Core Rotation

Every five trading sessions, the core ranks a broad ETF universe by 60-day ROC. A symbol is eligible when price is above its 200-day SMA and ROC is positive. BIL is always eligible with score zero. The top five selected symbols share the current core budget equally.

## Satellite Tree

The satellite runs daily on SPY, QQQ, TQQQ, UVXY, TECL, SPXL, SQQQ, TECS, and BSV using 10-day Wilder RSI plus SPY 200-day and TQQQ 20-day SMAs.

In bull regimes, QQQ/SPY overbought readings move the sleeve to UVXY; very overbought TQQQ moves to BSV; otherwise it holds TQQQ. In bear regimes, oversold TQQQ or SPY can select TECL or SPXL, high UVXY RSI selects UVXY, a TQQQ 20-day trend branch selects TECS/TECL, and otherwise BSV is held.

## Fidelity Notes

The sample adjusts mutable base allocation variables after trading inside `OnData`; this implementation computes the volatility-scaled budgets before producing targets each day. This is a small timing difference but keeps target generation deterministic inside the independent engine.
