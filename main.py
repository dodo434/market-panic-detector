"""Market Panic Detector desktop/CLI entry point."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from data import DEFAULT_TICKERS, compute_log_returns, download_alpaca_bars
from metrics import rolling_metrics
from network import fixed_layout
from plots import STRESS_PERIODS, animate, plot_metrics, static_comparison


def find_calm_and_crash(metrics: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Choose the lowest-correlation calm date and peak-Covid date."""
    calm_date = pd.Timestamp(metrics["average_correlation"].idxmin())
    covid = metrics.loc[
        (metrics.index >= pd.Timestamp(STRESS_PERIODS[0][1]))
        & (metrics.index <= pd.Timestamp(STRESS_PERIODS[0][2]))
    ]
    crash_date = pd.Timestamp(covid["average_correlation"].idxmax()) if not covid.empty else pd.Timestamp(
        metrics["average_correlation"].idxmax()
    )
    return calm_date, crash_date


def matrix_for_date(
    matrices: dict[tuple[pd.Timestamp, pd.Timestamp], pd.DataFrame],
    date: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.Timestamp]:
    exact = [(end, corr) for (_, end), corr in matrices.items() if end == date]
    if exact:
        return exact[0][1], exact[0][0]
    nearest = min(matrices.items(), key=lambda item: abs(item[0][1] - date))
    end = nearest[0][1]
    return nearest[1], end


def summarize(
    metrics: pd.DataFrame,
    calm_date: pd.Timestamp,
    crash_date: pd.Timestamp,
    dropped: list[str],
    coverage_start: pd.Timestamp,
    coverage_end: pd.Timestamp,
) -> str:
    calm = metrics.loc[calm_date]
    crash = metrics.loc[crash_date]
    dropped_text = ", ".join(dropped) if dropped else "None"
    return (
        "# Market Panic Detector\n\n"
        "This study uses 60-trading-day rolling correlations from adjusted IEX daily bars.\n"
        "The 50-stock diversified basket is: " + ", ".join(DEFAULT_TICKERS) + ".\n\n"
        f"Cached Alpaca coverage is {coverage_start.date()} to {coverage_end.date()}; "
        "rolling results begin after the first 60 trading-day window.\n\n"
        "## Key findings\n\n"
        f"- **Calm period:** {calm_date.date()}; average correlation "
        f"{calm['average_correlation']:.3f}; top eigenvalue "
        f"{calm['top_eigenvalue']:.3f}; eigenvalue variance share "
        f"{calm['eigenvalue_share']:.3f}; MP upper bound "
        f"{calm['mp_upper_bound']:.3f}.\n"
        f"- **Crash period:** {crash_date.date()}; average correlation "
        f"{crash['average_correlation']:.3f}; top eigenvalue "
        f"{crash['top_eigenvalue']:.3f}; eigenvalue variance share "
        f"{crash['eigenvalue_share']:.3f}; MP upper bound "
        f"{crash['mp_upper_bound']:.3f}.\n"
        f"- **Dropped tickers:** {dropped_text}. A ticker is dropped when more than "
        "10% of aligned daily history remains missing after forward-filling gaps of up to 3 days.\n\n"
        "## Outputs\n\n"
        "- `output/static_calm_vs_crash.png`\n"
        "- `output/market_panic_detector.gif`\n"
        "- `output/metrics.png`\n"
        "- `output/rolling_metrics.csv`\n\n"
        "## Run\n\n"
        "```bash\n"
        "python3 -m venv .venv\n"
        ".venv/bin/pip install -r requirements.txt\n"
        ".venv/bin/python main.py\n"
        ".venv/bin/pytest -q\n"
        "```\n\n"
        "Set `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`, or keep them in `api.txt` "
        "as `key=<key>` and `Secret=<secret>`.\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Market Panic Detector")
    parser.add_argument("--cli", action="store_true", help="Print terminal status and exit")
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end", default=date.today().isoformat())
    parser.add_argument("--window", type=int, default=60)
    parser.add_argument("--network", choices=("threshold", "mst", "weighted"), default="threshold")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--stride", type=int, default=5)
    parser.add_argument("--cache", default="cache/alpaca_daily.parquet")
    parser.add_argument("--output", default="output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.cli:
        from cli import run_cli
        raise SystemExit(run_cli(window=args.window))

    import sys
    from PySide6.QtWidgets import QApplication
    from gui.main_window import MainWindow
    from theme import STYLESHEET

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
