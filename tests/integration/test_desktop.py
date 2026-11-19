"""Drive the real first-run, settings and export paths with an isolated offline fixture."""

import os
from pathlib import Path
import shutil
import sys
from time import monotonic, sleep
import numpy as np
import pandas as pd
from PIL import Image


def test_desktop_controls_cache_and_exports(tmp_path, monkeypatch):
    if sys.platform.startswith("linux") and not (
        os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY")
    ):
        monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication, QFileDialog
    from panic_detector.app.entrypoint import configure_surface
    from panic_detector.app.main_window import MainWindow
    from panic_detector.data import alpaca_client
    from panic_detector import service
    from panic_detector.viz.theme import STYLESHEET

    configure_surface()
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(STYLESHEET)
    prefs = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    prefs.setValue("symbols", ["AA", "BB", "CC"])
    monkeypatch.setattr(service, "LEGACY", tmp_path / "absent")
    ticks = ["AA", "BB", "CC"]
    sample = pd.DataFrame(
        np.exp(0.01 * np.random.default_rng(2).normal(size=(90, 3)).cumsum(axis=0)),
        index=pd.bdate_range("2021-01-04", periods=90),
        columns=ticks,
    )
    sample["CC"] = np.nan
    monkeypatch.setattr(alpaca_client, "get_credentials", lambda: (None, None))
    w = MainWindow(prefs, tmp_path / "cache")

    def wait(predicate):
        end = monotonic() + 12
        while not predicate() and monotonic() < end:
            app.processEvents()
            sleep(0.003)
        assert predicate()

    try:
        w.show()
        assert w.stack.currentWidget() == w.welcome
        w.enter()
        wait(lambda: w.stack.currentWidget() == w.keys)
        monkeypatch.setattr(alpaca_client, "fetch", lambda *args: sample)
        w.stack.setCurrentWidget(w.dashboard)
        w.retry()
        wait(lambda: w.view is not None)
        assert "Insufficient history: CC" in w.banner.text()
        assert w.view.symbols == ("AA", "BB")
        w.play.click()
        initial = w.date_slider.value()
        wait(lambda: w.date_slider.value() != initial)
        w.play.click()
        w.advanced_button.click()
        assert w.drawer.isVisible()
        monkeypatch.setattr(
            QFileDialog,
            "getOpenFileName",
            lambda *args: (str(Path("tests/fixtures/tickers.csv").resolve()), ""),
        )
        w.drawer.load_csv()
        assert w.drawer.editor.toPlainText() == "AAPL, MSFT, BRK.B"
        w.drawer.editor.setPlainText("../bad")
        w.drawer.apply_button.click()
        assert w.fix.isVisible()
        w.drawer.editor.setPlainText("aa, bb, cc")
        w.drawer.lookback.setValue(20)
        w.drawer.mode.setCurrentIndex(1)
        w.drawer.threshold.setValue(8)
        w.drawer.apply_button.click()
        wait(lambda: w.job is None)
        assert (w.mode, w.window_days, w.cutoff) == (1, 20, 0.8)
        w.select_exact("2020-03-23")
        assert w.status.text() == "No reading"
        w.fix.click()
        assert w.status.text() != "No reading"
        for ext in (["png", "gif", "mp4"] if shutil.which("ffmpeg") else ["png", "gif"]):
            target = tmp_path / ("replay." + ext)
            monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(target), ""))
            w.export(ext)
            wait(lambda: w.job is None)
            assert target.stat().st_size > 100
            if ext == "gif":
                with Image.open(target) as img:
                    assert img.n_frames > 1
        assert prefs.value("welcomed", False, type=bool)
    finally:
        w.close()
        app.processEvents()
