"""Web-based GUI server for the Z407 controller.

Runs an aiohttp web server alongside the BLE controller on a single
asyncio event loop.  Provides a REST API for commands and Server-Sent
Events (SSE) for real-time state updates.
"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import webbrowser
from pathlib import Path

from aiohttp import web

from z407.connection import ConnectionState
from z407.controller import Z407Controller

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


def _get_local_ip() -> str:
    """Best-effort detection of the machine's LAN IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class Z407WebApp:
    """Web application bridging the BLE controller and a browser UI."""

    def __init__(self, host: str = "0.0.0.0", port: int = 5000) -> None:
        self.host = host
        self.port = port
        self._open_browser = True

        self.controller = Z407Controller(
            on_state_change=self._on_state_change,
            on_volume_change=self._on_volume_change,
            on_input_change=self._on_input_change,
        )

        self._sse_clients: list[web.StreamResponse] = []
        self._ble_task: asyncio.Task | None = None

        self._app = web.Application()
        self._setup_routes()
        self._app.on_startup.append(self._on_startup)
        self._app.on_cleanup.append(self._on_cleanup)

    # -- Routes -------------------------------------------------------------

    def _setup_routes(self) -> None:
        self._app.router.add_get("/", self._handle_index)
        self._app.router.add_get("/api/status", self._handle_status)
        self._app.router.add_post("/api/command/{name}", self._handle_command)
        self._app.router.add_get("/api/events", self._handle_sse)

    async def _handle_index(self, request: web.Request) -> web.Response:
        html_path = STATIC_DIR / "index.html"
        return web.FileResponse(html_path)

    async def _handle_status(self, request: web.Request) -> web.Response:
        return web.json_response({
            "state": self.controller.state.value,
            "volume": self.controller.volume,
            "input": self.controller.active_input,
            "connected": self.controller.is_connected,
        })

    async def _handle_command(self, request: web.Request) -> web.Response:
        name = request.match_info["name"]

        params: dict = {}
        if request.content_length:
            try:
                params = await request.json()
            except Exception:
                pass

        try:
            result = await self._dispatch_command(name, params)
            return web.json_response({"success": True, **result})
        except ValueError as e:
            return web.json_response(
                {"success": False, "error": str(e)}, status=400,
            )
        except RuntimeError as e:
            return web.json_response(
                {"success": False, "error": str(e)}, status=503,
            )
        except Exception as e:
            logger.exception("Command failed: %s", name)
            return web.json_response(
                {"success": False, "error": str(e)}, status=500,
            )

    async def _dispatch_command(self, name: str, params: dict) -> dict:
        steps = params.get("steps", 1)

        match name:
            case "volume_up":
                await self.controller.volume_up(steps=steps)
                return {"volume": self.controller.volume}
            case "volume_down":
                await self.controller.volume_down(steps=steps)
                return {"volume": self.controller.volume}
            case "bass_up":
                await self.controller.bass_up(steps=steps)
                return {}
            case "bass_down":
                await self.controller.bass_down(steps=steps)
                return {}
            case "play_pause":
                await self.controller.play_pause()
                return {}
            case "next_track":
                await self.controller.next_track()
                return {}
            case "prev_track":
                await self.controller.prev_track()
                return {}
            case "input":
                source = params.get("source", "")
                await self.controller.switch_input(source)
                return {"input": source}
            case "pair":
                await self.controller.pair_device_and_switch(timeout=120.0)
                return {"message": "Pairing complete"}
            case "factory_reset":
                await self.controller.factory_reset()
                return {}
            case _:
                raise ValueError(f"Unknown command: {name}")

    # -- SSE (Server-Sent Events) -------------------------------------------

    async def _handle_sse(self, request: web.Request) -> web.StreamResponse:
        response = web.StreamResponse()
        response.headers["Content-Type"] = "text/event-stream"
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"
        response.headers["Access-Control-Allow-Origin"] = "*"
        await response.prepare(request)

        self._sse_clients.append(response)

        # Push initial state
        await self._send_sse(response, "status", {
            "state": self.controller.state.value,
            "volume": self.controller.volume,
            "input": self.controller.active_input,
            "connected": self.controller.is_connected,
        })

        try:
            while True:
                await asyncio.sleep(15)
                await response.write(b": keepalive\n\n")
        except (asyncio.CancelledError, ConnectionResetError, ConnectionError):
            pass
        finally:
            if response in self._sse_clients:
                self._sse_clients.remove(response)

        return response

    @staticmethod
    async def _send_sse(
        response: web.StreamResponse, event: str, data: dict,
    ) -> None:
        payload = f"event: {event}\ndata: {json.dumps(data)}\n\n"
        await response.write(payload.encode())

    async def _broadcast(self, event: str, data: dict) -> None:
        dead: list[web.StreamResponse] = []
        for client in self._sse_clients:
            try:
                await self._send_sse(client, event, data)
            except Exception:
                dead.append(client)
        for d in dead:
            self._sse_clients.remove(d)

    # -- Controller callbacks (called from the asyncio loop) ----------------

    def _on_state_change(self, state: ConnectionState) -> None:
        asyncio.ensure_future(self._broadcast("status", {
            "state": state.value,
            "connected": state == ConnectionState.CONNECTED,
            "volume": self.controller.volume,
            "input": self.controller.active_input,
        }))

    def _on_volume_change(self, volume: int) -> None:
        asyncio.ensure_future(self._broadcast("volume", {"volume": volume}))

    def _on_input_change(self, source: str) -> None:
        asyncio.ensure_future(self._broadcast("input", {"input": source}))

    # -- Lifecycle ----------------------------------------------------------

    async def _on_startup(self, app: web.Application) -> None:
        self._ble_task = asyncio.create_task(self.controller.start())

        local_ip = _get_local_ip()
        url = f"http://localhost:{self.port}"
        print(
            f"\n"
            f"  ╔═══════════════════════════════════════════╗\n"
            f"  ║   Z407 Controller                        ║\n"
            f"  ║   Local:   http://localhost:{self.port:<14}║\n"
            f"  ║   Network: http://{local_ip}:{self.port:<14}║\n"
            f"  ╚═══════════════════════════════════════════╝\n"
        )

        if self._open_browser:
            webbrowser.open(url)

    async def _on_cleanup(self, app: web.Application) -> None:
        await self.controller.stop()
        if self._ble_task:
            self._ble_task.cancel()
            try:
                await self._ble_task
            except asyncio.CancelledError:
                pass

    def run(self, open_browser: bool = True) -> None:
        """Start the web server and BLE controller."""
        self._open_browser = open_browser
        web.run_app(
            self._app,
            host=self.host,
            port=self.port,
            print=None,  # we print our own banner
        )
