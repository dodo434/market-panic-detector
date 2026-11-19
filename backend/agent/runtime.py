from __future__ import annotations

import os
from collections import defaultdict
from typing import Iterator

import httpx

from backend.agent.tools import ToolRegistry


class LocalAgent:
    def __init__(self, tools: ToolRegistry) -> None:
        self.tools = tools
        self.base_url = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434").rstrip("/")
        self.model = os.getenv("LOCAL_LLM_MODEL", "qwen2.5:7b")
        self.history: dict[str, list[dict[str, str]]] = defaultdict(list)

    def health(self) -> dict[str, str | bool]:
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=1.5)
            response.raise_for_status()
            return {"online": True, "provider": os.getenv("LOCAL_LLM_PROVIDER", "ollama"), "model": self.model}
        except Exception as exc:
            return {"online": False, "provider": os.getenv("LOCAL_LLM_PROVIDER", "ollama"), "model": self.model, "error": str(exc)}

    def stream(self, session_id: str, message: str, asset: str, horizon: int) -> Iterator[str]:
        lower = message.lower()
        if "full" in lower or "synthesis" in lower:
            result = self.tools.run_full_market_synthesis(asset, horizon)
            text = result["synthesis"]
        elif "sentiment" in lower or "news" in lower:
            result = self.tools.analyze_news_sentiment(asset)
            text = f"Sentiment for {asset}: score {result['score']:.2f}, correlation {result['correlation']:.2f}."
        elif "risk" in lower or "extreme" in lower or "crash" in lower:
            result = self.tools.detect_extreme_events(asset)
            text = f"Tail-risk probability for {asset}: {result['risk_probability']:.1%}; regime {result['regime']}."
        else:
            result = self.tools.run_quantum_prediction(asset, horizon)
            text = f"{asset} expected price is {result['expected_price']:.2f}, return {result['expected_return']:.1%}, confidence {result['confidence']:.0%}."
        self.history[session_id].extend([{"role": "user", "content": message}, {"role": "assistant", "content": text}])
        for token in text.split():
            yield token + " "
