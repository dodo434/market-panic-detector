"""Advanced controls apply together and keep the main view uncluttered."""

import csv
import re
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from panic_detector.app.widgets import label, slider
from panic_detector.data.paths import selected_file
from panic_detector.data.universe import validate_tickers
from panic_detector.viz.plots import MODES


class Advanced(QWidget):
    def __init__(self, host) -> None:
        super().__init__()
        self.host = host
        self.setFixedWidth(280)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 0, 0, 0)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        controls, details = QWidget(), QWidget()
        tabs.addTab(controls, "Settings")
        tabs.addTab(details, "Details")
        form = QVBoxLayout(controls)
        self.lookback = slider(20, 250, host.window_days)
        self.threshold = slider(1, 9, round(host.cutoff * 10))
        for widget, title, formatter in (
            (self.lookback, "Trading days", str),
            (self.threshold, "Link cutoff", lambda v: f"{v/10:.1f}"),
        ):
            caption = label(f"{title}   {formatter(widget.value())}")
            widget.valueChanged.connect(
                lambda v, lab=caption, t=title, f=formatter: lab.setText(f"{t}   {f(v)}")
            )
            widget.setAccessibleName(title)
            form.addWidget(caption)
            form.addWidget(widget)
        self.mode = QComboBox()
        self.mode.addItems(MODES)
        self.mode.setCurrentIndex(host.mode)
        form.addWidget(label("Map links"))
        form.addWidget(self.mode)
        form.addWidget(label("Stock symbols"))
        self.editor = QPlainTextEdit(", ".join(host.tickers))
        self.editor.setMaximumHeight(96)
        form.addWidget(self.editor)
        self.button(form, "Load CSV", self.load_csv)
        self.apply_button = self.button(form, "Apply changes", lambda: self.apply(False))
        self.refresh_button = self.button(form, "Re-download prices", lambda: self.apply(True))
        self.button(form, "Alpaca keys", host.connect_keys)
        form.addWidget(label("Export"))
        exports = QHBoxLayout()
        for ext in ("png", "gif", "mp4"):
            self.button(exports, ext.upper(), lambda _, e=ext: host.export(e))
        form.addLayout(exports)
        form.addStretch()
        detail = QVBoxLayout(details)
        self.readout = label("")
        self.readout.setWordWrap(True)
        detail.addWidget(self.readout)
        detail.addWidget(label("Inspect a date"))
        self.day = QDateEdit(QDate.currentDate())
        self.day.setCalendarPopup(True)
        self.day.setDisplayFormat("yyyy-MM-dd")
        detail.addWidget(self.day)
        self.button(
            detail, "Show date", lambda: host.select_exact(self.day.date().toString("yyyy-MM-dd"))
        )
        detail.addStretch()
        self.hide()

    def button(self, layout, title, callback):
        button = QPushButton(title)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def load_csv(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Open ticker CSV", "", "CSV (*.csv)")
        if not name:
            return
        try:
            path = selected_file(name, ".csv")
            if path.stat().st_size > 65536:
                raise ValueError("Choose a CSV smaller than 64 KB.")
            with path.open(encoding="utf-8-sig", newline="") as stream:
                cells = [c.strip() for row in csv.reader(stream) for c in row if c.strip()]
            if cells and cells[0].lower() in {"ticker", "symbol", "tickers"}:
                cells.pop(0)
            self.editor.setPlainText(", ".join(validate_tickers(cells)))
        except (ValueError, OSError, csv.Error):
            self.host.error(
                "Choose a CSV containing up to 50 stock symbols.", self.load_csv, "Choose CSV"
            )

    def apply(self, refresh: bool) -> None:
        try:
            symbols = validate_tickers(re.split(r"[,;\s]+", self.editor.toPlainText().strip()))
            if len(symbols) < 2:
                raise ValueError("Enter at least two different stocks.")
        except ValueError as exc:
            self.host.error(str(exc), self.editor.setFocus, "Edit symbols")
            return
        self.host.load(
            symbols,
            self.lookback.value(),
            self.mode.currentIndex(),
            self.threshold.value() / 10,
            refresh,
        )
