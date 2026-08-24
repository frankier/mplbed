import io
import mimetypes

import matplotlib as mpl
from anyio import create_task_group
from matplotlib._pylab_helpers import Gcf
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocketState

from mplbed.server._utils import WorkerThreadWebSocket
from mplbed.webaggext._impl import (
    FigureCollector,
    FigureManagerWebAggExt,
)

managers = {}

FLOW_CONTROL_DEFAULTS = {
    "resize_max_in_flight": 1,
    "motion_throttle_ms": None,
    "scroll_throttle_ms": None,
}

COMPLETION_CONTROLLED_REQUESTS = {"motion_notify", "resize"}


def add_manager(manager):
    fig_id = manager.num
    managers[fig_id] = manager


def get_mpl_js(request):
    from mplbed.asgi import url_path_for

    images_url = url_path_for("data", path="images/")
    js_content = FigureManagerWebAggExt.get_javascript(
        image_root=images_url,
        flow_control=request.app.state.flow_control,
    )
    return Response(js_content, media_type="application/javascript")


async def download_fig(request):
    fig_id = request.path_params["fig_id"]
    fmt = request.path_params["fmt"]
    if fig_id not in managers:
        raise HTTPException(status_code=404, detail="Figure not found; It may have expired.")
    manager = managers[fig_id]
    buff = io.BytesIO()
    manager.canvas.figure.savefig(buff, format=fmt)
    resp_text = buff.getvalue()
    media_type = mimetypes.types_map.get(fmt, "binary")
    return Response(resp_text, media_type=media_type)


def handle_json(manager, websocket, message):
    collector = FigureCollector(target="modal", on_close="remove_dialog")
    with collector:
        manager.handle_json(message)
    for fig in collector.consume_many():
        websocket.send_json({"type": "newfig", "payload": fig})


def close_fig(worker_websocket, fig_id, clean):
    manager = managers[fig_id]
    if clean:
        worker_websocket.send_json({"type": "closed", "figure_id": fig_id})
    Gcf.destroy(manager)
    del managers[fig_id]


CLEANUP_CLOSED = True


def _send_completion(worker_websocket, request_type, seq):
    worker_websocket.send_json({"type": f"{request_type}_completion", "seq": seq})


def _draw_and_complete(manager, worker_websocket):
    if manager.canvas._delayed_draw_dirty:
        manager.canvas.draw()
    completions = manager.canvas._pending_completions
    manager.canvas._pending_completions = []
    for request_type, seq in completions:
        _send_completion(worker_websocket, request_type, seq)


async def delayed_draw(manager, mpl_lock, worker_websocket):
    import anyio

    async with mpl_lock:
        await anyio.to_thread.run_sync(_draw_and_complete, manager, worker_websocket)  # ty: ignore


async def handle_websocket(websocket):
    import anyio
    from anyio.lowlevel import current_token

    fig_id = websocket.path_params["fig_id"]
    # TOOD: Make use of this?
    supports_binary = True  # noqa: F841
    added = False
    fig_ids = []
    worker_websocket = WorkerThreadWebSocket(websocket, current_token())
    mpl_lock = anyio.Lock()
    try:
        await websocket.accept()
        async with create_task_group() as tg:
            async for message in websocket.iter_json():
                msg_fig_id = message["figure_id"]
                if msg_fig_id != fig_id:
                    continue
                fig_ids.append(fig_id)
                manager = managers[fig_id]
                async with mpl_lock:
                    if not added:
                        await anyio.to_thread.run_sync(  # ty: ignore
                            manager.add_web_socket, worker_websocket
                        )
                        added = True
                    if message["type"] == "supports_binary":
                        supports_binary = message["value"]  # noqa: F841
                    else:
                        await anyio.to_thread.run_sync(  # ty: ignore
                            handle_json, manager, worker_websocket, message
                        )
                if isinstance(manager, FigureManagerWebAggExt):
                    if manager.wants_close:
                        async with mpl_lock:
                            manager.remove_web_socket(worker_websocket)
                            await anyio.to_thread.run_sync(  # ty: ignore
                                close_fig, worker_websocket, fig_id, True
                            )
                        fig_ids.remove(fig_id)
                    elif manager.wants_delayed_draw:
                        if message["type"] in COMPLETION_CONTROLLED_REQUESTS and "seq" in message:
                            manager.canvas._pending_completions.append((message["type"], message["seq"]))
                        manager.canvas._wants_delayed_draw = False
                        tg.start_soon(delayed_draw, manager, mpl_lock, worker_websocket)
                    elif message["type"] in COMPLETION_CONTROLLED_REQUESTS and "seq" in message:
                        await websocket.send_json({"type": f"{message['type']}_completion", "seq": message["seq"]})
                if not fig_ids:
                    break
    finally:
        if (
            websocket.client_state != WebSocketState.DISCONNECTED
            and websocket.application_state != WebSocketState.DISCONNECTED
        ):
            await websocket.close()
        for fig_id in fig_ids:
            if fig_id is not None and fig_id in managers:
                manager = managers[fig_id]
                manager.remove_web_socket(worker_websocket)
                if CLEANUP_CLOSED and not manager.web_sockets:
                    await anyio.to_thread.run_sync(  # ty: ignore
                        close_fig, worker_websocket, fig_id, False
                    )


def _positive_integer(name: str, value: int | None, *, optional: bool = False) -> int | None:
    if optional and value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        qualifier = "a positive integer or None" if optional else "a positive integer"
        raise ValueError(f"{name} must be {qualifier}")
    return value


def mplbed_app_factory(
    *,
    resize_max_in_flight: int = 1,
    motion_throttle_ms: int | None = None,
    scroll_throttle_ms: int | None = None,
) -> Starlette:
    """Create the Starlette backend app for WebAgg or WebAggExt.

    Parameters
    ----------
    resize_max_in_flight : int, optional
        Maximum resize requests awaiting completion. Must be positive; the
        default is one.
    motion_throttle_ms, scroll_throttle_ms : int or None, optional
        Leading-and-trailing throttle interval for the corresponding browser
        input stream. ``None`` (the default) preserves every event. Positive
        values opt into sampled motion callbacks or aggregated scroll steps.
    """
    from os.path import realpath

    routes = [
        Mount(
            "/_static",
            app=StaticFiles(directory=realpath(FigureManagerWebAggExt.get_static_file_path())),
            name="static",
        ),
        Mount(
            "/_data",
            app=StaticFiles(directory=realpath(mpl.get_data_path())),
            name="data",
        ),
        Route("/mpl.js", get_mpl_js, name="mpl_js"),
        WebSocketRoute("/ws/{fig_id:int}", handle_websocket, name="websocket"),
        Route("/download/{fig_id:int}.{fmt}", download_fig, name="download_fig"),
    ]
    app = Starlette(routes=routes)
    app.state.flow_control = {
        "resize_max_in_flight": _positive_integer("resize_max_in_flight", resize_max_in_flight),
        "motion_throttle_ms": _positive_integer("motion_throttle_ms", motion_throttle_ms, optional=True),
        "scroll_throttle_ms": _positive_integer("scroll_throttle_ms", scroll_throttle_ms, optional=True),
    }
    return app
