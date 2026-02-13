"""High-level controller for the Logitech Z407 speaker.

Wraps :class:`Z407Connection` to provide a user-friendly API for volume,
bass, playback, input switching, and pairing.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

from z407.connection import ConnectionState, Z407Connection
from z407.protocol import (
    INPUT_COMMANDS,
    SOURCE_RESPONSE_MAP,
    Command,
    Response,
    is_confirmation,
)

logger = logging.getLogger(__name__)

# Volume estimation constants
VOLUME_STEP = 5
VOLUME_MIN = 0
VOLUME_MAX = 100
VOLUME_DEFAULT = 50

# Short delay between multi-step commands (seconds)
COMMAND_DELAY = 0.05


class Z407Controller:
    """High-level controller for the Z407 speaker.

    Parameters
    ----------
    on_state_change:
        Optional callback invoked on connection-state changes.  The
        callback receives a :class:`ConnectionState` value.
    on_volume_change:
        Optional callback invoked when the estimated volume changes.
    on_input_change:
        Optional callback invoked when the active input source changes.
    """

    def __init__(
        self,
        on_state_change: Callable[[ConnectionState], None] | None = None,
        on_volume_change: Callable[[int], None] | None = None,
        on_input_change: Callable[[str], None] | None = None,
    ) -> None:
        self._on_state_change = on_state_change
        self._on_volume_change = on_volume_change
        self._on_input_change = on_input_change

        self._connection = Z407Connection(
            on_response=self._handle_response,
            on_state_change=self._forward_state_change,
        )

        self._volume_estimate: int = VOLUME_DEFAULT
        self._active_input: str | None = None

    # -- Properties ---------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._connection.is_connected

    @property
    def state(self) -> ConnectionState:
        return self._connection.state

    @property
    def volume(self) -> int:
        """Estimated volume level (0–100)."""
        return self._volume_estimate

    @property
    def active_input(self) -> str | None:
        """Currently active input source, or ``None`` if unknown."""
        return self._active_input

    # -- Lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        """Start the background connection-maintenance loop."""
        await self._connection.maintain()

    async def stop(self) -> None:
        """Stop the controller and disconnect."""
        await self._connection.stop()

    # -- Volume -------------------------------------------------------------

    async def volume_up(self, steps: int = 1) -> None:
        """Increase volume by *steps* increments."""
        for _ in range(steps):
            await self._connection.send_command(Command.VOLUME_UP)
            self._volume_estimate = min(self._volume_estimate + VOLUME_STEP, VOLUME_MAX)
            if steps > 1:
                await asyncio.sleep(COMMAND_DELAY)
        self._notify_volume()

    async def volume_down(self, steps: int = 1) -> None:
        """Decrease volume by *steps* increments."""
        for _ in range(steps):
            await self._connection.send_command(Command.VOLUME_DOWN)
            self._volume_estimate = max(self._volume_estimate - VOLUME_STEP, VOLUME_MIN)
            if steps > 1:
                await asyncio.sleep(COMMAND_DELAY)
        self._notify_volume()

    def set_volume_estimate(self, value: int) -> None:
        """Manually set the volume estimate (0–100)."""
        self._volume_estimate = max(VOLUME_MIN, min(VOLUME_MAX, value))
        self._notify_volume()

    # -- Bass ---------------------------------------------------------------

    async def bass_up(self, steps: int = 1) -> None:
        for _ in range(steps):
            await self._connection.send_command(Command.BASS_UP)
            if steps > 1:
                await asyncio.sleep(COMMAND_DELAY)

    async def bass_down(self, steps: int = 1) -> None:
        for _ in range(steps):
            await self._connection.send_command(Command.BASS_DOWN)
            if steps > 1:
                await asyncio.sleep(COMMAND_DELAY)

    # -- Playback -----------------------------------------------------------

    async def play_pause(self) -> None:
        await self._connection.send_command(Command.PLAY_PAUSE)

    async def next_track(self) -> None:
        await self._connection.send_command(Command.NEXT_TRACK)

    async def prev_track(self) -> None:
        await self._connection.send_command(Command.PREV_TRACK)

    # -- Input switching ----------------------------------------------------

    async def switch_input(self, source: str) -> None:
        """Switch input to *source* (``'bluetooth'``, ``'aux'``, or ``'usb'``).

        Raises :class:`ValueError` if *source* is not recognised.
        """
        source = source.lower()
        command = INPUT_COMMANDS.get(source)
        if command is None:
            raise ValueError(
                f"Unknown input source: {source!r}. "
                f"Expected one of: {', '.join(INPUT_COMMANDS)}"
            )
        await self._connection.send_command(command)

    # -- Pairing ------------------------------------------------------------

    async def enter_pairing_mode(self) -> None:
        """Put the speaker into Bluetooth pairing mode (discoverable)."""
        await self._connection.send_command(Command.BT_PAIR)
        logger.info("Pairing mode activated – speaker is now discoverable")

    async def pair_device_and_switch(self, timeout: float = 120.0) -> None:
        """Enter pairing mode and then switch to Bluetooth input.

        Convenience method for the common workflow of pairing a new
        Bluetooth audio device (phone, tablet, laptop, etc.).

        Parameters
        ----------
        timeout:
            How long (in seconds) to wait in pairing mode before
            switching to Bluetooth input. Default is 120 seconds.
        """
        await self.enter_pairing_mode()
        logger.info("Pairing mode active for %.0f seconds...", timeout)
        await asyncio.sleep(timeout)
        await self.switch_input("bluetooth")
        logger.info("Switched to Bluetooth input after pairing mode")

    # -- System -------------------------------------------------------------

    async def factory_reset(self) -> None:
        """Send the factory-reset command to the speaker."""
        await self._connection.send_command(Command.FACTORY_RESET)
        logger.warning("Factory reset command sent")

    # -- Scanning (delegate) ------------------------------------------------

    async def scan(self, timeout: float = 10.0):
        """Scan for Z407 speakers. Returns a BLEDevice or None."""
        return await self._connection.scan(timeout=timeout)

    # -- Internal -----------------------------------------------------------

    def _handle_response(self, data: bytearray) -> None:
        """Process speaker responses for source-switch tracking."""
        raw = bytes(data)

        # Track source switch confirmations
        source = SOURCE_RESPONSE_MAP.get(raw)
        if source is not None:
            self._active_input = source
            logger.info("Active input changed to: %s", source)
            if self._on_input_change:
                try:
                    self._on_input_change(source)
                except Exception:
                    logger.exception("Error in input-change callback")

    def _forward_state_change(self, state: ConnectionState) -> None:
        if self._on_state_change:
            try:
                self._on_state_change(state)
            except Exception:
                logger.exception("Error in state-change callback")

    def _notify_volume(self) -> None:
        if self._on_volume_change:
            try:
                self._on_volume_change(self._volume_estimate)
            except Exception:
                logger.exception("Error in volume-change callback")
