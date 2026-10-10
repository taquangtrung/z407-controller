"""Command-line interface for the Z407 controller.

Usage examples::

    z407-cli scan
    z407-cli volume up --steps 3
    z407-cli input bluetooth
    z407-cli pair
    z407-cli daemon
    z407-gui
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from z407.controller import Z407Controller


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="z407-cli",
        description="Control Logitech Z407 speakers over BLE.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging."
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress all output except errors."
    )

    sub = parser.add_subparsers(dest="command")

    # scan
    sub.add_parser("scan", help="Scan for Z407 speaker.")

    # status
    sub.add_parser("status", help="Show connection status.")

    # volume
    vol = sub.add_parser("volume", help="Adjust volume.")
    vol.add_argument("direction", choices=["up", "down"])
    vol.add_argument("--steps", type=int, default=1, help="Number of steps (default: 1).")

    # bass
    bass = sub.add_parser("bass", help="Adjust bass.")
    bass.add_argument("direction", choices=["up", "down"])
    bass.add_argument("--steps", type=int, default=1, help="Number of steps (default: 1).")

    # play
    sub.add_parser("play", help="Toggle Play/Pause.")

    # next / prev
    sub.add_parser("next", help="Next track.")
    sub.add_parser("prev", help="Previous track.")

    # input
    inp = sub.add_parser("input", help="Switch input source.")
    inp.add_argument("source", choices=["bluetooth", "aux", "usb"])

    # pair
    pair_parser = sub.add_parser("pair", help="Enter BT pairing mode and switch to Bluetooth input.")
    pair_parser.add_argument(
        "--timeout", type=float, default=120.0,
        help="How long to stay in pairing mode (seconds, default: 120).",
    )

    # reset
    sub.add_parser("reset", help="Factory reset the speaker (requires confirmation).")

    # daemon
    daemon_parser = sub.add_parser(
        "daemon",
        help="Run as background daemon with web API (persistent BLE connection).",
    )
    daemon_parser.add_argument(
        "--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0).",
    )
    daemon_parser.add_argument(
        "--port", type=int, default=5000, help="Port (default: 5000).",
    )
    daemon_parser.add_argument(
        "--no-browser", action="store_true",
        help="Don't auto-open the browser.",
    )

    # gui
    gui_parser = sub.add_parser("gui", help="Launch the control panel (native GUI by default).")
    gui_parser.add_argument(
        "--web", action="store_true",
        help="Launch the web-based GUI instead of the native desktop GUI.",
    )
    gui_parser.add_argument(
        "--host", default="0.0.0.0", help="Bind address for web GUI (default: 0.0.0.0).",
    )
    gui_parser.add_argument(
        "--port", type=int, default=5000, help="Port for web GUI (default: 5000).",
    )
    gui_parser.add_argument(
        "--no-browser", action="store_true",
        help="Don't auto-open the browser (web GUI only).",
    )

    return parser


def _setup_logging(verbose: bool, quiet: bool) -> None:
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


async def _cmd_scan(_args: argparse.Namespace) -> int:
    ctrl = Z407Controller()
    device = await ctrl.scan(timeout=10.0)
    if device:
        print(f"Found Z407: {device.name} ({device.address})")
        return 0
    print("No Z407 speaker found.")
    return 1


async def _cmd_status(_args: argparse.Namespace) -> int:
    ctrl = Z407Controller()
    device = await ctrl.scan(timeout=5.0)
    if device:
        print(f"Speaker found: {device.name} ({device.address})")
        print("Attempting connection…")
        try:
            await ctrl._connection.connect(device)
            print(f"Status: {ctrl.state.value}")
            await ctrl._connection.disconnect()
            return 0
        except Exception as exc:  # noqa: BLE001
            print(f"Connection failed: {exc}")
            return 1
    print("No Z407 speaker found.")
    return 1


async def _connect_and_run(action) -> int:
    """Helper: scan, connect, run *action*, disconnect."""
    ctrl = Z407Controller()
    device = await ctrl.scan(timeout=10.0)
    if not device:
        print("No Z407 speaker found.", file=sys.stderr)
        return 1
    try:
        await ctrl._connection.connect(device)
    except Exception as exc:  # noqa: BLE001
        print(f"Connection failed: {exc}", file=sys.stderr)
        return 1
    try:
        await action(ctrl)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Command failed: {exc}", file=sys.stderr)
        return 2
    finally:
        await ctrl._connection.disconnect()


async def _cmd_volume(args: argparse.Namespace) -> int:
    async def action(ctrl: Z407Controller):
        if args.direction == "up":
            await ctrl.volume_up(steps=args.steps)
            print(f"Volume up {args.steps} step(s).")
        else:
            await ctrl.volume_down(steps=args.steps)
            print(f"Volume down {args.steps} step(s).")

    return await _connect_and_run(action)


async def _cmd_bass(args: argparse.Namespace) -> int:
    async def action(ctrl: Z407Controller):
        if args.direction == "up":
            await ctrl.bass_up(steps=args.steps)
            print(f"Bass up {args.steps} step(s).")
        else:
            await ctrl.bass_down(steps=args.steps)
            print(f"Bass down {args.steps} step(s).")

    return await _connect_and_run(action)


async def _cmd_play(_args: argparse.Namespace) -> int:
    return await _connect_and_run(lambda ctrl: ctrl.play_pause())


async def _cmd_next(_args: argparse.Namespace) -> int:
    return await _connect_and_run(lambda ctrl: ctrl.next_track())


async def _cmd_prev(_args: argparse.Namespace) -> int:
    return await _connect_and_run(lambda ctrl: ctrl.prev_track())


async def _cmd_input(args: argparse.Namespace) -> int:
    async def action(ctrl: Z407Controller):
        await ctrl.switch_input(args.source)
        print(f"Switched input to: {args.source}")

    return await _connect_and_run(action)


async def _cmd_pair(args: argparse.Namespace) -> int:
    async def action(ctrl: Z407Controller):
        timeout = getattr(args, "timeout", 120.0)
        print(
            f"Pairing mode activated for {timeout:.0f} seconds.\n"
            "Open Bluetooth settings on your device and select 'Logitech Z407'."
        )
        await ctrl.pair_device_and_switch(timeout=timeout)

    return await _connect_and_run(action)


async def _cmd_reset(_args: argparse.Namespace) -> int:
    answer = input("Are you sure you want to factory reset the speaker? [y/N] ")
    if answer.strip().lower() != "y":
        print("Aborted.")
        return 0

    async def action(ctrl: Z407Controller):
        await ctrl.factory_reset()
        print("Factory reset command sent.")

    return await _connect_and_run(action)


def _cmd_daemon(args: argparse.Namespace) -> int:
    """Run the controller as a daemon with web API."""
    try:
        from z407.gui.server import Z407WebApp
    except ImportError as exc:
        print(
            f"GUI dependencies not available: {exc}\n"
            "Install aiohttp: pip install aiohttp",
            file=sys.stderr,
        )
        return 1

    host = getattr(args, "host", "0.0.0.0")
    port = getattr(args, "port", 5000)
    no_browser = getattr(args, "no_browser", False)

    print(f"Starting Z407 daemon on {host}:{port}...")
    print("The BLE connection will persist even if you close the browser.")
    print("Press Ctrl+C to stop the daemon.\n")

    app = Z407WebApp(host=host, port=port)
    app.run(open_browser=not no_browser)
    return 0


def _cmd_gui(args: argparse.Namespace) -> int:
    """Launch GUI — native PySide6 by default, web with --web."""
    use_web = getattr(args, "web", False)

    if use_web:
        return _cmd_gui_web(args)

    # Native PySide6 GUI
    try:
        from z407.gui import launch_native_gui
    except ImportError as exc:
        print(
            f"Native GUI dependencies not available: {exc}\n"
            "Install PySide6 and qasync: pip install PySide6 qasync",
            file=sys.stderr,
        )
        return 1

    launch_native_gui()
    return 0


def _cmd_gui_web(args: argparse.Namespace) -> int:
    """Open the web control panel (connects to daemon)."""
    import socket
    import webbrowser

    host = getattr(args, "host", "0.0.0.0")
    port = getattr(args, "port", 5000)
    no_browser = getattr(args, "no_browser", False)

    # Check if daemon is already running
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    daemon_running = sock.connect_ex(("localhost", port)) == 0
    sock.close()

    if daemon_running:
        url = f"http://localhost:{port}"
        print(f"Daemon already running at {url}")
        if not no_browser:
            webbrowser.open(url)
        print("\nTo stop the daemon, run: pkill -f 'z407 daemon'")
        return 0

    # Daemon not running - start it
    print(f"Starting daemon on {host}:{port}...")
    print("The BLE connection will persist as a background daemon.")
    print("You can close the browser and reopen it anytime.\n")

    try:
        from z407.gui.server import Z407WebApp
    except ImportError as exc:
        print(
            f"GUI dependencies not available: {exc}\n"
            "Install aiohttp: pip install aiohttp",
            file=sys.stderr,
        )
        return 1

    app = Z407WebApp(host=host, port=port)
    app.run(open_browser=not no_browser)
    return 0


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

_COMMAND_MAP = {
    "scan": _cmd_scan,
    "status": _cmd_status,
    "volume": _cmd_volume,
    "bass": _cmd_bass,
    "play": _cmd_play,
    "next": _cmd_next,
    "prev": _cmd_prev,
    "input": _cmd_input,
    "pair": _cmd_pair,
    "reset": _cmd_reset,
    "daemon": _cmd_daemon,
}


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    _setup_logging(args.verbose, args.quiet)

    command = args.command

    if command is None:
        parser.print_help()
        sys.exit(1)

    # GUI and daemon are synchronous (run web server with event loop)
    if command == "gui":
        sys.exit(_cmd_gui(args))
    if command == "daemon":
        sys.exit(_cmd_daemon(args))

    handler = _COMMAND_MAP.get(command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    exit_code = asyncio.run(handler(args))
    sys.exit(exit_code)


def gui_main() -> None:
    """Entry point for ``z407-gui``: launch the native GUI."""
    _setup_logging(verbose=False, quiet=False)
    sys.exit(_cmd_gui(argparse.Namespace(web=False)))


if __name__ == "__main__":
    main()
