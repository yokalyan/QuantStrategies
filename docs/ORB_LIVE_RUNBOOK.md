# ORB Live Runbook

This runbook is for the TQQQ midpoint-stop opening-range breakout signal.

## 9:45 Signal Command

After the first fifteen regular-session one-minute bars are available, run:

```bash
python -m backtest_engine.cli orb-signal configs/midpoint_stop_orb_intraday.yaml --capital 5000
```

For testing a historical session:

```bash
python -m backtest_engine.cli orb-signal configs/midpoint_stop_orb_intraday.yaml --date 2025-01-31 --capital 5000
```

The command prints:

- Opening range high, low, midpoint, and direction.
- ATR20 from completed prior sessions.
- Opening range / ATR20 filter result.
- Whether to trade or stand down.
- Entry stop, initial stop, 10R target, 6R breakeven trigger, share quantity, estimated risk, and notional.

## Current Trading Rule

The live signal uses the selected full-history research variant:

- Opening range: first 15 regular-session minutes, 09:30 through 09:44 ET.
- Entry window: 09:45 through before 10:30 ET.
- Trade only when `0.20 < opening_range / ATR20 <= 0.35`.
- Keep the original 10R target.
- Move stop to breakeven after 6R.
- Risk 0.6% of the configured capital basis.
- Cap notional at 4x the configured capital basis.
- Flatten any open position at 15:30 ET.

With `--capital 5000`, risk budget is `$30` per trade before slippage.

## Example Signal

Historical example:

```bash
python -m backtest_engine.cli orb-signal configs/midpoint_stop_orb_intraday.yaml --date 2024-01-03 --capital 5000
```

Output summary:

- Opening range: `47.45 / 46.92 / 47.18`.
- OR/ATR20: `0.3178`, inside the required `0.20-0.35` band.
- Recommendation: prepare contingent or bracket order.
- Entry: `BUY STOP 113 TQQQ @ 47.45`, valid until 10:30 ET.
- Initial stop: `SELL 113 TQQQ @ 47.18`.
- Profit target: `SELL 113 TQQQ @ 50.08`.
- Breakeven trigger: if price reaches `49.03`, move stop to entry `47.45`.
- Estimated total risk: `$29.76`; notional: `$5,361.61`.

## Live Data Requirement

For live use, the command must see current one-minute bars through 09:44 ET plus enough prior sessions to compute ATR20 and the opening-range guardrail. The current config points at a historical file. For production, replace that with an IBKR or other real-time data capture process that writes the same schema:

```text
datetime,open,high,low,close,volume
```

## Important Safety Notes

This command does not place orders. It is an order-preparation tool. Before automating live orders, test in paper trading, add spread/slippage assumptions, handle partial fills, and build order-state reconciliation.
