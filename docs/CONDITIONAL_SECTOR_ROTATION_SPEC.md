# Conditional Sector Rotation Spec

This strategy was translated from pasted sample code into the independent engine's strategy interface.

## Rules

- Start date: 2012-01-01.
- Starting capital: 100,000 USD.
- Universe: SPY, QQQ, TQQQ, UVXY, TECL, SPXL, SQQQ, TECS, BSV.
- Indicators: 10-day Wilder RSI for every asset; 200-day SMA for SPY; 20-day SMA for QQQ and TQQQ.
- Decision frequency: daily after enough history exists.
- Execution: decide with data through close of day `t`, fill target allocation at next session open.
- Sizing: 100% target weight in the selected ETF, liquidating other positions.

## Target Tree

If SPY close is above its 200-day SMA:

- If QQQ 10-day RSI is above 81, hold UVXY.
- Else if SPY 10-day RSI is above 80, hold UVXY.
- Else hold TQQQ.

If SPY close is at or below its 200-day SMA:

- If TQQQ 10-day RSI is below 30, hold TECL.
- Else if SPY 10-day RSI is below 30, hold SPXL.
- Else if UVXY 10-day RSI is above 74:
  - If UVXY 10-day RSI is above 84:
    - If QQQ close is above its 20-day SMA:
      - If SQQQ 10-day RSI is below 31, hold TECS.
      - Else hold TECL.
    - Else hold whichever of TECS or BSV has the higher 10-day RSI.
  - Else hold UVXY.
- Else:
  - If TQQQ close is above its 20-day SMA:
    - If SQQQ 10-day RSI is below 34, hold TECS.
    - Else hold TECL.
  - Else hold whichever of TECS or BSV has the higher 10-day RSI.

## Fidelity Notes

The implementation does not reproduce platform-specific data normalization, broker fill behavior, or order-sizing internals. It uses locally cached yfinance adjusted daily OHLCV bars and explicit next-open fills.
