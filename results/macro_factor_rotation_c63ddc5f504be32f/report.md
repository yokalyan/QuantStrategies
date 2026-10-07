# Macro Factor Cross Asset Rotation Baseline

## Metrics
- `total_return`: 115.51%
- `cagr`: 10.41%
- `annual_volatility`: 14.78%
- `sharpe`: 0.746
- `sortino`: 0.885
- `calmar`: 0.440
- `max_drawdown`: -23.65%
- `max_drawdown_duration_days`: 835.00
- `best_day`: 5.55%
- `worst_day`: -9.12%
- `number_of_trades`: 209.00
- `total_costs`: 415.36
- `beta`: 0.339
- `alpha`: 4.94%
- `correlation`: 0.441

## Assumptions And Caveats
- The pasted sample was translated as a specification; no external engine code is imported.
- FRED CSVs provide VIXCLS, T10Y3M, and DFF factor history; yfinance provides adjusted ETF and BTC-USD bars.
- Monthly decisions use data through the first equity trading day of the month and fill at the next open, which is more conservative than same-morning platform scheduling.
- Gross exposure targets 150%; the engine does not model margin interest or crypto exchange financing.
- BTCUSD from the source is represented by yfinance BTC-USD, so crypto market, pricing, and trading-hour conventions differ from the sample.

## Gates
**STAGE 1 GATE: PASS** The pasted description and code specify assets, macro factors, model type, labels, monthly retraining, positive-forecast filter, gross exposure, and bitcoin cap.
**STAGE 2-6 GATE: CONDITIONAL PASS** The strategy ran on independent yfinance/FRED data with next-open execution. Reconciliation to the original platform requires its source data conventions and reported performance.
