"""PySide6 application entry point with qasync event loop integration.

Launches the native Z407 Controller GUI with an asyncio-compatible
Qt event loop so that the fully-async controller layer works seamlessly.
"""

from __future__ import annotations

import asyncio
import logging
import sys

import qasync
from PySide6.QtWidgets import QApplication

from z407.controller import Z407Controller
from z407.gui.bridge import ControllerBridge
from z407.gui.main_window import MainWindow
from z407.gui.style import STYLESHEET

logger = logging.getLogger(__name__)


def run_gui() -> None:
    """Launch the native PySide6 GUI."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Z407 Controller")
    app.setOrganizationName("z407")
    app.setStyleSheet(STYLESHEET)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Controller ↔ UI bridge
    bridge = ControllerBridge()
    controller = Z407Controller(
        on_state_change=bridge.on_state_change,
        on_volume_change=bridge.on_volume_change,
        on_input_change=bridge.on_input_change,
    )

    window = MainWindow(controller, bridge)
    window.show()

    with loop:
        # Start the BLE maintenance loop as a background task
        loop.create_task(controller.start())

        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(controller.stop())
