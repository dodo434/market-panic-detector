"""Main native desktop window."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from PySide6.QtCore import QSettings, QThread, QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from data import DEFAULT_TICKERS
from gui.widgets import HelpDialog, MatplotlibCanvas, SettingsDialog
from gui.workers import AnalysisWorker
from network import SECTOR_COLORS, SECTOR_MAP, build_network, fixed_layout
from theme import COLORS
from metrics import classify_status, status_thresholds


class MainWindow(QMainWindow):
    """Interactive desktop application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Market Panic Detector")
        self.resize(1500, 900)
        self.settings = QSettings("MarketPanicDetector", "MarketPanicDetector")
        self.tickers = list(DEFAULT_TICKERS)
        self.metrics: pd.DataFrame | None = None
        self.matrices: dict[tuple[pd.Timestamp, pd.Timestamp], pd.DataFrame] = {}
        self.layout: dict[str, tuple[float, float]] = {}
        self.current_date: pd.Timestamp | None = None
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self.advance_date)
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.timeout.connect(self.recompute_window)
        self.node_hover = None
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self.status_banner = QLabel("MARKET STATUS: LOADING")
        self.status_banner.setObjectName("statusBanner")
        self.status_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_banner.setStyleSheet(
            f"background:{COLORS['panel']}; border:1px solid {COLORS['cyan']}; "
            f"border-radius:8px; color:{COLORS['cyan']}; font-size:22px; "
            "font-weight:800; padding:14px;"
        )
        root.addWidget(self.status_banner)

        center = QHBoxLayout()
        left = QFrame()
        left.setObjectName("panel")
        left_layout = QVBoxLayout(left)
        self.canvas = MatplotlibCanvas(12, 7)
        self.canvas.mpl_connect("motion_notify_event", self._network_hover)
        left_layout.addWidget(NavigationToolbar2QT(self.canvas, left))
        left_layout.addWidget(self.canvas)
        center.addWidget(left, 3)

        right = QFrame()
        right.setObjectName("panel")
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("TICKERS"))
        self.ticker_text = QPlainTextEdit(", ".join(self.tickers))
        self.ticker_text.setMaximumHeight(120)
        self.ticker_text.setToolTip("Paste tickers separated by commas or whitespace.")
        right_layout.addWidget(self.ticker_text)

        self.download_button = QPushButton("Download / Refresh")
        self.download_button.clicked.connect(self.start_analysis)
        self.download_button.setToolTip("Download missing bars in a background thread.")
        right_layout.addWidget(self.download_button)
        csv_button = QPushButton("Load ticker CSV")
        csv_button.clicked.connect(self.load_ticker_csv)
        csv_button.setToolTip("Load a one-column ticker list from a CSV file.")
        right_layout.addWidget(csv_button)

        controls_row = QHBoxLayout()
        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(self.open_settings)
        help_button = QToolButton()
        help_button.setText("What am I looking at?")
        help_button.clicked.connect(self.open_help)
        controls_row.addWidget(settings_button)
        controls_row.addWidget(help_button)
        right_layout.addLayout(controls_row)

        right_layout.addWidget(QLabel("Dropped tickers"))
        self.dropped_label = QLabel("None")
        self.dropped_label.setWordWrap(True)
        right_layout.addWidget(self.dropped_label)

        export_row = QHBoxLayout()
        png_button = QPushButton("Save PNG")
        png_button.clicked.connect(self.save_png)
        export_row.addWidget(png_button)
        gif_button = QPushButton("Save GIF")
        gif_button.clicked.connect(self.save_gif)
        export_row.addWidget(gif_button)
        right_layout.addLayout(export_row)

        self.progress_label = QLabel("Ready")
        right_layout.addWidget(self.progress_label)
        right_layout.addStretch()
        center.addWidget(right, 1)
        root.addLayout(center, 1)

        bottom = QFrame()
        bottom.setObjectName("panel")
        bottom_layout = QGridLayout(bottom)

        bottom_layout.addWidget(QLabel("Window size"), 0, 0)
        self.window_slider = QSlider(Qt.Orientation.Horizontal)
        self.window_slider.setRange(20, 250)
        self.window_slider.setValue(60)
        self.window_slider.setToolTip("Number of trading days used in each correlation calculation.")
        self.window_label = QLabel("60 days")
        self.window_slider.valueChanged.connect(self._window_changed)
        bottom_layout.addWidget(self.window_slider, 0, 1)
        bottom_layout.addWidget(self.window_label, 0, 2)

        bottom_layout.addWidget(QLabel("Correlation cutoff"), 1, 0)
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(10, 90)
        self.threshold_slider.setValue(50)
        self.threshold_label = QLabel("0.50")
        self.threshold_slider.valueChanged.connect(self._threshold_changed)
        bottom_layout.addWidget(self.threshold_slider, 1, 1)
        bottom_layout.addWidget(self.threshold_label, 1, 2)

        bottom_layout.addWidget(QLabel("Network mode"), 2, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Threshold", "MST", "Weighted"])
        self.mode_combo.currentTextChanged.connect(lambda _: self.refresh_view())
        bottom_layout.addWidget(self.mode_combo, 2, 1)

        bottom_layout.addWidget(QLabel("Date"), 3, 0)
        self.date_slider = QSlider(Qt.Orientation.Horizontal)
        self.date_slider.setEnabled(False)
        self.date_slider.valueChanged.connect(self._date_changed)
        self.date_label = QLabel("No data")
        bottom_layout.addWidget(self.date_slider, 3, 1)
        bottom_layout.addWidget(self.date_label, 3, 2)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_play)
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["Slow", "Normal", "Fast"])
        bottom_layout.addWidget(self.play_button, 4, 0)
        bottom_layout.addWidget(self.speed_combo, 4, 1)
        root.addWidget(bottom)

        self.setCentralWidget(central)

    def open_settings(self) -> None:
        dialog = SettingsDialog(
            self.settings.value("alpaca_api_key", ""),
            self.settings.value("alpaca_secret_key", ""),
            self,
        )
        if dialog.exec():
            self.settings.setValue("alpaca_api_key", dialog.api_key.text())
            self.settings.setValue("alpaca_secret_key", dialog.secret_key.text())

    def open_help(self) -> None:
        HelpDialog(self).exec()

    def get_tickers(self) -> list[str]:
        text = self.ticker_text.toPlainText().replace(",", " ").replace("\n", " ")
        return list(dict.fromkeys(token.strip().upper() for token in text.split() if token.strip()))

    def load_ticker_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load ticker CSV", "", "CSV (*.csv)")
        if not path:
            return
        frame = pd.read_csv(path)
        candidates: list[str] = []
        for column in frame.columns:
            candidates.extend(str(value).strip().upper() for value in frame[column].dropna())
        tickers = list(dict.fromkeys(token for token in candidates if token.isalpha()))
        if not tickers:
            QMessageBox.warning(self, "No tickers", "Could not find ticker symbols in the CSV.")
            return
        self.ticker_text.setPlainText(", ".join(tickers))

    def start_analysis(self) -> None:
        tickers = self.get_tickers()
        if not tickers:
            QMessageBox.warning(self, "No tickers", "Enter at least one ticker.")
            return
        api_key = self.settings.value("alpaca_api_key", "")
        secret_key = self.settings.value("alpaca_secret_key", "")
        if api_key and secret_key:
            import os
            os.environ["ALPACA_API_KEY"] = str(api_key)
            os.environ["ALPACA_SECRET_KEY"] = str(secret_key)

        self.tickers = tickers
        self.download_button.setEnabled(False)
        self.thread = QThread(self)
        self.worker = AnalysisWorker(tickers, pd.Timestamp("2018-01-01").date(), "cache/alpaca_daily.parquet", self.window_slider.value())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._worker_progress)
        self.worker.finished.connect(self._analysis_finished)
        self.worker.failed.connect(self._analysis_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _worker_progress(self, percent: int, text: str) -> None:
        self.progress_label.setText(f"{percent}% — {text}")

    def _analysis_finished(self, result: dict) -> None:
        self.download_button.setEnabled(True)
        self.metrics = result["metrics"]
        self.matrices = result["matrices"]
        dropped = result["dropped"]
        self.dropped_label.setText(", ".join(dropped) if dropped else "None")
        if self.metrics is None or self.metrics.empty:
            QMessageBox.warning(self, "No analysis", "Not enough market history was available.")
            return
        dates = list(self.metrics.index)
        self.date_slider.setRange(0, len(dates) - 1)
        self.date_slider.setValue(len(dates) - 1)
        self.date_slider.setEnabled(True)
        first = next(iter(self.matrices.values()), None)
        self.layout = fixed_layout(first) if first is not None else {}
        self.current_date = pd.Timestamp(dates[-1])
        self.refresh_view()

    def _analysis_failed(self, message: str) -> None:
        self.download_button.setEnabled(True)
        self.progress_label.setText("Failed")
        QMessageBox.critical(self, "Analysis error", message)

    def _window_changed(self, value: int) -> None:
        self.window_label.setText(f"{value} days")
        self.debounce.start(350)

    def recompute_window(self) -> None:
        self.start_analysis()

    def _threshold_changed(self, value: int) -> None:
        self.threshold_label.setText(f"{value / 100:.2f}")
        self.refresh_view()

    def _date_changed(self, index: int) -> None:
        if self.metrics is None or self.metrics.empty:
            return
        self.current_date = pd.Timestamp(self.metrics.index[index])
        self.date_label.setText(str(self.current_date.date()))
        self.refresh_view()

    def advance_date(self) -> None:
        if self.metrics is None:
            return
        index = self.date_slider.value()
        if index >= self.date_slider.maximum():
            self.date_slider.setValue(0)
        else:
            self.date_slider.setValue(index + 1)

    def toggle_play(self) -> None:
        if self.play_timer.isActive():
            self.play_timer.stop()
            self.play_button.setText("Play")
            return
        speed_ms = {"Slow": 900, "Normal": 500, "Fast": 180}[self.speed_combo.currentText()]
        self.play_timer.start(speed_ms)
        self.play_button.setText("Pause")

    def _network_hover(self, event) -> None:
        if event.inaxes is None or event.xdata is None or event.ydata is None:
            return
        corr = self.matrix_for_date()
        if corr is None:
            return
        nearest = None
        nearest_distance = float("inf")
        for ticker, (x, y) in self.layout.items():
            distance = (event.xdata - x) ** 2 + (event.ydata - y) ** 2
            if distance < nearest_distance:
                nearest_distance = distance
                nearest = ticker
        if nearest is None or nearest_distance > 0.015:
            self.status_banner.setToolTip("")
            return
        if nearest in corr.columns:
            average = float(corr[nearest].drop(nearest).mean())
            sector = SECTOR_MAP.get(nearest, "Other")
            self.status_banner.setToolTip(
                f"{nearest} | {sector} | average correlation {average:.3f}"
            )

    def matrix_for_date(self) -> pd.DataFrame | None:
        if self.current_date is None:
            return None
        exact = [(end, corr) for (_, end), corr in self.matrices.items() if end == self.current_date]
        if exact:
            return exact[0][1]
        if not self.matrices:
            return None
        _, corr = min(self.matrices.items(), key=lambda item: abs(item[0][1] - self.current_date))
        return corr

    def refresh_view(self) -> None:
        if self.metrics is None or self.current_date is None:
            return
        corr = self.matrix_for_date()
        if corr is None:
            return
        elevated, panic = status_thresholds(self.metrics["eigenvalue_share"])
        metric_position = self.metrics.index.get_indexer([self.current_date], method="nearest")[0]
        row = self.metrics.iloc[metric_position]
        status = classify_status(float(row["eigenvalue_share"]), elevated, panic)
        colors = {"CALM": COLORS["green"], "ELEVATED": COLORS["amber"], "PANIC": COLORS["red"]}
        sentence = {
            "CALM": "Stocks are behaving independently. Diversification is working normally.",
            "ELEVATED": "Stocks are moving together more than usual. Diversification is weakening.",
            "PANIC": "Stocks are moving as one cluster. Diversification may offer little protection.",
        }[status]
        self.status_banner.setText(f"{status}  |  {sentence}")
        self.status_banner.setStyleSheet(
            f"background:{COLORS['panel']}; border:2px solid {colors[status]}; "
            f"border-radius:8px; color:{colors[status]}; font-size:20px; "
            "font-weight:800; padding:14px;"
        )

        fig = self.canvas.figure
        fig.clear()
        grid = fig.add_gridspec(2, 2, width_ratios=(1.15, 1.0))
        ax_net = fig.add_subplot(grid[:, 0])
        ax_avg = fig.add_subplot(grid[0, 1])
        ax_top = fig.add_subplot(grid[1, 1])
        for ax in (ax_net, ax_avg, ax_top):
            ax.set_facecolor(COLORS["panel"])
            ax.tick_params(colors=COLORS["muted"])
        ax_net.set_title(f"{self.mode_combo.currentText()} network", color=COLORS["text"])

        kind = self.mode_combo.currentText().lower()
        kind = "mst" if kind == "mst" else "weighted" if kind == "weighted" else "threshold"
        graph = build_network(corr, kind=kind, threshold=self.threshold_slider.value() / 100)
        if not self.layout:
            self.layout = fixed_layout(corr)
        nodes = [node for node in graph.nodes if node in self.layout]
        sectors = [SECTOR_MAP.get(node, "Other") for node in nodes]
        node_colors = [SECTOR_COLORS.get(sector, "#7F7F7F") for sector in sectors]
        nx.draw_networkx_edges(graph, self.layout, ax=ax_net, alpha=0.38, edge_color=COLORS["cyan"], width=0.7)
        nx.draw_networkx_nodes(graph, self.layout, ax=ax_net, nodelist=nodes, node_color=node_colors, node_size=80, edgecolors="white", linewidths=0.35)
        nx.draw_networkx_labels(graph, self.layout, ax=ax_net, labels={node: node for node in nodes}, font_size=5, font_color=COLORS["text"])
        ax_net.set_axis_off()

        ax_avg.plot(self.metrics.index, self.metrics["average_correlation"], color=COLORS["cyan"], lw=1.4)
        ax_avg.axvline(self.current_date, color="white", lw=1)
        ax_avg.scatter([self.current_date], [row["average_correlation"]], color=colors[status], s=28)
        ax_avg.set_title("Average correlation", color=COLORS["text"])
        ax_avg.grid(alpha=0.12)

        ax_top.plot(self.metrics.index, self.metrics["top_eigenvalue"], color=COLORS["red"], lw=1.4, label="Top eigenvalue")
        ax_top.plot(self.metrics.index, self.metrics["mp_upper_bound"], color=COLORS["muted"], ls="--", lw=1, label="Noise limit")
        ax_top.axvline(self.current_date, color="white", lw=1)
        ax_top.scatter([self.current_date], [row["top_eigenvalue"]], color=colors[status], s=28)
        ax_top.set_title("Top eigenvalue", color=COLORS["text"])
        ax_top.legend(facecolor=COLORS["panel"], edgecolor=COLORS["border"], labelcolor=COLORS["text"], fontsize=8)
        ax_top.grid(alpha=0.12)

        for label, start, end in (
            ("COVID crash", "2020-02-15", "2020-04-15"),
            ("2022 selloff", "2022-01-01", "2022-10-31"),
        ):
            ax_avg.axvspan(pd.Timestamp(start), pd.Timestamp(end), color=COLORS["red"], alpha=0.07)
            ax_top.axvspan(pd.Timestamp(start), pd.Timestamp(end), color=COLORS["red"], alpha=0.07)
        fig.tight_layout()
        self.canvas.draw_idle()

    def save_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save current view", "market_panic_view.png", "PNG (*.png)")
        if path:
            self.canvas.figure.savefig(path, dpi=180, facecolor=COLORS["background"], bbox_inches="tight")

    def save_gif(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save animation", "market_panic_animation.gif", "GIF (*.gif)")
        if not path:
            return
        try:
            import imageio.v2 as imageio
            if self.metrics is None:
                raise RuntimeError("Load market data first.")
            original = self.date_slider.value()
            frames = []
            for index in range(0, len(self.metrics), 5):
                self.date_slider.setValue(index)
                self.canvas.draw()
                import io
                buffer = io.BytesIO()
                self.canvas.figure.savefig(buffer, format="png", facecolor=COLORS["background"])
                buffer.seek(0)
                from PIL import Image
                frames.append(Image.open(buffer).convert("RGB"))
            imageio.mimsave(path, frames, duration=0.12, loop=0)
            self.date_slider.setValue(original)
            QMessageBox.information(self, "Export complete", f"Animation saved to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))
