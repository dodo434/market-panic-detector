"""Small labelled controls and a sector map drawn with persistent plot items."""

from datetime import date
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSlider,
    QWidget,
    QMessageBox,
)
from panic_detector.viz.theme import COLORS


def icon() -> QIcon:
    pix = QPixmap(64, 64)
    pix.fill(QColor(COLORS["background"]))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(COLORS["calm"]), 5))
    for x, h in ((10, 13), (20, 24), (31, 42), (42, 27), (53, 14)):
        p.drawLine(x, 32 - h // 2, x, 32 + h // 2)
    p.end()
    return QIcon(pix)


def label(text: str, style: str = "") -> QLabel:
    widget = QLabel(text)
    widget.setObjectName(style)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


def rule(vertical: bool = False) -> QFrame:
    line = QFrame()
    line.setObjectName("line")
    if vertical:
        line.setFixedWidth(1)
    else:
        line.setFixedHeight(1)
    return line


def heading(text: str, explanation: str, parent: QWidget) -> QHBoxLayout:
    bar = QHBoxLayout()
    bar.addWidget(label(text, "heading"))
    bar.addStretch()
    help_button = QPushButton("?")
    help_button.setObjectName("help")
    help_button.setAccessibleName(f"About {text}")
    help_button.clicked.connect(lambda: QMessageBox.information(parent, text, explanation))
    bar.addWidget(help_button)
    return bar


def slider(low: int, high: int, value: int) -> QSlider:
    s = QSlider(Qt.Orientation.Horizontal)
    s.setRange(low, high)
    s.setValue(value)
    return s


class YearAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [str(date.fromordinal(int(v)).year) if v >= 1 else "" for v in values]


class Gauge(QProgressBar):
    """Ease the meter between historical readings while the number remains precise."""

    def __init__(self) -> None:
        super().__init__()
        self.setTextVisible(False)
        self.setFixedHeight(6)
        self.animation = QPropertyAnimation(self, b"value", self)
        self.animation.setDuration(120)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def reading(self, level: float, color: str) -> None:
        if self.property("tone") != color:
            self.setProperty("tone", color)
            self.setStyleSheet(
                f"QProgressBar {{background:#303739;border:0}} QProgressBar::chunk {{background:{color}}}"
            )
        self.animation.stop()
        self.animation.setStartValue(max(0, self.value()))
        self.animation.setEndValue(round(level))
        self.animation.start()


class Map(pg.PlotWidget):
    def __init__(self) -> None:
        super().__init__(background=COLORS["background"])
        self.setAspectLocked(True)
        self.hideAxis("bottom")
        self.hideAxis("left")
        self.setXRange(-1.1, 1.1, padding=0)
        self.setYRange(-1.1, 1.1, padding=0)
        self.setMouseEnabled(x=False, y=False)
        self.setMenuEnabled(False)
        self.hideButtons()
        self.links = [
            pg.PlotCurveItem(pen=pg.mkPen(c, width=1), connect="pairs", skipFiniteCheck=True)
            for c in ("#303e3d", "#263132", "#526662")
        ]
        for item in self.links:
            self.addItem(item)
        self.names: list[str] = []
        self.dots = pg.ScatterPlotItem(
            size=8,
            pen=pg.mkPen(COLORS["background"]),
            pxMode=True,
            hoverable=True,
            tip=lambda x, y, data: str(data),
        )
        self.addItem(self.dots)
        self.brushes: list = []

    def draw_frame(self, points: np.ndarray, edges: tuple[np.ndarray, ...]) -> None:
        for line, coords in zip(self.links, edges):
            line.setData(x=coords[0], y=coords[1], connect="pairs", skipFiniteCheck=True)
        self.dots.setData(x=points[:, 0], y=points[:, 1], brush=self.brushes, data=self.names)
