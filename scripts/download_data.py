"""Refresh adjusted prices and precompute the default window."""

from panic_detector.config import load_settings
from panic_detector.service import snapshot

if __name__ == "__main__":
    settings = load_settings()
    snapshot(settings.universe, settings.window, refresh=True, progress=print)
