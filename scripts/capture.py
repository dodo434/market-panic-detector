"""Exercise the native controls and capture the actual widget states from the local cache."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic, sleep
import numpy as np
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PIL import Image
from panic_detector.app.entrypoint import configure_surface
from panic_detector.app.main_window import MainWindow
from panic_detector.viz.theme import STYLESHEET


def capture(folder: Path) -> None:
    configure_surface()
    app = QApplication([])
    app.setStyleSheet(STYLESHEET)
    folder.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as tmp:
        settings = QSettings(str(Path(tmp) / "capture.ini"), QSettings.Format.IniFormat)
        w = MainWindow(settings)
        w.show()

        def shot(name):
            app.processEvents()
            QTest.qWait(140)
            assert w.capture().save(str(folder / name))

        assert w.stack.currentWidget() == w.welcome
        shot("first-launch.png")
        w.enter()
        end = monotonic() + 40
        while w.view is None and monotonic() < end:
            app.processEvents()
            sleep(0.002)
        assert w.view is not None, w.banner.text()
        rows = w.view.rows
        calm = np.flatnonzero((rows["level"] < 25) & (rows["date"] >= "2021"))[-1]
        high = np.flatnonzero((rows["level"] > 80) & (np.char.startswith(rows["date"], "2022")))
        panic = high[np.argmax(rows["average"][high])] if len(high) else np.argmax(rows["level"])
        w.date_slider.setValue(int(calm))
        assert w.status.text() == "CALM"
        shot("calm.png")
        w.play.click()
        QTest.qWait(130)
        w.play.click()
        assert int(calm) != w.date_slider.value()
        w.date_slider.setValue(int(panic))
        assert w.status.text() == "PANIC"
        shot("panic.png")
        w.advanced_button.click()
        assert w.drawer.isVisible()
        shot("advanced.png")
        w.select_exact("2020-03-23")
        w.advanced_button.click()
        shot("march-2020.png")
        if getattr(w, "unavailable", False):
            assert w.fix.isVisible()
            QTest.mouseClick(w.fix, Qt.MouseButton.LeftButton)
            assert w.status.text() != "No reading"
        with Image.open(folder / "calm.png") as a, Image.open(folder / "panic.png") as b:
            a.save(
                folder / "market-mood.gif", save_all=True, append_images=[b], duration=2400, loop=0
            )
        for i in (calm, panic):
            r = rows[i]
            print(r["date"], r["average"], r["leading"], r["share"], r["level"])
        w.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("docs/figures"))
    capture(parser.parse_args().output)
