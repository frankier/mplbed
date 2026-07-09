import anyio
from anyio.lowlevel import EventLoopToken, current_token
from starlette.websockets import WebSocket


def is_anyio_worker_thread() -> bool:
    from anyio._core._eventloop import threadlocals

    try:
        threadlocals.current_token
    except AttributeError:
        return False
    else:
        return True


class WorkerThreadOnlyError(RuntimeError):
    def __init__(self):
        super().__init__("This method can only be called from an anyio worker thread. ")


class WorkerThreadWebSocket:
    def __init__(self, websocket: WebSocket, token: EventLoopToken | None = None):
        self.websocket = websocket
        # If token is not provided, get the current token from anyio
        self.token = token or current_token()

    def send_json(self, data):
        """Send JSON data synchronously"""
        if not is_anyio_worker_thread():
            raise WorkerThreadOnlyError()
        return anyio.from_thread.run(self.websocket.send_json, data, token=self.token)  # ty: ignore

    def send_binary(self, data: bytes):
        """Send binary data synchronously"""
        if not is_anyio_worker_thread():
            raise WorkerThreadOnlyError()
        return anyio.from_thread.run(self.websocket.send_bytes, data, token=self.token)  # ty: ignore
