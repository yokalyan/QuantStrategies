# Strategy Spec: Weekly QQQ Kelly Momentum Leaders

Source URL: `https://www.quantconnect.com/strategies/472/Weekly-QQQ-Kelly-Momentum-Leaders`

## Source Intake

The public URL returned a QuantConnect terminal shell and did not expose rules, parameters, code, or source-reported performance statistics. Search results did not reveal a reliable copy of the exact strategy. The baseline below is an assumption-based reconstruction from the title and must not be treated as a verified QuantConnect reproduction.

## Thesis

[ASSUMED] Each week, hold a concentrated basket of current large NASDAQ/QQQ-style stocks with positive intermediate-term momentum. Size selected names using a bounded Kelly-style estimate from trailing returns, so stronger risk-adjusted trends receive larger weights.

## Universe

[ASSUMED] Static liquid QQQ-like technology and growth tickers listed in the config. This is not point-in-time and has survivorship bias.

## Data Frequency and Schedule

[ASSUMED] Daily adjusted OHLCV bars. Signals are evaluated at each Monday close, or the first available trading day after a market holiday, and filled at the next session open.

## Signals

[ASSUMED] Momentum is trailing total return over `momentum_lookback` trading days using adjusted closes. Volatility is annualized daily return standard deviation over `volatility_lookback` days. Expected annual return is the annualized mean of trailing daily returns over `kelly_lookback`.

## Ranking and Selection

[ASSUMED] Eligible symbols must have positive momentum. Rank by Kelly score `expected_annual_return / annualized_variance`, select the top `top_n`.

## Sizing

[ASSUMED] Convert positive Kelly scores into proportional weights, multiply by `kelly_fraction`, cap each position at `max_position_weight`, then renormalize to at most `max_gross_exposure`. Unused capital remains cash.

## Costs and Fills

[ASSUMED] Fills occur at next open with 1 basis point slippage and $0.005/share commission, $1 minimum per fill.

## Reported Performance

[STATED] No source performance was obtainable from the public page fetch.

## Assumption Ledger

| Assumption | Value chosen | Why | Impact if wrong | Sensitivity tested? |
| --- | --- | --- | --- | --- |
| Universe | Static config list | No point-in-time QQQ constituents available from source | High survivorship bias | Partial |
| Momentum lookback | 63 trading days | Common quarterly momentum horizon | High | Yes |
| Kelly lookback | 252 trading days | One trading year | High | Yes |
| Rebalance | Weekly Monday close | Title says weekly | Medium | Yes |
| Fill | Next open | Avoids look-ahead | Medium | Cost/timing stress |
| Kelly cap | 25% per name | Avoids extreme estimated Kelly weights | High | Yes |

## Fidelity Risks

LEAN data normalization, scheduling, corporate-action handling, fill models, and any proprietary QuantConnect universe data are not reproduced. The engine uses adjusted yfinance data and static user-configured universes. Any comparison to QuantConnect output would require the original rules and source statistics.

