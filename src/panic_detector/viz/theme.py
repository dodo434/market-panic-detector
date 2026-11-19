"""Flat terminal palette shared by widgets, plots and exports."""

from panic_detector.config import load_settings

COLORS = load_settings().theme
STYLESHEET = """
QWidget { background: #0e1013; color: #e4e8e6; font-family: 'DejaVu Sans', 'Segoe UI', sans-serif; font-size: 13px; }
QLabel#brand { font-size: 20px; font-weight: 650; }
QLabel#heading { font-size: 17px; font-weight: 600; }
QLabel#muted, QLabel#meta { color: #99a5a3; }
QLabel#meta { font-family: monospace; font-size: 12px; }
QPushButton { border: 1px solid #394142; padding: 6px 12px; }
QPushButton:hover, QPushButton:checked { color: #72c2b0; border-color: #72c2b0; }
QPushButton:disabled { color: #677270; }
QPushButton#help { border: 0; padding: 0 4px; color: #99a5a3; }
QFrame#line { background: #303739; }
QSlider::groove:horizontal { height: 3px; background: #353e40; }
QSlider::sub-page:horizontal { background: #659f93; }
QSlider::handle:horizontal { width: 10px; margin: -6px 0; background: #b6d7cf; }
QLineEdit, QPlainTextEdit, QComboBox, QDateEdit { border: 1px solid #394142; padding: 6px; }
QTabWidget::pane { border: 0; }
QTabBar::tab { padding: 8px 12px; color: #99a5a3; }
QTabBar::tab:selected { color: #72c2b0; border-bottom: 1px solid #72c2b0; }
"""
