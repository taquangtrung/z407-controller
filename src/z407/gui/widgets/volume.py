"""Volume control widget with slider and +/- buttons."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class VolumeWidget(QWidget):
    """Volume slider with +/- buttons and percentage label.

    Emits :pyattr:`volume_change_requested` when the user drags the
    slider (debounced) or clicks +/-.
    """

    volume_up_requested = Signal(int)    # steps
    volume_down_requested = Signal(int)  # steps

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Section title + volume label in one row
        header = QHBoxLayout()
        title = QLabel("Volume")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()
        self._label = QLabel("50%")
        self._label.setObjectName("volumeLabel")
        header.addWidget(self._label)
        layout.addLayout(header)

        # Slider row
        row = QHBoxLayout()
        row.setSpacing(8)

        # Minus button
        self._btn_down = QPushButton("−")
        self._btn_down.setObjectName("iconBtn")
        self._btn_down.setAutoRepeat(True)
        self._btn_down.setAutoRepeatInterval(200)
        self._btn_down.setAutoRepeatDelay(400)
        self._btn_down.clicked.connect(lambda: self.volume_down_requested.emit(1))
        row.addWidget(self._btn_down)

        # Slider
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setSingleStep(5)
        self._slider.setPageStep(10)
        self._slider.setValue(50)
        row.addWidget(self._slider, stretch=1)

        # Plus button
        self._btn_up = QPushButton("+")
        self._btn_up.setObjectName("iconBtn")
        self._btn_up.setAutoRepeat(True)
        self._btn_up.setAutoRepeatInterval(200)
        self._btn_up.setAutoRepeatDelay(400)
        self._btn_up.clicked.connect(lambda: self.volume_up_requested.emit(1))
        row.addWidget(self._btn_up)

        layout.addLayout(row)

        # Debounce timer for slider drags
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(50)
        self._debounce_timer.timeout.connect(self._on_slider_debounced)

        self._last_sent_value: int = 50
        self._slider.valueChanged.connect(self._on_slider_moved)
        self._slider.sliderReleased.connect(self._on_slider_debounced)

    def _on_slider_moved(self, value: int) -> None:
        """Update the label immediately; debounce the BLE command."""
        self._label.setText(f"{value}%")
        if self._slider.isSliderDown():
            self._debounce_timer.start()
        else:
            # Programmatic change — don't send command
            pass

    def _on_slider_debounced(self) -> None:
        """Send the volume change after the debounce interval."""
        value = self._slider.value()
        delta = value - self._last_sent_value
        if delta == 0:
            return
        steps = abs(delta) // 5
        if steps == 0:
            return
        if delta > 0:
            self.volume_up_requested.emit(steps)
        else:
            self.volume_down_requested.emit(steps)
        self._last_sent_value = value

    def set_volume(self, value: int) -> None:
        """Update the slider without triggering a command."""
        self._slider.blockSignals(True)
        self._slider.setValue(value)
        self._slider.blockSignals(False)
        self._label.setText(f"{value}%")
        self._last_sent_value = value
