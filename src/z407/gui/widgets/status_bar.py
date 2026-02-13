"""Connection status indicator widget."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class StatusBar(QWidget):
    """Displays connection state with a colored dot and text label."""

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
