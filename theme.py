"""Dark trading-terminal theme constants and Qt stylesheet."""

COLORS = {
    "background": "#071018",
    "panel": "#0C1722",
    "panel_alt": "#101E2A",
    "border": "#1E3343",
    "text": "#DDEAF2",
    "muted": "#839CAA",
    "cyan": "#25D7F2",
    "green": "#36D399",
    "amber": "#FFB020",
    "red": "#FF4D67",
}

STYLESHEET = f"""
* {{ font-family: "Inter", "Segoe UI", sans-serif; color: {COLORS["text"]}; }}
QWidget {{ background: {COLORS["background"]}; }}
QFrame#panel, QGroupBox {{
    background: {COLORS["panel"]}; border: 1px solid {COLORS["border"]}; border-radius: 8px;
}}
QGroupBox {{ margin-top: 10px; padding: 8px; font-weight: 600; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}
QPushButton {{
    background: {COLORS["panel_alt"]}; border: 1px solid {COLORS["border"]};
    border-radius: 5px; padding: 8px 12px; font-weight: 600;
}}
QPushButton:hover {{ border-color: {COLORS["cyan"]}; color: {COLORS["cyan"]}; }}
QSlider::groove:horizontal {{ height: 5px; background: {COLORS["border"]}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    width: 14px; margin: -5px 0; border-radius: 7px; background: {COLORS["cyan"]};
}}
QComboBox, QPlainTextEdit, QLineEdit {{
    background: {COLORS["panel_alt"]}; border: 1px solid {COLORS["border"]};
    border-radius: 5px; padding: 6px;
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QToolTip {{
    background: {COLORS["panel_alt"]}; color: {COLORS["text"]};
    border: 1px solid {COLORS["cyan"]};
}}
"""
