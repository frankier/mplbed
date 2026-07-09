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

from mplbed.server.utils import WorkerThreadWebSocket
from mplbed.webaggext.impl import (
    FigureCollector,
    FigureManagerWebAggExt,
)

managers = {}


def add_manager(manager):
    fig_id = manager.num
    managers[fig_id] = manager


def get_mpl_js(request):
    from mplbed.asgi import url_path_for

    js_content = FigureManagerWebAggExt.get_javascript()
    images_url = url_path_for("data", path="images/")
    js_content = js_content.replace("'_images/'", f"'{images_url}'")
    return Response(js_content, media_type="application/javascript")


def get_webaggext_js(request):
    from importlib import resources as impresources

    import mplbed

    js_file = impresources.files(mplbed) / "webaggext" / "webaggext.js"
    with js_file.open() as f:
        contents = f.read()
    return Response(contents, media_type="application/javascript")


async def download_fig(request):
    fig_id = request.path_params["fig_id"]
    fmt = request.path_params["fmt"]
    if fig_id not in managers:
        raise HTTPException(
            status_code=404, detail="Figure not found; It may have expired."
        )
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


async def delayed_draw(manager, mpl_lock):
    import anyio

    async with mpl_lock:
        if manager.canvas._delayed_draw_dirty:
            await anyio.to_thread.run_sync(manager.canvas.draw)  # ty: ignore


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
                        manager.canvas._wants_delayed_draw = False
                        tg.start_soon(delayed_draw, manager, mpl_lock)
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


def mplbed_app_factory():
    from os.path import realpath

    routes = [
        Mount(
            "/_static",
            app=StaticFiles(
                directory=realpath(FigureManagerWebAggExt.get_static_file_path())
            ),
            name="static",
        ),
        Mount(
            "/_data",
            app=StaticFiles(directory=realpath(mpl.get_data_path())),
            name="data",
        ),
        Route("/mpl.js", get_mpl_js, name="mpl_js"),
        Route("/webaggext.js", get_webaggext_js, name="webaggext_js"),
        WebSocketRoute("/ws/{fig_id:int}", handle_websocket, name="websocket"),
        Route("/download/{fig_id:int}.{fmt}", download_fig, name="download_fig"),
    ]
    app = Starlette(routes=routes)
    return app
