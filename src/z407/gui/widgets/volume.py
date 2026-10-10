"""Volume control widget: a pair of - / + buttons."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

# Auto-repeat timing (ms) so holding a button keeps stepping
REPEAT_DELAY_MS = 400
REPEAT_INTERVAL_MS = 250


class VolumeWidget(QWidget):
    """Volume Down / Volume Up buttons."""

    volume_up_requested = Signal()
    volume_down_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title = QLabel("Volume")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        row = QHBoxLayout()
        row.setSpacing(6)

        for text, signal in (
            ("− Volume", self.volume_down_requested),
            ("+ Volume", self.volume_up_requested),
        ):
            btn = QPushButton(text)
            btn.setAutoRepeat(True)
            btn.setAutoRepeatDelay(REPEAT_DELAY_MS)
            btn.setAutoRepeatInterval(REPEAT_INTERVAL_MS)
            btn.clicked.connect(signal)
            row.addWidget(btn, stretch=1)

        layout.addLayout(row)
