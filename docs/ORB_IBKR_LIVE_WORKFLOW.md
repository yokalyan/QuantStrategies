# ORB IBKR Live Workflow

This is the intended human-confirmed live flow for the 15-minute TQQQ midpoint-stop ORB strategy.

## Flow

1. Start TWS or IB Gateway and log in to the intended account.
2. Enable API socket access in TWS or IB Gateway.
3. Start this script before the open or before the signal time.
4. The script waits until the first 15 regular-session bars should be complete.
5. Just after 09:45 ET, it pulls recent TQQQ one-minute bars from IBKR.
6. It calculates the opening range, ATR20, OR/ATR20 filter, trade direction, share size, entry stop, stop loss, target, and breakeven trigger.
7. If there is no trade, it exits.
8. If there is a trade, it prints the full bracket order and asks for typed confirmation.
9. With `--transmit`, the script submits a DAY stop-entry bracket to IBKR after confirmation.

The command defaults to paper-trading port `7497` and dry-run mode. Dry-run mode prints the bracket but does not send orders.

## Install Live Dependency

```bash
python -m pip install ".[live]"
```

## Paper Dry Run

```bash
python -m backtest_engine.cli live-orb-ibkr configs/midpoint_stop_orb_intraday.yaml --capital 5000
```

## Paper Order Submission

```bash
python -m backtest_engine.cli live-orb-ibkr configs/midpoint_stop_orb_intraday.yaml --capital 5000 --transmit
```

The confirmation prompt requires an exact string like:

```text
YES TQQQ 113
```

## Live Account Submission

Only after paper testing:

```bash
python -m backtest_engine.cli live-orb-ibkr configs/midpoint_stop_orb_intraday.yaml --capital 5000 --port 7496 --account YOUR_ACCOUNT_ID --transmit
```

## Important Current Limitation

The submitted IBKR order is a DAY bracket:

- Parent: stop-entry order.
- Child: profit-taking limit order.
- Child: protective stop order.

The printed strategy plan still includes a 6R breakeven stop move and a 15:30 ET flatten. Those require an active order-management loop after entry. Until that is implemented and paper-tested, manage those two steps manually in TWS or run the script only as a confirmed entry/bracket assistant.

## Safety Defaults

- Paper port `7497` is the default.
- Orders are not sent unless `--transmit` is present.
- Confirmation is required unless `--no-confirm` is explicitly supplied.
- TWS/IB Gateway order state should always be checked manually after submission.
