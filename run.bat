@echo off
setlocal
if not exist frontend\node_modules (cd frontend && npm install && cd ..)
start "Market Predictor API" cmd /k "python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8000"
cd frontend
npm run dev -- --host 127.0.0.1
