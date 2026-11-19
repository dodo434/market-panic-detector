# Market Predictor Price

The project now includes a unified quantitative workstation: a FastAPI backend
combines the existing market-correlation engine with quantum-inspired price
forecasting, financial-news sentiment/correlation, and extreme-event tail-risk
signals. A Vue 3/Vite dark-mode frontend provides the dashboard and local AI
copilot.

## Unified platform quick start

```bash
cp .env.example .env
python3 -m pip install -e ".[dev,web]"
make install-frontend
./run.sh
```

Open `http://localhost:5173`. The API is available at `http://localhost:8000`
and its health endpoint is `http://localhost:8000/api/health`.

The backend works without external market credentials by using a deterministic
offline data fallback. Alpaca/yfinance adapters can be enabled for live
historical data. Configure a local Ollama-compatible runtime in `.env`:

```dotenv
LOCAL_LLM_PROVIDER=ollama
LOCAL_LLM_BASE_URL=http://localhost:11434
LOCAL_LLM_MODEL=qwen2.5:7b
```

The local copilot remains usable in offline mode with built-in analysis tools:
forecast, sentiment, extreme-event risk, and full synthesis.

## Architecture

```text
backend/core/quantum_predictor/  Forecast distribution and uncertainty bands
backend/core/sentiment_engine/   Headline/sentiment and return correlation
backend/core/extreme_events/     Lagged tail-risk features and regime scoring
backend/core/pipeline.py         Concurrent cached orchestration
backend/agent/                    Local copilot runtime and tool registry
backend/api/                      FastAPI health, analysis, and streaming routes
frontend/                         Vue 3/Vite dark quantitative workstation
```

The three engines share typed Pydantic contracts and a common OHLCV provider.
Repeated requests are cached in memory, and independent engine execution uses
a bounded thread pool so API requests do not serialize CPU work.

## Verification

```bash
pytest tests/integration/test_api.py
npm --prefix frontend run build
```

The original PySide6 desktop application and CLI remain available through
their existing entry points while the web workstation is adopted.
