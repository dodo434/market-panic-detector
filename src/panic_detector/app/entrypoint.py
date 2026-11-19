"""Select CLI before importing any Qt components."""

import sys


def configure_surface() -> None:
    """Let the precise playback timer pace frames without an extra blocking swap."""
    from PySide6.QtGui import QSurfaceFormat

    surface = QSurfaceFormat.defaultFormat()
    surface.setSwapInterval(0)
    QSurfaceFormat.setDefaultFormat(surface)


def run() -> int:
    args = sys.argv[1:]
    if "--cli" in args:
        from panic_detector.cli import main

        args.remove("--cli")
        return main(args)
    from PySide6.QtWidgets import QApplication
    from panic_detector.app.main_window import MainWindow
    from panic_detector.viz.theme import STYLESHEET

    configure_surface()
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()
