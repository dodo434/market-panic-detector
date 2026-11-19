"""Prepare line endpoints in a worker. Selecting a date only addresses a frame."""

from dataclasses import dataclass
from datetime import date
import numpy as np
from panic_detector.networks.threshold import threshold_edges
from panic_detector.networks.weighted import all_pairs

MODES = ("Threshold", "Spanning tree", "All links")


@dataclass
class Scene:
    rows: np.ndarray
    days: np.ndarray
    symbols: tuple[str, ...]
    positions: np.ndarray
    lines: list[tuple[np.ndarray, ...]]


def scene(rows: np.ndarray, mode: int, cutoff: float) -> Scene:
    symbols = rows.dtype["symbols"].names or ()
    pairs = all_pairs(len(symbols))
    points = rows["xy"][:, mode]
    frames = []
    for row, xy in zip(rows, points):
        if mode == 0:
            groups = (threshold_edges(row["corr"], pairs, cutoff),)
        elif mode == 1:
            groups = (row["mst"],)
        else:
            weights = row["corr"][pairs[:, 0], pairs[:, 1]]
            groups = tuple(
                pairs[mask]
                for mask in (weights < 0, (weights >= 0) & (weights < cutoff), weights >= cutoff)
            )
        frames.append(tuple(np.ascontiguousarray(xy[group].reshape(-1, 2).T) for group in groups))
    days = np.array([date.fromisoformat(s).toordinal() for s in rows["date"]])
    return Scene(rows, days, symbols, points, frames)
