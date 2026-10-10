"""PySide6 application entry point with qasync event loop integration.

Launches the native Z407 Controller GUI with an asyncio-compatible
Qt event loop so that the fully-async controller layer works seamlessly.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

import qasync
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from z407.controller import Z407Controller
from z407.gui.bridge import ControllerBridge
from z407.gui.main_window import MainWindow
from z407.gui.style import STYLESHEET

logger = logging.getLogger(__name__)

ICON_PATH = Path(__file__).parent / "static" / "icon.svg"

# Interval at which Qt yields to Python so SIGINT (Ctrl+C) can be handled
SIGNAL_POLL_MS = 200


def run_gui() -> None:
    """Launch the native PySide6 GUI."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Z407 Controller")
    app.setOrganizationName("z407")
    # Matches the .desktop file name so launchers and taskbars group the window
    app.setDesktopFileName("z407-gui")
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    app.setStyleSheet(STYLESHEET)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Controller ↔ UI bridge
    bridge = ControllerBridge()
    controller = Z407Controller(
        on_state_change=bridge.on_state_change,
        on_input_change=bridge.on_input_change,
    )

    window = MainWindow(controller, bridge)
    window.show()

    # Qt's C++ event loop blocks Python signal handlers; a periodic no-op timer
    # lets the interpreter run so Ctrl+C can stop the loop.
    signal.signal(signal.SIGINT, lambda *_: loop.stop())
    wakeup = QTimer()
    wakeup.start(SIGNAL_POLL_MS)
    wakeup.timeout.connect(lambda: None)

    with loop:
        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(controller.stop())
