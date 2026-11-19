"""Share one atomic, versioned historical snapshot between desktop and CLI."""

from collections.abc import Callable, Sequence
from contextlib import contextmanager
from datetime import date
import hashlib
import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterator
import numpy as np
from platformdirs import user_cache_path
from panic_detector.data.universe import validate_tickers

START = date(2018, 1, 1)
LEGACY = Path(__file__).resolve().parents[2] / "cache/alpaca_daily.parquet"


@contextmanager
def atomic_target(path: Path) -> Iterator[Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False, suffix=path.suffix) as tmp:
        candidate = Path(tmp.name)
    try:
        yield candidate
        candidate.replace(path)
    finally:
        candidate.unlink(missing_ok=True)


def snapshot(
    symbols: Sequence[str],
    window: int,
    refresh: bool = False,
    progress: Callable[[str], None] = lambda _: None,
    root: Path | None = None,
) -> np.ndarray:
    tickers = validate_tickers(symbols)
    if len(tickers) < 2 or not 20 <= window <= 250:
        raise ValueError("Choose at least two stocks and a window between 20 and 250 days.")
    folder = root or user_cache_path("MarketMood", appauthor=False)
    universe = hashlib.sha256(",".join(tickers).encode()).hexdigest()[:20]
    raw = folder / "raw" / f"{universe}.parquet"
    source = raw
    if not raw.exists() and not refresh and LEGACY.is_file():
        import pyarrow.parquet as pq

        if set(tickers) <= set(pq.read_schema(LEGACY).names):
            with atomic_target(raw) as candidate:
                shutil.copyfile(LEGACY, candidate)
            source = raw

    def processed_path(stream) -> Path:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()[:24]
        return folder / "processed" / f"v4-{universe}-{window}-{digest}.npy"

    if refresh or not source.exists():
        from panic_detector.data.alpaca_client import fetch

        prices = fetch(tickers, START, date.today(), progress)
        result = prepare(prices, tickers, window, progress)
        with atomic_target(raw) as candidate:
            prices.to_parquet(candidate)
            with candidate.open("rb") as stream:
                processed = processed_path(stream)
            if not processed.exists():
                with atomic_target(processed) as target:
                    np.save(target, result, allow_pickle=False)
        return result
    with source.open("rb") as stream:
        processed = processed_path(stream)
        if processed.exists():
            try:
                return np.load(processed, mmap_mode="r", allow_pickle=False)
            except (OSError, ValueError, EOFError):
                pass
        import pandas as pd

        stream.seek(0)
        result = prepare(pd.read_parquet(stream), tickers, window, progress)
    with atomic_target(processed) as target:
        np.save(target, result, allow_pickle=False)
    return result


def prepare(
    prices: "pd.DataFrame", tickers: list[str], window: int, progress: Callable[[str], None]
) -> np.ndarray:
    from panic_detector.analysis import analyze
    from panic_detector.data.cleaning import clean_prices

    progress("Preparing stock maps and daily readings…")
    aligned, _ = clean_prices(
        prices.loc[(prices.index.date >= START) & (prices.index.date <= date.today())].reindex(
            columns=tickers
        )
    )
    return analyze(aligned, window)
