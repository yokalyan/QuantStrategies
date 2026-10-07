from __future__ import annotations

import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

from backtest_engine.strategy import MarketDataView, Strategy, register_strategy


@register_strategy("macro_factor_rotation")
class MacroFactorRotation(Strategy):
    def target_weights(self, data: MarketDataView, current_weights: dict[str, float]) -> dict[str, float]:
        assets = list(self.params.get("assets", ["SPY", "GLD", "BND", "BTC-USD"]))
        factors = list(self.params.get("factors", ["VIXCLS", "T10Y3M", "DFF"]))
        lookback_days = int(float(self.params.get("lookback_years", 4)) * 365)
        horizon = int(self.params.get("prediction_horizon_days", 21))
        gross_exposure = float(self.params.get("gross_exposure", 1.5))
        max_bitcoin_weight = float(self.params.get("max_bitcoin_weight", 0.1))
        bitcoin_symbol = self.params.get("bitcoin_symbol", "BTC-USD")

        factor_frame = self._aligned_history(data, factors, "close").dropna().iloc[-lookback_days:]
        close_frame = self._aligned_history(data, assets, "close").dropna().iloc[-lookback_days:]
        labels = close_frame.pct_change(horizon).shift(-horizon).dropna()
        latest_factor = factor_frame.iloc[[-1]]
        predictions: dict[str, float] = {}
        for asset in assets:
            asset_labels = labels[asset].dropna()
            idx = factor_frame.index.intersection(asset_labels.index)
            if len(idx) < max(60, horizon * 3):
                continue
            scaler = StandardScaler()
            model = DecisionTreeRegressor(max_depth=int(self.params.get("max_depth", 12)), random_state=int(self.params.get("random_state", 1)))
            model.fit(scaler.fit_transform(factor_frame.loc[idx]), asset_labels.loc[idx])
            prediction = float(model.predict(scaler.transform(latest_factor))[0])
            if prediction > 0:
                predictions[asset] = prediction
        if not predictions:
            return {}

        total_prediction = sum(predictions.values())
        weights = {asset: gross_exposure * prediction / total_prediction for asset, prediction in predictions.items()}
        if weights.get(bitcoin_symbol, 0.0) > max_bitcoin_weight:
            weights[bitcoin_symbol] = max_bitcoin_weight
            redistribute = [asset for asset in assets if asset != bitcoin_symbol and asset in weights]
            equity_total = sum(weights[asset] for asset in redistribute)
            if redistribute and equity_total > 0:
                for asset in redistribute:
                    weights[asset] = gross_exposure * weights[asset] / equity_total
        return weights

    @staticmethod
    def _aligned_history(data: MarketDataView, symbols: list[str], field: str) -> pd.DataFrame:
        return pd.concat([data.history(symbol, field).rename(symbol) for symbol in symbols], axis=1)
