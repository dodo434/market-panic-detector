from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.agent.runtime import LocalAgent
from backend.agent.tools import ToolRegistry
from backend.core.pipeline import MarketPipeline
from backend.core.schemas import AgentRequest, AnalysisRequest

pipeline = MarketPipeline()
agent = LocalAgent(ToolRegistry(pipeline))
app = FastAPI(title="Market Predictor Price API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "engines": {"pipeline": "ready"}, "local_llm": agent.health()}


@app.post("/api/analyze")
def analyze(request: AnalysisRequest):
    return pipeline.run(request.asset, request.horizon, request.timeframe, request.lookback_days)


@app.post("/api/agent/stream")
def agent_stream(request: AgentRequest):
    tokens = agent.stream(request.session_id, request.message, request.asset, request.horizon)
    return StreamingResponse(tokens, media_type="text/plain")
