# Architecture

The GUI and CLI open the same versioned snapshot. Only the Alpaca adapter imports the market-data SDK. The analytics path takes in-memory prices and returns numeric records. Each row stores an ISO trading date, five statistics, the complete matrix, a spanning tree and three sets of stable map coordinates. The symbol names live in the array schema. NPY loading disables object deserialization and supports memory mapping.

The platform user cache holds raw Parquet per universe and one derived NPY per universe, window, algorithm version and price-file digest. Atomic replacements prevent partial reads. Re-downloading validates the replacement before publishing it. A checkout can adopt the old `cache/alpaca_daily.parquet` after inspecting its actual symbols. Changing only the map mode or cutoff reuses the NPY. A Qt worker prepares line endpoints for the chosen display mode. The GUI holds persistent plot items, a fixed trace and a movable marker. Changing date selects one frame.

Onboarding and last-applied display choices use QSettings. Credentials live in the platform vault. The CLI imports Qt only when the desktop is selected. PNG captures the native view including both graphics scenes. GIF and MP4 sample up to 120 evenly spaced recorded dates in a worker, and MP4 streams RGB frames to FFmpeg.

## Migration

| Earlier path | Current owner |
|---|---|
| `data.py` | `data/alpaca_client.py`, `data/cleaning.py`, `features/returns.py` |
| `metrics.py` | `features/rolling_corr.py`, `models/`, `analysis.py` |
| `network.py` | `networks/` and `data/sectors.py` |
| `gui/main_window.py`, `gui/widgets.py`, `gui/workers.py` | `app/` |
| `theme.py` | `viz/theme.py` |
| `plots.py` | `viz/static.py` for research, `viz/plots.py` and `viz/animation.py` for desktop |
| `cli.py` | `cli.py` under the installable package |
| `tests/test_metrics.py` | `tests/unit/test_models.py` |
| `main.py` | Thin source/frozen launcher for `app/entrypoint.py` |

Package-relative destinations are under `src/panic_detector/`. The pre-existing optional web workstation retains its separate source directories and instructions. [Web workstation](web-workstation.md)
