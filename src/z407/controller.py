"""High-level controller for the Logitech Z407 speaker.

Wraps :class:`Z407Connection` to provide a user-friendly API for volume,
bass, playback, input switching, and pairing.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from z407.connection import ConnectionState, Z407Connection
from z407.protocol import (
    INPUT_COMMANDS,
    SOURCE_RESPONSE_MAP,
    Command,
)

logger = logging.getLogger(__name__)

# Short delay between multi-step commands (seconds)
COMMAND_DELAY = 0.05


class Z407Controller:
    """High-level controller for the Z407 speaker.

    Parameters
    ----------
    on_state_change:
        Optional callback invoked on connection-state changes.  The
        callback receives a :class:`ConnectionState` value.
    on_input_change:
        Optional callback invoked when the active input source changes.
    """

    def __init__(
        self,
        on_state_change: Callable[[ConnectionState], None] | None = None,
        on_input_change: Callable[[str], None] | None = None,
    ) -> None:
        self._on_state_change = on_state_change
        self._on_input_change = on_input_change

        self._connection = Z407Connection(
            on_response=self._handle_response,
            on_state_change=self._forward_state_change,
        )

        self._active_input: str | None = None
        self._maintain_task: asyncio.Future[None] | None = None

    # -- Properties ---------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._connection.is_connected

    @property
    def state(self) -> ConnectionState:
        return self._connection.state

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
        await self.disconnect()
        await self._connection.stop()

    def connect(self) -> None:
        """Start connecting to the speaker in the background (no-op if already running)."""
        if self._maintain_task is None or self._maintain_task.done():
            self._maintain_task = asyncio.ensure_future(self._connection.maintain())

    async def disconnect(self) -> None:
        """Cancel any connection attempt and disconnect from the speaker."""
        task, self._maintain_task = self._maintain_task, None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await self._connection.stop()

    # -- Volume -------------------------------------------------------------

    async def volume_up(self, steps: int = 1) -> None:
        """Increase volume by *steps* increments."""
        await self._repeat(Command.VOLUME_UP, steps)

    async def volume_down(self, steps: int = 1) -> None:
        """Decrease volume by *steps* increments."""
        await self._repeat(Command.VOLUME_DOWN, steps)

    # -- Bass ---------------------------------------------------------------

    async def bass_up(self, steps: int = 1) -> None:
        await self._repeat(Command.BASS_UP, steps)

    async def bass_down(self, steps: int = 1) -> None:
        await self._repeat(Command.BASS_DOWN, steps)

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

    async def _repeat(self, command: Command, steps: int) -> None:
        """Send *command* *steps* times with a short delay between sends."""
        for _ in range(steps):
            await self._connection.send_command(command)
            if steps > 1:
                await asyncio.sleep(COMMAND_DELAY)

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
