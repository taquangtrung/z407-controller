"""Main application window for the Z407 native GUI."""

from __future__ import annotations

import logging

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from qasync import asyncSlot

from z407.controller import Z407Controller
from z407.gui.bridge import ControllerBridge
from z407.gui.style import STYLESHEET
from z407.gui.widgets.bass import BassWidget
from z407.gui.widgets.input_source import InputSourceWidget
from z407.gui.widgets.pairing import PairingWidget
from z407.gui.widgets.playback import PlaybackWidget
from z407.gui.widgets.status_bar import StatusBar
from z407.gui.widgets.volume import VolumeWidget

logger = logging.getLogger(__name__)


def _make_section(widget: QWidget) -> QFrame:
    """Wrap *widget* in a styled section frame."""
    frame = QFrame()
    frame.setObjectName("section")
    layout = QVBoxLayout(frame)
    # Margins handled by QSS padding — avoid double-padding that clips content
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(widget)
    return frame


class MainWindow(QMainWindow):
    """Z407 Controller main window."""

    def __init__(
        self,
        controller: Z407Controller,
        bridge: ControllerBridge,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._bridge = bridge

        self.setWindowTitle("Z407 Controller")
        self.setFixedWidth(380)
        self.setMinimumHeight(520)

        self._build_ui()
        self._connect_signals()
        self._setup_tray()

    # -- UI construction ----------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Status bar
        self._status_bar = StatusBar()
        main_layout.addWidget(self._status_bar)

        # Volume
        self._volume = VolumeWidget()
        main_layout.addWidget(_make_section(self._volume))

        # Bass
        self._bass = BassWidget()
        main_layout.addWidget(_make_section(self._bass))

        # Playback
        self._playback = PlaybackWidget()
        main_layout.addWidget(_make_section(self._playback))

        # Input source
        self._input_source = InputSourceWidget()
        main_layout.addWidget(_make_section(self._input_source))

        # Pairing
        self._pairing = PairingWidget()
        main_layout.addWidget(_make_section(self._pairing))

        # Factory reset — flat, no card wrapper
        self._reset_btn = QPushButton("⚠️  Factory Reset")
        self._reset_btn.setObjectName("dangerBtn")
        self._reset_btn.clicked.connect(self._on_factory_reset)
        main_layout.addWidget(self._reset_btn)

        main_layout.addStretch()

    # -- Signal wiring ------------------------------------------------------

    def _connect_signals(self) -> None:
        # Bridge → widgets
        self._bridge.state_changed.connect(self._status_bar.set_state)
        self._bridge.volume_changed.connect(self._volume.set_volume)
        self._bridge.input_changed.connect(self._input_source.set_active)

        # Widgets → controller (async)
        self._volume.volume_up_requested.connect(self._on_volume_up)
        self._volume.volume_down_requested.connect(self._on_volume_down)
        self._bass.bass_up_requested.connect(self._on_bass_up)
        self._bass.bass_down_requested.connect(self._on_bass_down)
        self._playback.play_pause_requested.connect(self._on_play_pause)
        self._playback.next_requested.connect(self._on_next_track)
        self._playback.prev_requested.connect(self._on_prev_track)
        self._input_source.input_requested.connect(self._on_switch_input)
        self._pairing.pair_requested.connect(self._on_pair)

    # -- System tray --------------------------------------------------------

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.info("System tray not available — skipping tray icon")
            return

        self._tray = QSystemTrayIcon(self)
        self._tray.setToolTip("Z407 Controller")

        # Use application icon or a default
        icon = QApplication.instance().windowIcon()
        if icon.isNull():
            icon = QIcon.fromTheme("audio-speakers")
        self._tray.setIcon(icon)

        # Context menu
        menu = QMenu()
        vol_up = QAction("Volume Up", self)
        vol_up.triggered.connect(self._on_volume_up_tray)
        menu.addAction(vol_up)

        vol_down = QAction("Volume Down", self)
        vol_down.triggered.connect(self._on_volume_down_tray)
        menu.addAction(vol_down)

        menu.addSeparator()

        play = QAction("Play / Pause", self)
        play.triggered.connect(self._on_play_pause)
        menu.addAction(play)

        menu.addSeparator()

        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self._show_from_tray)
        menu.addAction(show_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _quit_app(self) -> None:
        QApplication.instance().quit()

    # -- Close to tray ------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802
        if hasattr(self, "_tray") and self._tray.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

    # -- Async controller slots ---------------------------------------------

    @asyncSlot(int)
    async def _on_volume_up(self, steps: int = 1) -> None:
        try:
            await self._controller.volume_up(steps=steps)
        except Exception:
            logger.exception("Volume up failed")

    @asyncSlot(int)
    async def _on_volume_down(self, steps: int = 1) -> None:
        try:
            await self._controller.volume_down(steps=steps)
        except Exception:
            logger.exception("Volume down failed")

    @asyncSlot()
    async def _on_volume_up_tray(self) -> None:
        try:
            await self._controller.volume_up(steps=1)
        except Exception:
            logger.exception("Volume up failed")

    @asyncSlot()
    async def _on_volume_down_tray(self) -> None:
        try:
            await self._controller.volume_down(steps=1)
        except Exception:
            logger.exception("Volume down failed")

    @asyncSlot()
    async def _on_bass_up(self) -> None:
        try:
            await self._controller.bass_up()
        except Exception:
            logger.exception("Bass up failed")

    @asyncSlot()
    async def _on_bass_down(self) -> None:
        try:
            await self._controller.bass_down()
        except Exception:
            logger.exception("Bass down failed")

    @asyncSlot()
    async def _on_play_pause(self) -> None:
        try:
            await self._controller.play_pause()
        except Exception:
            logger.exception("Play/pause failed")

    @asyncSlot()
    async def _on_next_track(self) -> None:
        try:
            await self._controller.next_track()
        except Exception:
            logger.exception("Next track failed")

    @asyncSlot()
    async def _on_prev_track(self) -> None:
        try:
            await self._controller.prev_track()
        except Exception:
            logger.exception("Previous track failed")

    @asyncSlot(str)
    async def _on_switch_input(self, source: str) -> None:
        try:
            await self._controller.switch_input(source)
        except Exception:
            logger.exception("Switch input failed")

    @asyncSlot()
    async def _on_pair(self) -> None:
        try:
            await self._controller.pair_device_and_switch()
        except Exception:
            logger.exception("Pairing failed")

    def _on_factory_reset(self) -> None:
        result = QMessageBox.warning(
            self,
            "Factory Reset",
            "Factory reset the speaker? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            self._do_factory_reset()

    @asyncSlot()
    async def _do_factory_reset(self) -> None:
        try:
            await self._controller.factory_reset()
            logger.info("Factory reset command sent")
        except Exception:
            logger.exception("Factory reset failed")
