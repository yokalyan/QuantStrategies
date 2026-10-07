# Quad Ensemble Tactical Allocation Spec

This strategy was translated from pasted sample code and prose into the independent engine.

## Structure

The strategy combines four sleeves, each with a 25% capital budget:

- T10 / SimonsKMLM.
- T11 / FeaverFrontrunner.
- S2 / HolyGrail.
- S3 / DailyRegimeRotation.

Each sleeve independently returns a target allocation. Overlapping target symbols are summed before execution.

## Sleeve Summary

T10 uses RSI exhaustion checks across broad equity, value, growth, sector, and leveraged ETFs. Overbought regimes allocate to UVXY; dip-buy conditions allocate to TECL, SOXL, SPXL, or LABU. Otherwise, XLK versus KMLM relative strength controls risk-on TECL/SOXL/short-vol exposure versus SQQQ/TLT defense.

T11 applies similar RSI overbought and dip-buy logic, then uses SPY 200-day trend, XLK/KMLM comparison, KMLM 20-day trend, bond/inverse-equity RSI comparisons, and QQQ 60-day drawdown checks to choose bull, inverse, bond, or managed-futures-like branches.

S2 uses a TQQQ 200-day SMA gate. In bull regimes it switches between TQQQ and UVXY based on TQQQ 10-day RSI. In weaker regimes it uses TQQQ/SOXL oversold checks, TQQQ 20-day SMA, and SQQQ versus BSV RSI.

S3 uses a 3-of-4 vote from SPY, QQQ, SMH, and SOXL against 202-day SMAs. Bull regimes hold TQQQ/SOXL unless 15-day RSI exhaustion sends the sleeve to UVIX or UVXY. Bear regimes can dip-buy SOXL on QQQ or SMH short-term RSI weakness, otherwise staying in cash.

## Fidelity Notes

The sample uses platform market-on-open orders and daily `on_data` timing. The independent engine uses data visible through close of day `t` and fills at next open. This preserves no-look-ahead behavior but changes timing versus the sample.
