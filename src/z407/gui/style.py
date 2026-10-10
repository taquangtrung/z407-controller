"""Dark theme QSS stylesheet for the Z407 native GUI.

macOS-inspired dark mode:
- Background: #1e1e1e
- Surface:    #2a2a2a
- Accent:     #0a84ff  (macOS blue)
"""

# Color palette — macOS dark mode
BG = "#1e1e1e"
SURFACE = "#2a2a2a"
BORDER = "#3a3a3c"
TEXT = "#f5f5f7"
TEXT_DIM = "#86868b"
ACCENT = "#0a84ff"
ACCENT_HOVER = "#409cff"
GREEN = "#30d158"
RED = "#ff453a"
YELLOW = "#ffd60a"

STYLESHEET = f"""
/* ── Global ─────────────────────────────────────────── */

QMainWindow, QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: -apple-system, 'SF Pro Text', 'Helvetica Neue', 'Segoe UI', sans-serif;
    font-size: 13px;
}}

/* ── Section Frames ─────────────────────────────────── */

QFrame#section {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 12px;
}}

/* ── Labels ─────────────────────────────────────────── */

QLabel {{
    color: {TEXT};
    background: transparent;
    border: none;
}}

QLabel#sectionTitle {{
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: {TEXT_DIM};
    margin-bottom: 2px;
}}

QLabel#statusDot {{
    min-width: 8px;
    max-width: 8px;
    min-height: 8px;
    max-height: 8px;
    border-radius: 4px;
    background-color: {RED};
}}

QLabel#statusDot[state="connected"] {{
    background-color: {GREEN};
}}

QLabel#statusDot[state="connecting"],
QLabel#statusDot[state="scanning"],
QLabel#statusDot[state="handshaking"] {{
    background-color: {YELLOW};
}}

QLabel#statusDot[state="disconnected"] {{
    background-color: {RED};
}}

/* ── Push Buttons ───────────────────────────────────── */

QPushButton {{
    background-color: #333336;
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
    min-height: 28px;
}}

QPushButton:hover {{
    background-color: #3a3a3e;
    border-color: #48484a;
}}

QPushButton:pressed {{
    background-color: #2c2c2e;
}}

QPushButton:disabled {{
    opacity: 0.35;
    color: #636366;
}}

QPushButton#iconBtn {{
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    border-radius: 8px;
    font-size: 15px;
    padding: 0;
}}

QPushButton#playBtn {{
    min-width: 44px;
    max-width: 44px;
    min-height: 44px;
    max-height: 44px;
    border-radius: 22px;
    background-color: {ACCENT};
    border: none;
    font-size: 17px;
    color: #ffffff;
}}

QPushButton#playBtn:hover {{
    background-color: {ACCENT_HOVER};
}}

QPushButton#playBtn:pressed {{
    background-color: #0070e0;
}}

QPushButton#playBtn:disabled {{
    background-color: #2c2c2e;
    color: #636366;
}}

QPushButton#accentBtn {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    color: #ffffff;
    font-weight: 600;
}}

QPushButton#accentBtn:hover {{
    background-color: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}

QPushButton#accentBtn:disabled {{
    background-color: #1a3a5c;
    border-color: #1a3a5c;
    color: #636366;
}}

QPushButton#dangerBtn {{
    color: {RED};
    border-color: {BORDER};
    background-color: transparent;
    font-size: 12px;
}}

QPushButton#dangerBtn:hover {{
    background-color: #3a2020;
    border-color: #5a2828;
}}

QPushButton#dangerBtn:disabled {{
    color: #636366;
}}

QPushButton#inputBtn {{
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    min-height: 30px;
    padding: 5px 4px;
}}

QPushButton#inputBtn[active="true"] {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    color: #ffffff;
}}

QPushButton#inputBtn[active="true"]:disabled {{
    background-color: #1a3a5c;
    border-color: #1a3a5c;
    color: #636366;
}}

/* ── Message Box ────────────────────────────────────── */

QMessageBox {{
    background-color: {SURFACE};
}}

QMessageBox QLabel {{
    color: {TEXT};
    font-size: 13px;
}}

QMessageBox QPushButton {{
    min-width: 80px;
}}

/* ── System Tray Menu ───────────────────────────────── */

QMenu {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 4px 20px 4px 12px;
    border-radius: 4px;
    color: {TEXT};
}}

QMenu::item:selected {{
    background-color: {ACCENT};
    color: #ffffff;
}}

QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 8px;
}}
"""
