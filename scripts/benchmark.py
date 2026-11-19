"""Measure process startup to a painted, usable cached timeline and completed repaints."""

from time import perf_counter, sleep
import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

START = perf_counter()


def measure(
    frames: int, root: Path | None = None, full: bool = False, mode: str = "threshold"
) -> dict:
    import numpy as np
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    from panic_detector.app.main_window import MainWindow
    from panic_detector.viz.theme import STYLESHEET
    from panic_detector.app.entrypoint import configure_surface

    imports_s = perf_counter() - START
    configure_surface()
    with TemporaryDirectory() as tmp:
        prefs = QSettings(str(Path(tmp) / "settings.ini"), QSettings.Format.IniFormat)
        prefs.setValue("welcomed", True)
        prefs.setValue("mode", ("threshold", "mst", "weighted").index(mode))
        app = QApplication.instance() or QApplication([])
        app.setStyleSheet(STYLESHEET)
        window = MainWindow(prefs, root)
        window.show()
        shown_s = perf_counter() - START
        while window.view is None:
            app.processEvents()
            sleep(0.001)
            if perf_counter() - START > 30 or window.stack.currentWidget() == window.keys:
                raise RuntimeError("Prepare the offline cache before running the benchmark.")
        app.processEvents()
        window.repaint()
        startup = perf_counter() - START
        from PySide6.QtOpenGLWidgets import QOpenGLWidget

        gl = isinstance(window.map.viewport(), QOpenGLWidget)
        if full and not gl:
            raise RuntimeError("GPU readback requires an accelerated OpenGL desktop.")
        times = []
        for index in np.linspace(0, window.date_slider.maximum(), frames, dtype=int):
            start = perf_counter()
            window.date_slider.setValue(int(index))
            app.processEvents()
            # Deliver posted viewport paints once per input, as in playback.
            if full:
                window.map.viewport().grabFramebuffer()
                window.chart.viewport().grabFramebuffer()
            times.append((perf_counter() - start) * 1000)
        window.close()
        return {
            "startup_s": round(startup, 4),
            "imports_s": round(imports_s, 4),
            "shown_s": round(shown_s, 4),
            "opengl": gl,
            "frames": len(times),
            "p50_ms": round(float(np.median(times)), 3),
            "p95_ms": round(float(np.percentile(times, 95)), 3),
            "max_ms": round(max(times), 3),
            "platform": app.platformName(),
            "mode": mode,
            "gpu_readback": full,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--cache-root", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--gpu-readback", action="store_true")
    parser.add_argument("--mode", choices=("threshold", "mst", "weighted"), default="threshold")
    args = parser.parse_args()
    metrics = measure(args.frames, args.cache_root, args.gpu_readback, args.mode)
    print(json.dumps(metrics))
    sys.exit(int(args.check and (metrics["startup_s"] >= 2 or metrics["max_ms"] > 16)))
