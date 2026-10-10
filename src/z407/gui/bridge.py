"""Bridge between the async Z407Controller and Qt signal/slot system.

The ``ControllerBridge`` receives callbacks from the controller (which
fire on the asyncio event loop thread — same thread with qasync) and
re-emits them as Qt signals so widgets can safely connect.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from z407.connection import ConnectionState


class ControllerBridge(QObject):
    """Thread-safe bridge from controller callbacks to Qt signals."""

    state_changed = Signal(str)       # ConnectionState.value
    input_changed = Signal(str)       # 'bluetooth', 'aux', 'usb'

    def on_state_change(self, state: ConnectionState) -> None:
        """Controller callback — emits :pyattr:`state_changed`."""
        self.state_changed.emit(state.value)

    def on_input_change(self, source: str) -> None:
        """Controller callback — emits :pyattr:`input_changed`."""
        self.input_changed.emit(source)
