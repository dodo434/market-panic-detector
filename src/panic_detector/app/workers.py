"""Worker signals cross the Qt event queue. Only friendly messages leave a task."""

from collections.abc import Callable
from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class Signals(QObject):
    message = Signal(str)
    ready = Signal(object)
    failed = Signal(str, bool)


class Job(QRunnable):
    def __init__(self, action: Callable) -> None:
        super().__init__()
        self.action = action
        self.signals = Signals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.ready.emit(self.action(self.signals.message.emit))
        except ValueError as error:
            from panic_detector.data.alpaca_client import MissingKeys

            self.signals.failed.emit(str(error), isinstance(error, MissingKeys))
        except Exception:
            self.signals.failed.emit("Check the selected file or connection and try again.", False)
