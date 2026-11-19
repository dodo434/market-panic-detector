"""Reusable Qt widgets for the Market Panic Detector."""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout


class SettingsDialog(QDialog):
    """Collect local Alpaca credentials."""

    def __init__(self, api_key: str = "", secret_key: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Alpaca API Settings")
        self.resize(460, 210)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Alpaca API key"))
        self.api_key = QLineEdit(api_key)
        self.api_key.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.api_key)
        layout.addWidget(QLabel("Alpaca secret key"))
        self.secret_key = QLineEdit(secret_key)
        self.secret_key.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.secret_key)
        layout.addWidget(QLabel("Credentials are stored locally with Qt QSettings."))
        save = QPushButton("Save")
        save.clicked.connect(self.accept)
        layout.addWidget(save)


class HelpDialog(QDialog):
    """Plain-language explanation."""

    def __init__(parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("What am I looking at?")
        self.resize(520, 300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "<h2>One stock moving is normal. Many stocks moving together can be a warning.</h2>"
            "<p><b>Average correlation</b> summarizes whether stocks tend to rise and fall together.</p>"
            "<p><b>Top eigenvalue</b> measures how strongly one broad market factor dominates movement.</p>"
            "<p><b>Dots</b> are stocks; <b>lines</b> show strong relationships. "
            "Dark green means calm, amber means unusually elevated, and red means panic-like behavior.</p>"
            "<p>The bottom date slider lets you compare calm periods and market crashes.</p>"
        ))
        layout.itemAt(0).widget().setWordWrap(True)
        close_button = QPushButton("Got it")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)


class MatplotlibCanvas(FigureCanvasQTAgg):
    """A single matplotlib canvas for network and time-series views."""

    def __init__(self, width: float = 12, height: float = 7) -> None:
        fig = Figure(figsize=(width, height), facecolor="#071018")
        fig.subplots_adjust(left=0.05, right=0.98, top=0.94, bottom=0.08)
        super().__init__(fig)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
