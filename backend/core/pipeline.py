from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import threading

from backend.core.data import MarketDataProvider
from backend.core.extreme_events import ExtremeEventDetector
from backend.core.quantum_predictor import QuantumPricePredictor
from backend.core.schemas import PipelineResult
from backend.core.sentiment_engine import SentimentEngine


class MarketPipeline:
    def __init__(self) -> None:
        self.data = MarketDataProvider()
        self.quantum = QuantumPricePredictor()
        self.sentiment = SentimentEngine()
        self.extreme = ExtremeEventDetector()
        self._cache: dict[tuple[str, int, str], PipelineResult] = {}
        self._lock = threading.Lock()

    def run(self, asset: str, horizon: int = 10, timeframe: str = "1d", lookback_days: int = 180) -> PipelineResult:
        key = (asset.upper(), horizon, timeframe)
        with self._lock:
            cached = self._cache.get(key)
        if cached:
            return cached
        frame = self.data.history(asset, lookback_days)
        with ThreadPoolExecutor(max_workers=3) as pool:
            q = pool.submit(self.quantum.predict, asset, frame, horizon)
            s = pool.submit(self.sentiment.analyze, asset, frame, min(lookback_days, 30))
            e = pool.submit(self.extreme.detect, asset, frame, timeframe)
            result = PipelineResult(
                asset=asset.upper(),
                generated_at=datetime.now(timezone.utc),
                quantum=q.result(),
                sentiment=s.result(),
                extreme_events=e.result(),
                synthesis=self._synthesis(q.result().expected_return, s.result().score, e.result().risk_probability),
            )
        with self._lock:
            self._cache[key] = result
        return result

    @staticmethod
    def _synthesis(expected_return: float, sentiment: float, risk: float) -> str:
        if risk >= 0.35:
            return "Tail risk is dominant; treat the forecast as defensive despite other signals."
        if expected_return >= 0 and sentiment >= 0:
            return "Quantum forecast and sentiment agree on a constructive near-term regime."
        if expected_return < 0 and sentiment < 0:
            return "Quantum forecast and sentiment agree on a cautious near-term regime."
        return "Signals diverge; use smaller exposure and monitor the risk regime."
