"""Bass control widget."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class BassWidget(QWidget):
    """Bass Up / Bass Down buttons."""

    bass_up_requested = Signal()
    bass_down_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title = QLabel("Bass")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        row = QHBoxLayout()
        row.setSpacing(6)

        btn_down = QPushButton("− Bass")
        btn_down.setAutoRepeat(True)
        btn_down.setAutoRepeatInterval(250)
        btn_down.setAutoRepeatDelay(400)
        btn_down.clicked.connect(self.bass_down_requested)
        row.addWidget(btn_down, stretch=1)

        btn_up = QPushButton("+ Bass")
        btn_up.setAutoRepeat(True)
        btn_up.setAutoRepeatInterval(250)
        btn_up.setAutoRepeatDelay(400)
        btn_up.clicked.connect(self.bass_up_requested)
        row.addWidget(btn_up, stretch=1)

        layout.addLayout(row)
