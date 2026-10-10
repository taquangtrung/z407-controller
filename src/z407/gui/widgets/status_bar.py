"""Connection status indicator widget."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class StatusBar(QWidget):
    """Displays connection state with a colored dot, text label and connect button."""

    connect_requested = Signal()
    disconnect_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Colored status dot
        self._dot = QLabel()
        self._dot.setObjectName("statusDot")
        self._dot.setFixedSize(10, 10)
        self._dot.setProperty("state", "disconnected")
        layout.addWidget(self._dot)

        # Status text
        self._label = QLabel("Disconnected")
        layout.addWidget(self._label)

        layout.addStretch()

        # Connect / Cancel / Disconnect, depending on the current state
        self._btn = QPushButton("Connect")
        self._btn.clicked.connect(self._on_click)
        layout.addWidget(self._btn)

        self._layout = layout
        self._state = "disconnected"

    def add_action(self, widget: QWidget) -> None:
        """Append *widget* to the right-hand side, after the connect button."""
        self._layout.addWidget(widget)

    def _on_click(self) -> None:
        if self._state == "disconnected":
            self.connect_requested.emit()
        else:
            self.disconnect_requested.emit()

    def set_state(self, state: str) -> None:
        """Update the display for a new connection state.

        Parameters
        ----------
        state:
            One of ``'disconnected'``, ``'scanning'``, ``'connecting'``,
            ``'handshaking'``, ``'connected'``.
        """
        self._dot.setProperty("state", state)
        # Force style re-evaluation after dynamic property change
        self._dot.style().unpolish(self._dot)
        self._dot.style().polish(self._dot)
        self._dot.update()

        display = {
            "disconnected": "Disconnected",
            "scanning": "Scanning…",
            "connecting": "Connecting…",
            "handshaking": "Handshaking…",
            "connected": "Connected",
        }.get(state, state.capitalize())
        self._label.setText(display)

        self._state = state
        self._btn.setText({
            "disconnected": "Connect",
            "connected": "Disconnect",
        }.get(state, "Cancel"))
