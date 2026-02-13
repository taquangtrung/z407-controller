"""Input source selector widget (Bluetooth / AUX / USB)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class InputSourceWidget(QWidget):
    """Exclusive toggle group for input source selection."""

    input_requested = Signal(str)  # source name

    SOURCES = ("bluetooth", "aux", "usb")
    LABELS = {"bluetooth": "Bluetooth", "aux": "AUX", "usb": "USB"}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title = QLabel("Input Source")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        row = QHBoxLayout()
        row.setSpacing(6)

        self._buttons: dict[str, QPushButton] = {}
        for source in self.SOURCES:
            btn = QPushButton(self.LABELS[source])
            btn.setObjectName("inputBtn")
            btn.setProperty("active", "false")
            btn.setCheckable(False)
            btn.clicked.connect(lambda checked=False, s=source: self._on_click(s))
            row.addWidget(btn, stretch=1)
            self._buttons[source] = btn

        layout.addLayout(row)

    def _on_click(self, source: str) -> None:
        self.input_requested.emit(source)

    def set_active(self, source: str) -> None:
        """Highlight the active input source button."""
        for name, btn in self._buttons.items():
            is_active = name == source
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()
