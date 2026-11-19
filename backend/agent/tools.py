from __future__ import annotations

from backend.core.pipeline import MarketPipeline


class ToolRegistry:
    def __init__(self, pipeline: MarketPipeline) -> None:
        self.pipeline = pipeline

    def run_quantum_prediction(self, asset: str, horizon: int = 10) -> dict:
        return self.pipeline.run(asset, horizon).quantum.model_dump()

    def analyze_news_sentiment(self, asset: str, lookback_days: int = 30) -> dict:
        return self.pipeline.run(asset, 10, lookback_days=lookback_days).sentiment.model_dump()

    def detect_extreme_events(self, asset: str, timeframe: str = "1d") -> dict:
        return self.pipeline.run(asset, 10, timeframe).extreme_events.model_dump()

    def run_full_market_synthesis(self, asset: str, horizon: int = 10) -> dict:
        return self.pipeline.run(asset, horizon).model_dump(mode="json")
