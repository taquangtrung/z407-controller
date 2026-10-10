"""BLE connection manager for the Logitech Z407 speaker.

Handles scanning, connecting, the mandatory 5-step handshake, keepalive
responses, and automatic reconnection with exponential backoff.
"""

from __future__ import annotations

import asyncio
import logging
import platform
import subprocess
from collections.abc import Callable
from enum import Enum

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

from z407.protocol import (
    COMMAND_UUID,
    RESPONSE_UUID,
    SERVICE_UUID,
    Command,
    Response,
    is_keepalive,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection states
# ---------------------------------------------------------------------------

class ConnectionState(Enum):
    """Possible states of the BLE connection."""

    DISCONNECTED = "disconnected"
    SCANNING = "scanning"
    CONNECTING = "connecting"
    HANDSHAKING = "handshaking"
    CONNECTED = "connected"


# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------

class Z407Connection:
    """Low-level BLE connection to a Logitech Z407 speaker.

    Parameters
    ----------
    on_response:
        Optional callback invoked for every notification received on the
        response characteristic.  Called with the raw ``bytearray`` data.
    on_state_change:
        Optional callback invoked whenever the :pyattr:`state` changes.
    """

    def __init__(
        self,
        on_response: Callable[[bytearray], None] | None = None,
        on_state_change: Callable[[ConnectionState], None] | None = None,
    ) -> None:
        self._client: BleakClient | None = None
        self._state: ConnectionState = ConnectionState.DISCONNECTED
        self._on_response = on_response
        self._on_state_change = on_state_change

        # Handshake synchronisation
        self._handshake_event: asyncio.Event = asyncio.Event()
        self._handshake_ack_received: bool = False

        # Reconnection bookkeeping
        self._consecutive_failures: int = 0
        self._maintain_task: asyncio.Task[None] | None = None
        self._should_run: bool = False

        # Stored device address for reconnection
        self._address: str | None = None

    # -- Properties ---------------------------------------------------------

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED

    # -- State management ---------------------------------------------------

    def _set_state(self, new_state: ConnectionState) -> None:
        if new_state != self._state:
            logger.info("Connection state: %s -> %s", self._state.value, new_state.value)
            self._state = new_state
            if self._on_state_change:
                try:
                    self._on_state_change(new_state)
                except Exception:
                    logger.exception("Error in state-change callback")

    # -- Scanning -----------------------------------------------------------

    async def scan(self, timeout: float = 10.0) -> BLEDevice | None:
        """Scan for a Z407 speaker advertising the expected service UUID.

        Returns the first matching :class:`BLEDevice`, or ``None`` if no
        device was found within *timeout* seconds.
        """
        self._set_state(ConnectionState.SCANNING)
        logger.info("Scanning for Z407 speaker (timeout=%.1fs)…", timeout)

        try:
            devices = await BleakScanner.discover(
                timeout=timeout,
                service_uuids=[SERVICE_UUID],
            )
        except Exception:
            logger.exception("BLE scan failed")
            self._set_state(ConnectionState.DISCONNECTED)
            return None

        for device in devices:
            logger.info("Found Z407: %s (%s)", device.name, device.address)
            return device

        # A speaker that BlueZ already holds a link to stops advertising, so
        # the scan above cannot see it; look it up among the connected devices.
        device = await self._find_bluez_connected_device()
        if device:
            logger.info("Found already-connected Z407: %s (%s)", device.name, device.address)
            return device

        logger.warning("No Z407 speaker found")
        self._set_state(ConnectionState.DISCONNECTED)
        return None

    @staticmethod
    async def _find_bluez_connected_device() -> BLEDevice | None:
        """Return a BlueZ device that is already connected and exposes the Z407 service.

        Linux only; relies on bleak's BlueZ manager cache. Returns ``None`` on
        other platforms or if the cache cannot be read.
        """
        if platform.system() != "Linux":
            return None
        try:
            from bleak.backends.bluezdbus.manager import get_global_bluez_manager

            manager = await get_global_bluez_manager()
            for path, interfaces in list(manager._properties.items()):
                props = interfaces.get("org.bluez.Device1")
                if (
                    props
                    and props.get("Connected")
                    and SERVICE_UUID in props.get("UUIDs", [])
                ):
                    return BLEDevice(props["Address"], props.get("Alias"), {"path": path})
        except Exception:
            logger.debug("Could not query BlueZ for connected devices", exc_info=True)
        return None

    # -- Connect / Handshake ------------------------------------------------

    async def connect(self, target: str | BLEDevice, timeout: float = 15.0) -> None:
        """Connect to the speaker and perform the handshake.

        *target* is a device address or a :class:`BLEDevice` from :meth:`scan`.
        Prefer the device object: a speaker BlueZ already holds a link to is not
        in bleak's scan cache, so it can only be resolved from the object.

        Raises :class:`TimeoutError` if the handshake does not complete
        within *timeout* seconds.
        """
        address = target if isinstance(target, str) else target.address
        self._address = address
        self._set_state(ConnectionState.CONNECTING)
        self._handshake_event.clear()
        self._handshake_ack_received = False

        self._client = BleakClient(
            target,
            disconnected_callback=self._on_disconnect,
        )
        await self._client.connect()
        logger.info("BLE connected to %s", address)

        # Subscribe to notifications BEFORE sending the handshake init so
        # we don't miss the response.
        await self._client.start_notify(RESPONSE_UUID, self._handle_notification)

        # -- Handshake step 1: send init ------------------------------------
        self._set_state(ConnectionState.HANDSHAKING)
        await self._client.write_gatt_char(
            COMMAND_UUID, Command.HANDSHAKE_INIT, response=False,
        )
        logger.info(">> Sent HANDSHAKE_INIT (8405)")

        # Wait for the handshake to complete (steps 2–5 happen in the
        # notification handler). Some firmware versions may not send
        # CONNECTED (d40003), so if we get ACK_REPLY, retry sending ACK.
        retry_interval = 2.0
        retry_count = 0
        max_retries = int(timeout / retry_interval)

        while retry_count < max_retries:
            try:
                await asyncio.wait_for(self._handshake_event.wait(), timeout=retry_interval)
                break  # Success - got CONNECTED
            except TimeoutError:
                # If we got ACK_REPLY but not CONNECTED, retry sending ACK
                if self._handshake_ack_received:
                    retry_count += 1
                    logger.warning(
                        "ACK_REPLY received but no CONNECTED - retry %d/%d",
                        retry_count, max_retries,
                    )
                    if self._client and self._client.is_connected:
                        await self._client.write_gatt_char(
                            COMMAND_UUID, Command.HANDSHAKE_ACK, response=False,
                        )
                        logger.info(">> Resent HANDSHAKE_ACK (8400)")
                else:
                    # Haven't received ACK_REPLY yet, give up
                    logger.error("Handshake timed out - no ACK_REPLY received")
                    await self.disconnect()
                    raise TimeoutError("Z407 handshake did not complete in time")

        if not self._handshake_event.is_set():
            # Retries exhausted - treat ACK_REPLY as sufficient if we got it
            if self._handshake_ack_received:
                logger.warning(
                    "CONNECTED never received, but ACK_REPLY confirmed - proceeding anyway"
                )
                self._handshake_event.set()
            else:
                logger.error("Handshake timed out")
                await self.disconnect()
                raise TimeoutError("Z407 handshake did not complete in time")

        self._set_state(ConnectionState.CONNECTED)
        self._consecutive_failures = 0
        logger.info("Handshake complete – connected to Z407")

    # -- Disconnect ---------------------------------------------------------

    async def disconnect(self) -> None:
        """Gracefully disconnect from the speaker."""
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
            except Exception:
                logger.debug("Error during disconnect (ignored)", exc_info=True)
        self._client = None
        self._set_state(ConnectionState.DISCONNECTED)

    def _on_disconnect(self, _client: BleakClient) -> None:
        """Called by bleak when the connection drops."""
        logger.warning("BLE connection lost")
        self._client = None
        self._set_state(ConnectionState.DISCONNECTED)

    # -- Command writing ----------------------------------------------------

    async def send_command(self, command: Command) -> None:
        """Write a 2-byte command to the speaker.

        Raises :class:`RuntimeError` if not connected.
        """
        if not self._client or not self._client.is_connected:
            raise RuntimeError("Not connected to Z407 speaker")
        await self._client.write_gatt_char(COMMAND_UUID, command, response=False)
        logger.debug("Sent command: %s (%s)", command.name, command.hex())

    # -- Notification handler -----------------------------------------------

    async def _handle_notification(self, _sender, data: bytearray) -> None:
        """Process notifications from the response characteristic.

        This callback is ``async`` so that the keepalive ACK can be
        ``await``-ed inline — exactly how both reference implementations
        (freundTech and androrama) handle it.  Bleak >= 0.20 natively
        supports async notification callbacks.
        """
        raw = bytes(data)
        logger.info("<< Notification: %s", raw.hex())

        # Keepalive / Handshake step 2: speaker sends d40501 → reply ACK
        if is_keepalive(raw):
            logger.info("Keepalive/handshake ping – sending ACK")
            if self._client and self._client.is_connected:
                try:
                    await self._client.write_gatt_char(
                        COMMAND_UUID, Command.HANDSHAKE_ACK, response=False,
                    )
                    logger.info(">> Sent HANDSHAKE_ACK (8400)")
                except Exception:
                    logger.exception("Failed to send keepalive ACK")

        # Handshake step 4: d40001 – acknowledge response
        if raw == Response.ACK_REPLY:
            logger.info("Handshake step 4: ACK_REPLY received")
            self._handshake_ack_received = True

        # Handshake step 5: d40003 – connection established
        if raw == Response.CONNECTED:
            logger.info("Handshake step 5: CONNECTED received")
            self._handshake_event.set()

        # Forward to external callback
        if self._on_response:
            try:
                self._on_response(data)
            except Exception:
                logger.exception("Error in response callback")

    # -- Connection maintenance loop ----------------------------------------

    async def maintain(self) -> None:
        """Background loop that keeps the connection alive.

        Continuously scans, connects, and reconnects on failure with
        exponential backoff.  After 5 consecutive failures on Linux it
        resets the Bluetooth adapter via ``rfkill``.
        """
        self._should_run = True
        backoff = 1.0  # seconds
        max_backoff = 60.0

        while self._should_run:
            if self.is_connected:
                # Sleep and re-check. The keepalive handler runs via
                # bleak's notification loop, so we just idle here.
                await asyncio.sleep(1.0)
                continue

            # --- Attempt scan + connect ------------------------------------
            try:
                device = await self.scan(timeout=10.0)
                if device:
                    await self.connect(device)
                    backoff = 1.0  # reset on success
                    continue
            except Exception:
                logger.exception("Connection attempt failed")

            self._consecutive_failures += 1
            logger.info(
                "Consecutive failures: %d (backoff=%.1fs)",
                self._consecutive_failures,
                backoff,
            )

            # Reset Bluetooth adapter after repeated failures (Linux only)
            if self._consecutive_failures >= 5 and platform.system() == "Linux":
                self._reset_bluetooth_adapter()
                self._consecutive_failures = 0

            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)

    async def stop(self) -> None:
        """Signal the maintenance loop to stop and disconnect."""
        self._should_run = False
        await self.disconnect()

    # -- Adapter reset (Linux) ----------------------------------------------

    @staticmethod
    def _reset_bluetooth_adapter() -> None:
        """Attempt to reset the Bluetooth adapter using rfkill."""
        logger.warning("Resetting Bluetooth adapter via rfkill …")
        try:
            subprocess.run(["rfkill", "block", "bluetooth"], check=True, timeout=5)
            import time
            time.sleep(1)
            subprocess.run(["rfkill", "unblock", "bluetooth"], check=True, timeout=5)
            logger.info("Bluetooth adapter reset complete")
        except FileNotFoundError:
            logger.warning("rfkill not found – cannot reset adapter")
        except subprocess.SubprocessError:
            logger.warning("rfkill command failed", exc_info=True)
