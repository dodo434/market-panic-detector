"""Market Mood desktop. Timeline, banner and maps share the same selected record."""

from datetime import date
from pathlib import Path
from typing import cast
from collections.abc import Callable
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QSettings, QTimer, QThreadPool
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from panic_detector.app.advanced import Advanced
from panic_detector.app.widgets import (
    accelerated_plots_available,
    Gauge,
    Map,
    YearAxis,
    heading,
    icon,
    label,
    rule,
    slider,
)
from panic_detector.app.workers import Job
from panic_detector.config import load_settings
from panic_detector.data.paths import selected_file
from panic_detector.data.sectors import SECTOR_COLORS, SECTOR_MAP
from panic_detector.models.panic_score import classify_status
from panic_detector.service import snapshot
from panic_detector.viz.plots import Scene, scene
from panic_detector.viz.theme import COLORS

SENTENCES = {
    "CALM": "Stocks are mostly moving their own way.",
    "NERVOUS": "More stocks are starting to move together.",
    "PANIC": "Stocks are moving as one. A broad fall can hit many holdings at once.",
}


class MainWindow(QMainWindow):
    def __init__(
        self, preferences: QSettings | None = None, cache_root: Path | None = None
    ) -> None:
        super().__init__()
        self.setWindowTitle("Market Mood")
        self.setWindowIcon(icon())
        self.resize(1112, 736)
        self.prefs = preferences or QSettings("MarketMood", "Desktop")
        self.cache_root = cache_root
        defaults = load_settings()
        self.tickers = cast(
            list[str], self.prefs.value("symbols", list(defaults.universe), type=list)
        )
        self.window_days = cast(int, self.prefs.value("window", defaults.window, type=int))
        self.cutoff = cast(float, self.prefs.value("cutoff", defaults.threshold, type=float))
        self.mode = cast(int, self.prefs.value("mode", 0, type=int))
        self.view: Scene | None = None
        self.pool = QThreadPool(self)
        self.job: Job | None = None
        self.action: Callable = self.connect_keys
        self.play_timer = QTimer(self)
        self.play_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.play_timer.timeout.connect(self.advance)
        pg.setConfigOptions(useOpenGL=accelerated_plots_available(), antialias=False)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.dashboard = QWidget()
        self.stack.addWidget(self.dashboard)
        self._dashboard()
        self.welcome = self._intro()
        self.keys = self._keys()
        if self.prefs.value("welcomed", False, type=bool):
            QTimer.singleShot(0, self.reload)
        else:
            self.stack.setCurrentWidget(self.welcome)

    def _dashboard(self) -> None:
        outer = QVBoxLayout(self.dashboard)
        outer.setContentsMargins(32, 20, 32, 16)
        outer.setSpacing(12)
        top = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(self.windowIcon().pixmap(32, 32))
        top.addWidget(mark)
        top.addWidget(label("Market Mood", "brand"))
        top.addStretch()
        self.feed = label("Adjusted daily prices  /  IEX", "meta")
        top.addWidget(self.feed)
        self.advanced_button = QPushButton("Advanced")
        self.advanced_button.setCheckable(True)
        top.addWidget(self.advanced_button)
        outer.addLayout(top)
        outer.addWidget(rule())
        body = QHBoxLayout()
        outer.addLayout(body, 1)
        main = QVBoxLayout()
        body.addLayout(main, 1)
        upper = QHBoxLayout()
        left = QVBoxLayout()
        left.setContentsMargins(0, 8, 24, 8)
        left.addLayout(
            heading(
                "Is the market panicking?",
                "This reading compares stocks with their own history. Pick a date to see how unusual their shared movement was.",
                self,
            )
        )
        left.addStretch()
        self.asof = label("Loading history", "meta")
        left.addWidget(self.asof)
        self.status = label("—")
        self.status.setStyleSheet("font-size:54px;font-weight:700;")
        left.addWidget(self.status)
        self.sentence = label("Preparing your reading…")
        self.sentence.setWordWrap(True)
        self.sentence.setMinimumHeight(42)
        left.addWidget(self.sentence)
        left.addSpacing(8)
        self.score = label("Panic level    — / 100", "meta")
        left.addWidget(self.score)
        self.gauge = Gauge()
        left.addWidget(self.gauge)
        left.addStretch()
        upper.addLayout(left, 4)
        upper.addWidget(rule(True))
        right = QVBoxLayout()
        right.setContentsMargins(24, 8, 0, 8)
        right.addLayout(
            heading(
                "Stock map",
                "Each dot is a stock, colored by its industry. Stocks that move with their peers pull closer to the center.",
                self,
            )
        )
        self.map = Map()
        right.addWidget(self.map, 1)
        self.caption = label("", "muted")
        right.addWidget(self.caption)
        upper.addLayout(right, 6)
        main.addLayout(upper, 3)
        main.addWidget(rule())
        main.addLayout(
            heading(
                "Panic level over time",
                "A higher line means stocks moved together more than they usually did. The marker follows the date you select.",
                self,
            )
        )
        self.chart = pg.PlotWidget(
            background=COLORS["background"], axisItems={"bottom": YearAxis(orientation="bottom")}
        )
        self.chart.setMinimumHeight(154)
        self.chart.hideButtons()
        self.chart.setMouseEnabled(x=False, y=False)
        self.chart.setMenuEnabled(False)
        self.chart.setYRange(-2, 120, padding=0)
        self.chart.getAxis("left").setTicks([[(0, "0"), (50, "50"), (100, "100")]])
        for side in ("left", "bottom"):
            self.chart.getAxis(side).setPen("#46504f")
            self.chart.getAxis(side).setTextPen(COLORS["muted"])
        self.curve = self.chart.plot(pen=pg.mkPen(COLORS["calm"], width=1))
        self.marker = pg.InfiniteLine(angle=90, pen=pg.mkPen("#a8b7b4"))
        self.chart.addItem(self.marker)
        self.events: list = []
        main.addWidget(self.chart, 2)
        main.addWidget(rule())
        controls = QHBoxLayout()
        self.play = QPushButton("Play")
        self.play.setFixedWidth(80)
        self.play.clicked.connect(self.toggle_play)
        controls.addWidget(self.play)
        self.date_slider = slider(0, 0, 0)
        self.date_slider.setAccessibleName("Historical date")
        self.date_slider.valueChanged.connect(self.select_date)
        controls.addWidget(self.date_slider, 1)
        self.date_label = label("—", "meta")
        controls.addWidget(self.date_label)
        main.addLayout(controls)
        self.drawer = Advanced(self)
        body.addWidget(self.drawer)
        self.advanced_button.toggled.connect(self.show_drawer)
        notice = QHBoxLayout()
        self.banner = label("", "muted")
        self.banner.setWordWrap(True)
        self.fix = QPushButton("Retry")
        self.fix.clicked.connect(lambda: self.action())
        self.fix.hide()
        notice.addWidget(self.banner, 1)
        notice.addWidget(self.fix)
        outer.addLayout(notice)
        self.play.setEnabled(False)

    def _page(self, title: str, body: str):
        page = QWidget()
        box = QVBoxLayout(page)
        box.setContentsMargins(64, 48, 64, 48)
        brand = label("Market Mood", "brand")
        box.addWidget(brand)
        box.addWidget(rule())
        box.addStretch()
        headline = label(title)
        headline.setStyleSheet("font-size:40px;font-weight:650;")
        box.addWidget(headline)
        note = label(body, "muted")
        note.setWordWrap(True)
        box.addWidget(note)
        box.addSpacing(16)
        self.stack.addWidget(page)
        return page, box

    def _intro(self) -> QWidget:
        page, box = self._page(
            "Do stocks move as one?",
            "When stocks fall together, owning several can offer less protection. Explore one trading day at a time.",
        )
        for title, copy in (
            ("CALM", "Stocks go their own way."),
            ("NERVOUS", "More stocks move together."),
            ("PANIC", "One shared move dominates."),
        ):
            row = QHBoxLayout()
            name = label(title)
            name.setStyleSheet(f"color:{COLORS[title.lower()]};font-weight:650")
            name.setFixedWidth(96)
            row.addWidget(name)
            row.addWidget(label(copy))
            row.addStretch()
            box.addLayout(row)
        box.addStretch()
        actions = QHBoxLayout()
        for title in ("Open timeline", "Skip welcome"):
            b = QPushButton(title)
            b.clicked.connect(self.enter)
            actions.addWidget(b)
        actions.addStretch()
        box.addLayout(actions)
        return page

    def enter(self) -> None:
        self.prefs.setValue("welcomed", True)
        self.stack.setCurrentWidget(self.dashboard)
        self.reload()

    def _keys(self) -> QWidget:
        page, box = self._page(
            "Connect your Alpaca account",
            "Paste your market-data keys once. Your operating system keeps them in its credential store.",
        )
        self.key_fields = []
        for title in ("API key", "Secret key"):
            box.addWidget(label(title))
            field = QLineEdit()
            field.setEchoMode(QLineEdit.EchoMode.Password)
            field.setMaximumWidth(460)
            box.addWidget(field)
            self.key_fields.append(field)
        self.key_message = label("")
        box.addWidget(self.key_message)
        buttons = QHBoxLayout()
        for title, callback in (
            ("Save keys", self.save_keys),
            ("Back", lambda: self.stack.setCurrentWidget(self.dashboard)),
        ):
            b = QPushButton(title)
            b.clicked.connect(callback)
            buttons.addWidget(b)
        buttons.addStretch()
        box.addLayout(buttons)
        box.addStretch()
        return page

    def connect_keys(self) -> None:
        self.stack.setCurrentWidget(self.keys)
        self.key_fields[0].setFocus()

    def save_keys(self) -> None:
        from panic_detector.data.credentials import save_credentials

        values = [f.text().strip() for f in self.key_fields]
        if not all(values):
            self.key_message.setText("Paste both keys to continue.")
            return
        try:
            save_credentials(*values)
        except Exception:
            self.key_message.setText(
                "Unlock your OS keyring or set both Alpaca environment variables."
            )
            return
        for field in self.key_fields:
            field.clear()
        self.stack.setCurrentWidget(self.dashboard)
        self.drawer.apply(self.pending[-1] if hasattr(self, "pending") else False)

    def reload(self) -> None:
        self.load(self.tickers, self.window_days, self.mode, self.cutoff, False)

    def load(
        self, tickers: list[str], window: int, mode: int, cutoff: float, refresh: bool
    ) -> None:
        if self.job:
            return
        self.stop_play()
        self.fix.hide()
        self.banner.setText("Opening stock history…")
        self.pending = (tickers, window, mode, cutoff, refresh)

        def work(progress: Callable[[str], None]) -> Scene:
            rows = snapshot(tickers, window, refresh, progress, self.cache_root)
            return scene(rows, mode, cutoff)

        self.submit(work, self.ready, self.retry)

    def submit(self, work: Callable, success: Callable, retry: Callable) -> None:
        self.retry_action = retry
        self.job = Job(work)
        self.job.signals.message.connect(self.banner.setText)
        self.job.signals.ready.connect(success)
        self.job.signals.failed.connect(self.failed)
        self.drawer.setEnabled(False)
        self.pool.start(self.job)

    def failed(self, message: str, missing: bool) -> None:
        self.job = None
        self.drawer.setEnabled(True)
        self.error(
            message,
            self.connect_keys if missing else self.retry_action,
            "Connect Alpaca" if missing else "Retry",
        )
        if missing:
            self.connect_keys()

    def retry(self) -> None:
        self.load(*self.pending)

    def error(self, message: str, callback: Callable, title: str) -> None:
        self.banner.setText(message)
        self.action = callback
        self.fix.setText(title)
        self.fix.show()

    def ready(self, view: Scene) -> None:
        self.job = None
        self.drawer.setEnabled(True)
        self.view = view
        self.tickers, self.window_days, self.mode, self.cutoff, _ = self.pending
        for key, val in (
            ("symbols", self.tickers),
            ("window", self.window_days),
            ("mode", self.mode),
            ("cutoff", self.cutoff),
        ):
            self.prefs.setValue(key, val)
        omitted = sorted(set(self.tickers) - set(view.symbols))
        self.history_note = f"{len(view.symbols)} stocks   ·   {self.window_days} trading days   ·   Data through {view.rows['date'][-1]}"
        if omitted:
            self.history_note += "   ·   Insufficient history: " + ", ".join(omitted)
        self.banner.setText(self.history_note)
        self.fix.hide()
        self.map.names = [
            f"{symbol} · {SECTOR_MAP.get(symbol, 'Unclassified')}" for symbol in view.symbols
        ]
        self.map.brushes = [
            pg.mkBrush(SECTOR_COLORS.get(SECTOR_MAP.get(s, ""), "#999999")) for s in view.symbols
        ]
        for line in self.map.links:
            line.setData([], [])
        days = view.days
        # Break the trace across outages, while keeping all valid readings selectable.
        breaks = np.flatnonzero(np.diff(days) > 7) + 1
        self.curve.setData(
            x=np.insert(days.astype(float), breaks, np.nan),
            y=np.insert(view.rows["level"], breaks, np.nan),
            connect="finite",
        )
        first = min(days[0], date(2020, 3, 23).toordinal())
        self.chart.setXRange(first, days[-1], padding=0.015)
        ticks = [
            (date(y, 1, 1).toordinal(), str(y))
            for y in range(
                date.fromordinal(first).year + 1, date.fromordinal(int(days[-1])).year + 1
            )
        ]
        self.chart.getAxis("bottom").setTicks([ticks])
        for item in self.events:
            self.chart.removeItem(item)
        self.events = []
        for day, title in ((date(2020, 3, 23), "Covid crash"), (date(2022, 6, 16), "2022 selloff")):
            if day.toordinal() <= days[-1]:
                item = pg.TextItem(title, color=COLORS["muted"], anchor=(0, 0))
                item.setPos(day.toordinal(), 120)
                self.chart.addItem(item)
                self.events.append(item)
        self.date_slider.blockSignals(True)
        self.date_slider.setRange(0, len(days) - 1)
        self.date_slider.setValue(len(days) - 1)
        self.date_slider.blockSignals(False)
        self.play.setEnabled(True)
        self.select_date(len(days) - 1)

    def select_date(self, index: int) -> None:
        if self.view is None:
            return
        row = self.view.rows[index]
        day = str(row["date"])
        level = float(row["level"])
        state = classify_status(level)
        color = COLORS[state.lower()]
        if self.status.text() != state:
            self.status.setText(state)
            self.status.setStyleSheet(f"color:{color};font-size:54px;font-weight:700;")
        self.asof.setText(date.fromisoformat(day).strftime("%d %B %Y"))
        self.sentence.setText(SENTENCES[state])
        self.score.setText(f"Panic level    {level:.1f} / 100")
        self.gauge.reading(level, color)
        self.caption.setText(
            {
                "CALM": "Spread out · stocks are moving independently",
                "NERVOUS": "Drawing closer · more stocks share a move",
                "PANIC": "Bunched together · stocks are moving as one",
            }[state]
        )
        self.date_label.setText(day)
        self.marker.setValue(self.view.days[index])
        self.map.draw_frame(self.view.positions[index], self.view.lines[index])
        if self.drawer.isVisible():
            self.details(row)
        if getattr(self, "unavailable", False):
            self.unavailable = False
            self.banner.setText(self.history_note)
            self.fix.hide()

    def show_drawer(self, opened: bool) -> None:
        self.drawer.setVisible(opened)
        if opened and self.view is not None and not getattr(self, "unavailable", False):
            self.details(self.view.rows[self.date_slider.value()])

    def details(self, row) -> None:
        self.drawer.readout.setText(
            f"Stocks moving together   {row['average']:.1%}\nThe average measures how closely pairs rise and fall together.\n\nLeading eigenvalue   {row['leading']:.2f}\nOne common move accounts for {row['share']:.1%} of variation.\n\nNoise baseline   {row['noise']:.2f}\nIndependent stocks can produce a leading eigenvalue this large by chance."
        )
        from PySide6.QtCore import QDate

        self.drawer.day.setDate(QDate.fromString(str(row["date"]), "yyyy-MM-dd"))

    def select_exact(self, day: str) -> None:
        if self.view is None:
            return
        idx = int(np.searchsorted(self.view.rows["date"], day))
        if idx < len(self.view.rows) and self.view.rows["date"][idx] == day:
            self.date_slider.setValue(idx)
            self.select_date(idx)
            return
        self.stop_play()
        self.unavailable = True
        self.status.setText("No reading")
        self.status.setStyleSheet("font-size:42px;color:#99a5a3")
        self.asof.setText(day)
        self.date_label.setText(day)
        self.sentence.setText("There are too few shared trading days to score this date.")
        self.score.setText("Panic level    — / 100")
        self.gauge.reading(0, COLORS["muted"])
        self.caption.setText("No stock map for this date")
        self.drawer.readout.setText("No measured window for the selected date.")
        for line in self.map.links:
            line.setData([], [])
        self.map.dots.clear()
        self.marker.setValue(date.fromisoformat(day).toordinal())
        self.error(
            f"Readings begin {self.view.rows['date'][0]} in this cache.",
            lambda: self.select_date(self.date_slider.value()),
            "Return to history",
        )

    def toggle_play(self) -> None:
        if self.play_timer.isActive():
            self.stop_play()
        elif self.view is not None:
            self.play.setText("Pause")
            self.play_timer.start(16)

    def stop_play(self) -> None:
        self.play_timer.stop()
        self.play.setText("Play")

    def advance(self) -> None:
        self.date_slider.setValue((self.date_slider.value() + 1) % (self.date_slider.maximum() + 1))

    def capture(self):
        """Composite live graphics scenes explicitly since Qt omits GL children in grab()."""
        from PySide6.QtCore import QPoint, QRectF
        from PySide6.QtGui import QPainter
        from PySide6.QtWidgets import QGraphicsView

        pixmap = self.grab()
        if self.stack.currentWidget() == self.dashboard:
            painter = QPainter(pixmap)
            for plot in (self.map, self.chart):
                viewport = plot.viewport()
                target = QRectF(viewport.rect())
                target.moveTopLeft(viewport.mapTo(self, QPoint(0, 0)).toPointF())
                painter.fillRect(target, plot.backgroundBrush())
                QGraphicsView.render(plot, painter, target, viewport.rect())
            painter.end()
        return pixmap

    def export(self, ext: str) -> None:
        if self.view is None or self.job:
            return
        name, _ = QFileDialog.getSaveFileName(
            self, "Export history", f"market-mood.{ext}", f"{ext.upper()} (*.{ext})"
        )
        if not name:
            return
        try:
            target = selected_file(name, "." + ext)
        except ValueError as exc:
            self.error(str(exc), lambda: self.export(ext), "Choose file")
            return
        self.stop_play()
        if ext == "png":
            if not self.capture().save(str(target)):
                self.error(
                    "Choose a writable location for the image.",
                    lambda: self.export(ext),
                    "Choose file",
                )
            return
        from panic_detector.viz.animation import export_animation

        view = self.view
        self.banner.setText("Exporting historical replay…")
        self.submit(
            lambda _: export_animation(view, target), self.exported, lambda: self.export(ext)
        )

    def exported(self, _: object) -> None:
        self.job = None
        self.drawer.setEnabled(True)
        self.banner.setText("Replay saved.")

    def closeEvent(self, event: QCloseEvent) -> None:
        self.stop_play()
        if self.pool.activeThreadCount():
            self.hide()
            event.ignore()
            QTimer.singleShot(100, self.close)
            return
        event.accept()
