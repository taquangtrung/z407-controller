"""Pairing mode widget with countdown timer."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class PairingWidget(QWidget):
    """Button to enter pairing mode with a countdown timer."""

    pair_requested = Signal()

    PAIRING_DURATION = 120  # seconds

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title = QLabel("Pairing")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self._btn = QPushButton("📡  Pair New Device")
        self._btn.setObjectName("accentBtn")
        self._btn.clicked.connect(self._on_click)
        layout.addWidget(self._btn)

        self._status = QLabel("Activates pairing mode for 120 s")
        self._status.setObjectName("sectionTitle")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

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
            self._countdown_timer.stop()
            self._btn.setEnabled(True)
            self._btn.setText("📡  Pair New Device")
            self._status.setText("Done — Bluetooth active")
        else:
            self._update_countdown_text()

    def _update_countdown_text(self) -> None:
        self._btn.setText(f"📡  Pairing… {self._remaining}s")
        self._status.setText(
            "Pairing mode active — open Bluetooth settings on your device"
        )

    def reset(self) -> None:
        """Reset the widget to its idle state."""
        self._countdown_timer.stop()
        self._remaining = 0
        self._btn.setEnabled(True)
        self._btn.setText("📡  Pair New Device")
        self._status.setText("Activates pairing mode for 120 s")
