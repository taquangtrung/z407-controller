"""Tests for z407.protocol module."""

from z407.protocol import Command, Response, is_confirmation, is_keepalive


class TestCommand:
    """Verify Command enum values match the protocol specification."""

    def test_volume_up_bytes(self):
        assert Command.VOLUME_UP == bytes.fromhex("8002")

    def test_volume_down_bytes(self):
        assert Command.VOLUME_DOWN == bytes.fromhex("8003")

    def test_bass_up_bytes(self):
        assert Command.BASS_UP == bytes.fromhex("8000")

    def test_bass_down_bytes(self):
        assert Command.BASS_DOWN == bytes.fromhex("8001")

    def test_play_pause_bytes(self):
        assert Command.PLAY_PAUSE == bytes.fromhex("8004")

    def test_next_track_bytes(self):
        assert Command.NEXT_TRACK == bytes.fromhex("8005")

    def test_prev_track_bytes(self):
        assert Command.PREV_TRACK == bytes.fromhex("8006")

    def test_input_bluetooth(self):
        assert Command.INPUT_BLUETOOTH == bytes.fromhex("8101")

    def test_input_aux(self):
        assert Command.INPUT_AUX == bytes.fromhex("8102")

    def test_input_usb(self):
        assert Command.INPUT_USB == bytes.fromhex("8103")

    def test_bt_pair(self):
        assert Command.BT_PAIR == bytes.fromhex("8200")

    def test_factory_reset(self):
        assert Command.FACTORY_RESET == bytes.fromhex("8300")

    def test_handshake_ack(self):
        assert Command.HANDSHAKE_ACK == bytes.fromhex("8400")

    def test_handshake_init(self):
        assert Command.HANDSHAKE_INIT == bytes.fromhex("8405")

    def test_all_commands_are_two_bytes(self):
        for cmd in Command:
            assert len(cmd) == 2, f"{cmd.name} is not 2 bytes"


class TestResponse:
    """Verify Response constants."""

    def test_handshake_reply(self):
        assert Response.HANDSHAKE_REPLY == bytes.fromhex("d40501")

    def test_ack_reply(self):
        assert Response.ACK_REPLY == bytes.fromhex("d40001")

    def test_connected(self):
        assert Response.CONNECTED == bytes.fromhex("d40003")

    def test_source_bluetooth(self):
        assert Response.SOURCE_BLUETOOTH == bytes.fromhex("cf04")

    def test_source_aux(self):
        assert Response.SOURCE_AUX == bytes.fromhex("cf05")

    def test_source_usb(self):
        assert Response.SOURCE_USB == bytes.fromhex("cf06")


class TestIsConfirmation:
    """Verify the is_confirmation() helper."""

    def test_volume_up_confirmation(self):
        # 0x8002 -> confirmed by 0xc002
        assert is_confirmation(bytes.fromhex("c002"), Command.VOLUME_UP)

    def test_volume_down_confirmation(self):
        assert is_confirmation(bytes.fromhex("c003"), Command.VOLUME_DOWN)

    def test_bass_up_confirmation(self):
        assert is_confirmation(bytes.fromhex("c000"), Command.BASS_UP)

    def test_play_pause_confirmation(self):
        assert is_confirmation(bytes.fromhex("c004"), Command.PLAY_PAUSE)

    def test_input_bluetooth_confirmation(self):
        # 0x8101 -> confirmed by 0xc101
        assert is_confirmation(bytes.fromhex("c101"), Command.INPUT_BLUETOOTH)

    def test_bt_pair_confirmation(self):
        # 0x8200 -> confirmed by 0xc200
        assert is_confirmation(bytes.fromhex("c200"), Command.BT_PAIR)

    def test_factory_reset_confirmation(self):
        assert is_confirmation(bytes.fromhex("c300"), Command.FACTORY_RESET)

    def test_wrong_confirmation_returns_false(self):
        assert not is_confirmation(bytes.fromhex("c003"), Command.VOLUME_UP)

    def test_empty_response_returns_false(self):
        assert not is_confirmation(b"", Command.VOLUME_UP)

    def test_short_response_returns_false(self):
        assert not is_confirmation(b"\xc0", Command.VOLUME_UP)


class TestIsKeepalive:
    """Verify the is_keepalive() helper."""

    def test_keepalive_true(self):
        assert is_keepalive(bytes.fromhex("d40501"))

    def test_keepalive_bytearray(self):
        assert is_keepalive(bytearray.fromhex("d40501"))

    def test_not_keepalive(self):
        assert not is_keepalive(bytes.fromhex("d40001"))

    def test_empty(self):
        assert not is_keepalive(b"")
