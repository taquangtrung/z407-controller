"""Pairing mode button with countdown timer."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

IDLE_TEXT = "📡  Pair"
IDLE_TOOLTIP = "Make the speaker discoverable for 120 s so a new device can pair with it"
ACTIVE_TOOLTIP = "Pairing mode active: open Bluetooth settings on your device"


class PairingWidget(QWidget):
    """Compact button to enter pairing mode, with a countdown on the button."""

    pair_requested = Signal()

    PAIRING_DURATION = 120  # seconds

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._btn = QPushButton(IDLE_TEXT)
        self._btn.setToolTip(IDLE_TOOLTIP)
        self._btn.clicked.connect(self._on_click)
        layout.addWidget(self._btn)

        # Countdown timer
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._tick)
        self._remaining = 0

    def _on_click(self) -> None:
        self._btn.setEnabled(False)
        self._remaining = self.PAIRING_DURATION
        self._update_countdown_text()
        self._countdown_timer.start()
        self.pair_requested.emit()

    def _tick(self) -> None:
        self._remaining -= 1
        if self._remaining <= 0:
            self.reset()
        else:
            self._update_countdown_text()

    def _update_countdown_text(self) -> None:
        self._btn.setText(f"📡  {self._remaining}s")
        self._btn.setToolTip(ACTIVE_TOOLTIP)

    def reset(self) -> None:
        """Reset the widget to its idle state."""
        self._countdown_timer.stop()
        self._remaining = 0
        self._btn.setEnabled(True)
        self._btn.setText(IDLE_TEXT)
        self._btn.setToolTip(IDLE_TOOLTIP)
