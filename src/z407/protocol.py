"""BLE protocol constants and command definitions for Logitech Z407."""

from __future__ import annotations

from enum import Enum

# ---------------------------------------------------------------------------
# BLE GATT identifiers
# ---------------------------------------------------------------------------

SERVICE_UUID: str = "0000fdc2-0000-1000-8000-00805f9b34fb"
"""Custom BLE service advertised by the Z407 speaker."""

COMMAND_UUID: str = "c2e758b9-0e78-41e0-b0cb-98a593193fc5"
"""Characteristic for writing commands (Client -> Speaker)."""

RESPONSE_UUID: str = "b84ac9c6-29c5-46d4-bba1-9d534784330f"
"""Characteristic for receiving notifications (Speaker -> Client)."""


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

class Command(bytes, Enum):
    """Two-byte commands sent to the Z407 speaker."""

    # Audio control (0x80xx)
    BASS_UP = bytes.fromhex("8000")
    BASS_DOWN = bytes.fromhex("8001")
    VOLUME_UP = bytes.fromhex("8002")
    VOLUME_DOWN = bytes.fromhex("8003")
    PLAY_PAUSE = bytes.fromhex("8004")
    NEXT_TRACK = bytes.fromhex("8005")
    PREV_TRACK = bytes.fromhex("8006")

    # Input switching (0x81xx)
    INPUT_BLUETOOTH = bytes.fromhex("8101")
    INPUT_AUX = bytes.fromhex("8102")
    INPUT_USB = bytes.fromhex("8103")

    # System (0x82xx–0x85xx)
    BT_PAIR = bytes.fromhex("8200")
    FACTORY_RESET = bytes.fromhex("8300")
    HANDSHAKE_ACK = bytes.fromhex("8400")
    HANDSHAKE_INIT = bytes.fromhex("8405")

    # Auditory cues (0x85xx)
    SOUND_1 = bytes.fromhex("8501")
    SOUND_2 = bytes.fromhex("8502")
    SOUND_3 = bytes.fromhex("8503")


# ---------------------------------------------------------------------------
# Input source name ↔ command mapping
# ---------------------------------------------------------------------------

INPUT_COMMANDS: dict[str, Command] = {
    "bluetooth": Command.INPUT_BLUETOOTH,
    "aux": Command.INPUT_AUX,
    "usb": Command.INPUT_USB,
}

# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class Response:
    """Known byte sequences sent by the speaker on the response characteristic."""

    # Handshake
    HANDSHAKE_REPLY = bytes.fromhex("d40501")
    ACK_REPLY = bytes.fromhex("d40001")
    CONNECTED = bytes.fromhex("d40003")

    # Source switch confirmations
    SOURCE_BLUETOOTH = bytes.fromhex("cf04")
    SOURCE_AUX = bytes.fromhex("cf05")
    SOURCE_USB = bytes.fromhex("cf06")


# Reverse map: response bytes -> source name
SOURCE_RESPONSE_MAP: dict[bytes, str] = {
    Response.SOURCE_BLUETOOTH: "bluetooth",
    Response.SOURCE_AUX: "aux",
    Response.SOURCE_USB: "usb",
}


def is_confirmation(response: bytes, command: Command) -> bool:
    """Check whether *response* is the confirmation for *command*.

    The speaker confirms commands by mirroring the command bytes with the
    first nibble changed from ``0x8`` to ``0xc``.  For example, command
    ``0x8002`` (volume up) is confirmed by ``0xc002``.
    """
    if len(response) < 2 or len(command) < 2:
        return False
    # Build expected confirmation: first nibble 0x8 -> 0xc
    expected_first = (command[0] & 0x0F) | 0xC0
    return response[0] == expected_first and response[1] == command[1]


def is_keepalive(response: bytes) -> bool:
    """Return ``True`` if *response* is a keepalive ping from the speaker."""
    return bytes(response) == Response.HANDSHAKE_REPLY
