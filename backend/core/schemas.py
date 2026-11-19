from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    asset: str = Field(default="AAPL", min_length=1, max_length=12, pattern=r"^[A-Za-z0-9.^-]+$")
    timeframe: str = "1d"
    horizon: int = Field(default=10, ge=1, le=90)
    lookback_days: int = Field(default=180, ge=30, le=2000)


class ForecastPoint(BaseModel):
    date: str
    expected: float
    lower: float
    upper: float


class QuantumResult(BaseModel):
    asset: str
    current_price: float
    expected_price: float
    expected_return: float
    confidence: float
    forecast: list[ForecastPoint]
    method: str = "quantum-inspired Monte Carlo"


class SentimentResult(BaseModel):
    asset: str
    score: float
    correlation: float
    headlines: list[dict[str, Any]]
    sample_size: int


class ExtremeEventResult(BaseModel):
    asset: str
    risk_probability: float
    regime: str
    anomaly: bool
    threshold: float
    features: dict[str, float]
    model: str


class PipelineResult(BaseModel):
    asset: str
    generated_at: datetime
    quantum: QuantumResult
    sentiment: SentimentResult
    extreme_events: ExtremeEventResult
    synthesis: str


class AgentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    asset: str = "AAPL"
    horizon: int = Field(default=10, ge=1, le=90)
    session_id: str = "default"
