# ORB Live Runbook

This runbook is for the TQQQ midpoint-stop opening-range breakout signal.

## 9:35 Signal Command

After the first five regular-session one-minute bars are available, run:

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

The live signal uses the best-tested full-history variant:

- Trade only when `0.15 < opening_range / ATR20 <= 0.25`.
- Keep the original 10R target.
- Move stop to breakeven after 6R.
- Risk 0.6% of the configured capital basis.
- Cap notional at 4x the configured capital basis.
- Flatten any open position at 15:30 ET.

With `--capital 5000`, risk budget is `$30` per trade before slippage.

## Live Data Requirement

For live use, the command must see current one-minute bars through 09:34 ET plus enough prior sessions to compute ATR20 and the opening-range guardrail. The current config points at a historical file. For production, replace that with an IBKR or other real-time data capture process that writes the same schema:

```text
datetime,open,high,low,close,volume
```

## Important Safety Notes

This command does not place orders. It is an order-preparation tool. Before automating live orders, test in paper trading, add spread/slippage assumptions, handle partial fills, and build order-state reconciliation.

