"""Validated YAML defaults for the installed package and development checkout."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from importlib.resources import files
import yaml
from panic_detector.data.universe import validate_tickers


@dataclass(frozen=True)
class Settings:
    universe: tuple[str, ...]
    window: int
    threshold: float
    theme: dict[str, str]


def load_settings(path: Path | None = None) -> Settings:
    source = path or Path(str(files("mood_configs").joinpath("app.yaml")))
    data: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf8"))
    window, threshold = int(data["window"]), float(data["threshold"])
    if not 20 <= window <= 250 or not 0.1 <= threshold <= 0.9:
        raise ValueError("Use a window of 20–250 sessions and a cutoff of 0.1–0.9.")
    return Settings(tuple(validate_tickers(data["universe"])), window, threshold, data["theme"])
