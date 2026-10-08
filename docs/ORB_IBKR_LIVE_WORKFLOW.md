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
10. After submission, the script keeps running as the day manager.
11. If the entry has not filled by 10:30 ET, it cancels the bracket.
12. If the entry fills, it polls TQQQ every 60 seconds by default.
13. If price reaches 6R, it cancels the original protective stop and submits a replacement stop at breakeven.
14. At 15:30 ET, it cancels remaining exits and submits a market order to flatten any remaining position.

The command defaults to paper-trading port `7497`, dry-run mode, and active order management. Dry-run mode prints the bracket but does not send orders or start the manager.

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

The confirmation prompt requires typing:

```text
yes
```

## Live Account Submission

Only after paper testing:

```bash
python -m backtest_engine.cli live-orb-ibkr configs/midpoint_stop_orb_intraday.yaml --capital 5000 --port 7496 --account YOUR_ACCOUNT_ID --transmit
```

## Order Manager

The submitted IBKR order is a DAY bracket:

- Parent: stop-entry order.
- Child: profit-taking limit order.
- Child: protective stop order.

After a fill, the manager keeps the process attached to IBKR. It uses the same strategy levels printed in the signal sheet:

- No fill by 10:30 ET: cancel the parent and attached exits.
- 6R reached: cancel the existing stop and submit a replacement stop at the entry price.
- 15:30 ET: cancel remaining exits and submit a market flatten order for any remaining TQQQ position.

The default polling interval is 60 seconds. You can change it:

```bash
python -m backtest_engine.cli live-orb-ibkr configs/midpoint_stop_orb_intraday.yaml --capital 5000 --transmit --poll-seconds 30
```

The process must stay running all day for these management steps to happen.

## Off-Hours Paper Testing

To test the entire IBKR connection, signal computation, order construction, and order manager outside regular market hours (e.g. evenings or weekends), use `--off-hours-test`:

```bash
python -m backtest_engine.cli live-orb-ibkr configs/midpoint_stop_orb_intraday.yaml --capital 5000 --off-hours-test
```

With paper transmission:

```bash
python -m backtest_engine.cli live-orb-ibkr configs/midpoint_stop_orb_intraday.yaml --capital 5000 --off-hours-test --transmit
```

### Safety Protections for `--off-hours-test`:
- **Paper Trading Only**: The script strictly checks that the port is paper trading (`7497` or `4002`) or the account is a paper account (`DU...` or `DF...`). If run against a live port (`7496`), it raises a hard safety exception and halts immediately.
- **Relaxed Timing**: Bypasses the 09:45 morning wait, uses the most recent completed regular-session 1-minute bars to calculate the opening range, permits bracket order generation outside the 09:45–10:30 window, and bypasses wall-clock 10:30 expiration and 15:30 flattening so you can observe the manager in action.

## Safety Defaults

- Paper port `7497` is the default.
- Orders are not sent unless `--transmit` is present.
- Confirmation is required unless `--no-confirm` is explicitly supplied.
- Order management is enabled unless `--no-manage` is explicitly supplied.
- Off-hours testing `--off-hours-test` is strictly blocked on live accounts.
- TWS/IB Gateway order state should always be checked manually after submission.

