"""Tests for z407.controller module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from z407.connection import ConnectionState
from z407.controller import Z407Controller, VOLUME_DEFAULT, VOLUME_STEP
from z407.protocol import Command, Response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_controller(**kwargs) -> Z407Controller:
    """Create a controller with a mocked connection."""
    ctrl = Z407Controller(**kwargs)
    ctrl._connection = MagicMock()
    ctrl._connection.send_command = AsyncMock()
    ctrl._connection.is_connected = True
    ctrl._connection.state = ConnectionState.CONNECTED
    return ctrl


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestZ407ControllerVolume:
    @pytest.mark.asyncio
    async def test_volume_up_single(self):
        ctrl = _make_controller()
        await ctrl.volume_up()
        ctrl._connection.send_command.assert_awaited_once_with(Command.VOLUME_UP)
        assert ctrl.volume == VOLUME_DEFAULT + VOLUME_STEP

    @pytest.mark.asyncio
    async def test_volume_down_single(self):
        ctrl = _make_controller()
        await ctrl.volume_down()
        ctrl._connection.send_command.assert_awaited_once_with(Command.VOLUME_DOWN)
        assert ctrl.volume == VOLUME_DEFAULT - VOLUME_STEP

    @pytest.mark.asyncio
    async def test_volume_up_multiple_steps(self):
        ctrl = _make_controller()
        await ctrl.volume_up(steps=3)
        assert ctrl._connection.send_command.await_count == 3
        assert ctrl.volume == VOLUME_DEFAULT + 3 * VOLUME_STEP

    @pytest.mark.asyncio
    async def test_volume_clamped_at_max(self):
        ctrl = _make_controller()
        ctrl._volume_estimate = 100
        await ctrl.volume_up()
        assert ctrl.volume == 100

    @pytest.mark.asyncio
    async def test_volume_clamped_at_min(self):
        ctrl = _make_controller()
        ctrl._volume_estimate = 0
        await ctrl.volume_down()
        assert ctrl.volume == 0

    def test_set_volume_estimate(self):
        ctrl = _make_controller()
        ctrl.set_volume_estimate(75)
        assert ctrl.volume == 75

    def test_set_volume_estimate_clamped(self):
        ctrl = _make_controller()
        ctrl.set_volume_estimate(150)
        assert ctrl.volume == 100
        ctrl.set_volume_estimate(-10)
        assert ctrl.volume == 0

    @pytest.mark.asyncio
    async def test_volume_change_callback(self):
        volumes = []
        ctrl = _make_controller(on_volume_change=volumes.append)
        await ctrl.volume_up()
        assert volumes == [VOLUME_DEFAULT + VOLUME_STEP]


class TestZ407ControllerBass:
    @pytest.mark.asyncio
    async def test_bass_up(self):
        ctrl = _make_controller()
        await ctrl.bass_up()
        ctrl._connection.send_command.assert_awaited_once_with(Command.BASS_UP)

    @pytest.mark.asyncio
    async def test_bass_down(self):
        ctrl = _make_controller()
        await ctrl.bass_down()
        ctrl._connection.send_command.assert_awaited_once_with(Command.BASS_DOWN)

    @pytest.mark.asyncio
    async def test_bass_up_multiple(self):
        ctrl = _make_controller()
        await ctrl.bass_up(steps=4)
        assert ctrl._connection.send_command.await_count == 4


class TestZ407ControllerPlayback:
    @pytest.mark.asyncio
    async def test_play_pause(self):
        ctrl = _make_controller()
        await ctrl.play_pause()
        ctrl._connection.send_command.assert_awaited_once_with(Command.PLAY_PAUSE)

    @pytest.mark.asyncio
    async def test_next_track(self):
        ctrl = _make_controller()
        await ctrl.next_track()
        ctrl._connection.send_command.assert_awaited_once_with(Command.NEXT_TRACK)

    @pytest.mark.asyncio
    async def test_prev_track(self):
        ctrl = _make_controller()
        await ctrl.prev_track()
        ctrl._connection.send_command.assert_awaited_once_with(Command.PREV_TRACK)


class TestZ407ControllerInput:
    @pytest.mark.asyncio
    async def test_switch_bluetooth(self):
        ctrl = _make_controller()
        await ctrl.switch_input("bluetooth")
        ctrl._connection.send_command.assert_awaited_once_with(Command.INPUT_BLUETOOTH)

    @pytest.mark.asyncio
    async def test_switch_aux(self):
        ctrl = _make_controller()
        await ctrl.switch_input("aux")
        ctrl._connection.send_command.assert_awaited_once_with(Command.INPUT_AUX)

    @pytest.mark.asyncio
    async def test_switch_usb(self):
        ctrl = _make_controller()
        await ctrl.switch_input("usb")
        ctrl._connection.send_command.assert_awaited_once_with(Command.INPUT_USB)

    @pytest.mark.asyncio
    async def test_switch_case_insensitive(self):
        ctrl = _make_controller()
        await ctrl.switch_input("BLUETOOTH")
        ctrl._connection.send_command.assert_awaited_once_with(Command.INPUT_BLUETOOTH)

    @pytest.mark.asyncio
    async def test_switch_invalid_raises(self):
        ctrl = _make_controller()
        with pytest.raises(ValueError, match="Unknown input source"):
            await ctrl.switch_input("hdmi")


class TestZ407ControllerPairing:
    @pytest.mark.asyncio
    async def test_enter_pairing_mode(self):
        ctrl = _make_controller()
        await ctrl.enter_pairing_mode()
        ctrl._connection.send_command.assert_awaited_once_with(Command.BT_PAIR)

    @pytest.mark.asyncio
    async def test_pair_device_and_switch(self):
        ctrl = _make_controller()
        await ctrl.pair_device_and_switch()
        calls = ctrl._connection.send_command.await_args_list
        # Should send BT_PAIR first, then INPUT_BLUETOOTH
        assert calls[0].args[0] == Command.BT_PAIR
        assert calls[1].args[0] == Command.INPUT_BLUETOOTH


class TestZ407ControllerFactoryReset:
    @pytest.mark.asyncio
    async def test_factory_reset(self):
        ctrl = _make_controller()
        await ctrl.factory_reset()
        ctrl._connection.send_command.assert_awaited_once_with(Command.FACTORY_RESET)


class TestZ407ControllerResponseHandling:
    def test_source_switch_updates_active_input(self):
        inputs = []
        ctrl = _make_controller(on_input_change=inputs.append)
        # Simulate speaker source-switch response
        ctrl._handle_response(bytearray(Response.SOURCE_BLUETOOTH))
        assert ctrl.active_input == "bluetooth"
        assert inputs == ["bluetooth"]

    def test_source_switch_aux(self):
        ctrl = _make_controller()
        ctrl._handle_response(bytearray(Response.SOURCE_AUX))
        assert ctrl.active_input == "aux"

    def test_source_switch_usb(self):
        ctrl = _make_controller()
        ctrl._handle_response(bytearray(Response.SOURCE_USB))
        assert ctrl.active_input == "usb"

    def test_unknown_response_does_not_change_input(self):
        ctrl = _make_controller()
        ctrl._handle_response(bytearray(b"\xc0\x02"))
        assert ctrl.active_input is None
