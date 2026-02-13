"""Tests for z407.connection module using mocked bleak."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from z407.connection import ConnectionState, Z407Connection
from z407.protocol import COMMAND_UUID, RESPONSE_UUID, Command, Response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_client(connected: bool = True):
    """Create a mock BleakClient."""
    client = AsyncMock()
    client.is_connected = connected
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.start_notify = AsyncMock()
    client.write_gatt_char = AsyncMock()
    return client


def _make_mock_device(name="Logitech Z407", address="AA:BB:CC:DD:EE:FF"):
    device = MagicMock()
    device.name = name
    device.address = address
    return device


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestZ407ConnectionState:
    def test_initial_state_is_disconnected(self):
        conn = Z407Connection()
        assert conn.state == ConnectionState.DISCONNECTED
        assert not conn.is_connected


class TestZ407ConnectionScan:
    @pytest.mark.asyncio
    async def test_scan_finds_device(self):
        mock_device = _make_mock_device()
        with patch("z407.connection.BleakScanner") as MockScanner:
            MockScanner.discover = AsyncMock(return_value=[mock_device])
            conn = Z407Connection()
            device = await conn.scan(timeout=5.0)
            assert device is mock_device

    @pytest.mark.asyncio
    async def test_scan_no_device(self):
        with patch("z407.connection.BleakScanner") as MockScanner:
            MockScanner.discover = AsyncMock(return_value=[])
            conn = Z407Connection()
            device = await conn.scan(timeout=1.0)
            assert device is None
            assert conn.state == ConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_scan_updates_state(self):
        states = []
        with patch("z407.connection.BleakScanner") as MockScanner:
            MockScanner.discover = AsyncMock(return_value=[])
            conn = Z407Connection(on_state_change=states.append)
            await conn.scan(timeout=1.0)
            assert ConnectionState.SCANNING in states


class TestZ407ConnectionConnect:
    @pytest.mark.asyncio
    async def test_connect_performs_handshake(self):
        mock_client = _make_mock_client()

        # Simulate the handshake: when start_notify is called, capture the
        # notification callback and immediately simulate the full handshake.
        notification_callback = None

        async def fake_start_notify(uuid, callback):
            nonlocal notification_callback
            notification_callback = callback

        mock_client.start_notify = fake_start_notify

        async def fake_write(uuid, data, response=False):
            # When HANDSHAKE_INIT is sent, simulate speaker responses
            if data == Command.HANDSHAKE_INIT and notification_callback:
                notification_callback(0, bytearray(Response.HANDSHAKE_REPLY))
                notification_callback(0, bytearray(Response.ACK_REPLY))
                notification_callback(0, bytearray(Response.CONNECTED))

        mock_client.write_gatt_char = fake_write

        with patch("z407.connection.BleakClient", return_value=mock_client):
            conn = Z407Connection()
            await conn.connect("AA:BB:CC:DD:EE:FF")
            assert conn.state == ConnectionState.CONNECTED
            assert conn.is_connected

    @pytest.mark.asyncio
    async def test_connect_timeout(self):
        mock_client = _make_mock_client()

        # Don't simulate any handshake responses -> should timeout
        async def fake_start_notify(uuid, callback):
            pass

        mock_client.start_notify = fake_start_notify

        with patch("z407.connection.BleakClient", return_value=mock_client):
            conn = Z407Connection()
            with pytest.raises(TimeoutError):
                await conn.connect("AA:BB:CC:DD:EE:FF", timeout=0.5)


class TestZ407ConnectionSendCommand:
    @pytest.mark.asyncio
    async def test_send_command_when_connected(self):
        mock_client = _make_mock_client()
        conn = Z407Connection()
        conn._client = mock_client
        conn._state = ConnectionState.CONNECTED

        await conn.send_command(Command.VOLUME_UP)
        mock_client.write_gatt_char.assert_awaited_once_with(
            COMMAND_UUID, Command.VOLUME_UP, response=False,
        )

    @pytest.mark.asyncio
    async def test_send_command_when_disconnected_raises(self):
        conn = Z407Connection()
        with pytest.raises(RuntimeError, match="Not connected"):
            await conn.send_command(Command.VOLUME_UP)


class TestZ407ConnectionKeepalive:
    @pytest.mark.asyncio
    async def test_keepalive_sends_ack(self):
        """Verify the notification handler auto-replies to keepalive pings."""
        mock_client = _make_mock_client()
        conn = Z407Connection()
        conn._client = mock_client

        # Simulate a keepalive notification (handler is async)
        await conn._handle_notification(0, bytearray(Response.HANDSHAKE_REPLY))

        # The handler should have awaited an ACK write
        mock_client.write_gatt_char.assert_awaited_once_with(
            COMMAND_UUID, Command.HANDSHAKE_ACK, response=False,
        )


class TestZ407ConnectionDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect(self):
        mock_client = _make_mock_client()
        conn = Z407Connection()
        conn._client = mock_client
        conn._state = ConnectionState.CONNECTED

        await conn.disconnect()
        mock_client.disconnect.assert_awaited_once()
        assert conn.state == ConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_disconnect_when_already_disconnected(self):
        conn = Z407Connection()
        await conn.disconnect()  # Should not raise
        assert conn.state == ConnectionState.DISCONNECTED
