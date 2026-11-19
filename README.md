# Market Panic Detector

A native dark-theme desktop app that shows when stock prices are becoming unusually synchronized. It combines a 60-day rolling correlation network, average correlation, and the top eigenvalue of the correlation matrix.

![Desktop app](screenshots/calm.png)
![Crash view](screenshots/crash_march_2020.png)

## Run on Windows or Linux

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\activate` instead.

```bash
python main.py
```

Terminal fallback:

```bash
python main.py --cli
```

## API credentials

Set environment variables:

```bash
export ALPACA_API_KEY="..."
export ALPACA_SECRET_KEY="..."
```

Or open **Settings** in the app and enter them once. They are stored locally with Qt settings. The existing `api.txt` format (`key=<key>` / `Secret=<secret>`) is also supported.

## Features

- Download adjusted IEX daily bars through `alpaca-py`
- Local Parquet cache for fast restarts and offline use
- Threshold, minimum-spanning-tree, and weighted network modes
- Fixed spring layout across dates
- GICS sector node colors and legend
- Rolling 20–250 trading-day window control
- Historical-percentile CALM, ELEVATED, and PANIC status
- Interactive date and animation controls
- PNG and GIF export
- Ticker text paste and CSV import

## Key findings

Using the cached 2019-11-11 to 2026-11-18 sample:

| Period | Average correlation | Top eigenvalue | Variation share |
|---|---:|---:|---:|
| Calm: 2026-09-15 | 0.068 | 9.628 | 19.3% |
| Crash: 2022-10-25 | 0.559 | 29.013 | 58.0% |

The app currently uses 50 diversified US tickers and is suitable for visual analysis, not investment advice.

The IEX cache available in this workspace has no usable March 2020 rows, so the crash screenshot uses the strongest available stress date (2022-10-25). March 2020 is shaded in the chart once that history is present in Alpaca.

## Tests

```bash
pytest -q
```

## Build one executable

```bash
pyinstaller --clean MarketPanicDetector.spec
```

The executable is written to `dist/MarketPanicDetector` on Linux or `dist/MarketPanicDetector.exe` on Windows.
