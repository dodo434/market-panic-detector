"""Safe Parquet cache loading and path containment."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def safe_cache_path(user_path: str | Path, root: str | Path = "data/processed") -> Path:
    """Resolve a cache path while preventing traversal outside the cache root."""
    root_path = Path(root).resolve()
    candidate = (root_path / user_path).resolve()
    if candidate != root_path and root_path not in candidate.parents:
        raise ValueError("Cache path escapes the allowed data directory")
    if candidate.suffix != ".parquet":
        raise ValueError("Cache files must use the .parquet extension")
    return candidate


def load_prices(path: str | Path) -> pd.DataFrame:
    """Load a local Parquet cache only after its path is contained."""
    cache = safe_cache_path(path)
    if not cache.exists():
        raise FileNotFoundError(cache)
    frame = pd.read_parquet(cache)
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("Cache index must contain dates")
    return frame
