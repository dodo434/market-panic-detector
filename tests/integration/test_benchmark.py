"""Run the real GUI in a new process against a repeatable, warmed 50-stock cache."""

import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
import pandas as pd
from panic_detector.config import load_settings
from panic_detector.data import alpaca_client
from panic_detector.service import snapshot


def test_warm_start_and_frames(tmp_path, monkeypatch):
    tickers = load_settings().universe
    rng = np.random.default_rng(9)
    common = rng.normal(size=(650, 1))
    moves = 0.01 * (rng.normal(size=(650, len(tickers))) + common)
    prices = pd.DataFrame(
        np.exp(moves.cumsum(axis=0)),
        columns=tickers,
        index=pd.bdate_range("2019-01-01", periods=650),
    )
    monkeypatch.setattr(alpaca_client, "fetch", lambda *args: prices)
    snapshot(tickers, 60, True, root=tmp_path)
    env = os.environ.copy()
    if sys.platform.startswith("linux") and not (env.get("DISPLAY") or env.get("WAYLAND_DISPLAY")):
        env["QT_QPA_PLATFORM"] = "offscreen"
    script = Path(__file__).resolve().parents[2] / "scripts/benchmark.py"
    result = subprocess.run(
        [sys.executable, str(script), "--cache-root", str(tmp_path), "--frames", "60", "--check"],
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["frames"] == 60 and report["startup_s"] < 2 and report["max_ms"] <= 16
