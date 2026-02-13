"""Playback control widget (previous, play/pause, next)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class PlaybackWidget(QWidget):
    """Play/Pause, Next, and Previous buttons."""

    play_pause_requested = Signal()
    next_requested = Signal()
    prev_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title = QLabel("Playback")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch()

        # Previous
        btn_prev = QPushButton("⏮")
        btn_prev.setObjectName("iconBtn")
        btn_prev.clicked.connect(self.prev_requested)
        row.addWidget(btn_prev)

        # Play/Pause (larger, accent)
        btn_play = QPushButton("⏯")
        btn_play.setObjectName("playBtn")
        btn_play.clicked.connect(self.play_pause_requested)
        row.addWidget(btn_play)

        # Next
        btn_next = QPushButton("⏭")
        btn_next.setObjectName("iconBtn")
        btn_next.clicked.connect(self.next_requested)
        row.addWidget(btn_next)

        row.addStretch()
        layout.addLayout(row)
