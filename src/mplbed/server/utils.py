import asyncio

from starlette.websockets import WebSocket


class SyncWebSocket:
    def __init__(
        self, websocket: WebSocket, loop: asyncio.AbstractEventLoop | None = None
    ):
        self.websocket = websocket
        # If loop is not provided, use the running event loop
        self.loop = loop or asyncio.get_event_loop()

    def send_json(self, data):
        """Send JSON data synchronously"""
        return asyncio.ensure_future(self.websocket.send_json(data), loop=self.loop)

    def send_binary(self, data: bytes):
        """Send binary data synchronously"""
        return asyncio.ensure_future(self.websocket.send_bytes(data), loop=self.loop)
