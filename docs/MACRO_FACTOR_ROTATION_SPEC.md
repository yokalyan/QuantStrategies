# Macro Factor Cross Asset Rotation Spec

This strategy was translated from pasted sample code and prose into the independent engine.

## Thesis

A compact set of macro and risk-regime factors can help forecast near-term relative returns for equities, gold, bonds, and bitcoin. The strategy retrains a decision tree each month and allocates only to assets with positive predicted 21-trading-day returns.

## Universe

- SPY: US equities.
- GLD: gold.
- BND: US aggregate bonds.
- BTC-USD: yfinance proxy for BTCUSD.

## Factors

- VIXCLS: CBOE VIX close from FRED.
- T10Y3M: 10-year Treasury minus 3-month Treasury slope from FRED.
- DFF: effective federal funds rate from FRED.

## Model And Labels

At each monthly rebalance, the model uses a rolling four-year daily lookback. Features are standardized macro factor values. Labels are each asset's 21-day forward return. A `DecisionTreeRegressor(max_depth=12, random_state=1)` is fit separately for each asset.

## Portfolio Construction

Only assets with positive predicted returns are eligible. Weights are proportional to positive prediction magnitude and target 150% gross exposure. BTC-USD is capped at 10%; excess exposure is redistributed across eligible non-bitcoin assets following the sample's behavior.

## Execution Difference

The sample schedules rebalancing shortly after market open at month start. This independent engine decides with data visible through that date and fills on the next open to keep look-ahead prevention structural.
