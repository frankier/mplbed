from abc import ABCMeta
import io
import matplotlib as mpl
import mimetypes
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.routing import Route, Mount, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocketState

from mplbed.server.utils import SyncWebSocket
from mplbed.webaggext.impl import (
    FigureManagerWebAggExt,
    FigureCollector,
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

    js_file = impresources.files(mplbed) / 'webaggext' / 'webaggext.js'
    with js_file.open() as f:
        contents = f.read()
    return Response(contents, media_type="application/javascript")


async def download_fig(request):
    fig_id = request.path_params["fig_id"]
    fmt = request.path_params["fmt"]
    app = request.app
    if fig_id not in managers:
        raise HTTPException(status_code=404, detail="Figure not found; It may have expired.")
    manager = managers[fig_id]
    buff = io.BytesIO()
    manager.canvas.figure.savefig(buff, format=fmt)
    resp_text = buff.getvalue()
    media_type = mimetypes.types_map.get(fmt, 'binary')
    return Response(resp_text, media_type=media_type)


async def handle_websocket(websocket):
    import os
    mplbed_profile = "MPLBED_PROFILE" in os.environ
    if mplbed_profile:
        try:
            import pyinstrument  # ty: ignore[unresolved-import]
        except ImportError:
            mplbed_profile = False
    fig_id = websocket.path_params["fig_id"]
    supports_binary = True
    added = False
    fig_ids = []
    sync_websocket = SyncWebSocket(websocket)
    if mplbed_profile:
        profile_counter = 0
    try:
        await websocket.accept()
        async for message in websocket.iter_json():
            msg_fig_id = message["figure_id"]
            if msg_fig_id != fig_id:
                continue
            fig_ids.append(fig_id)
            manager = managers[fig_id]
            if not added:
                manager.add_web_socket(sync_websocket)
                added = True
            collector = FigureCollector(target="modal", on_close="remove_dialog")
            if message['type'] == 'supports_binary':
                supports_binary = message['value']
            else:
                with collector:
                    if mplbed_profile:
                        profile_counter += 1
                        profiler = pyinstrument.Profiler()
                        profiler.start()
                    try:
                        manager.handle_json(message)
                    finally:
                        if mplbed_profile:
                            profiler.stop()
                            out_path = f"profiles/{fig_id}_{profile_counter}.html"
                            with open(out_path, "w") as f:
                                f.write(profiler.output_html())
                                import os
                                full_path = os.path.realpath(f.name)
                                print(f"Wrote profile to {full_path}")
            for fig in collector.consume_many():
                await websocket.send_json({
                    "type": "newfig",
                    "payload": fig
                })
    finally:
        if websocket.client_state != WebSocketState.DISCONNECTED and websocket.application_state != WebSocketState.DISCONNECTED:
            await websocket.close()
        for fig_id in fig_ids:
            if fig_id is not None and fig_id in managers:
                manager = managers[fig_id]
                manager.remove_web_socket(sync_websocket)
                del managers[fig_id]


def handle_status_page(request):
    pass


class MplPageAuth(metaclass=ABCMeta):
    def __call__(self, *args, **kwargs):
        ...


class ExternalStatusPageAuth(MplPageAuth):
    def __call__(self, handler, *args, **kwargs):
        return handler(*args, **kwargs)


class ExternalStatusPageAuth(MplPageAuth):
    def __call__(self, handler, *args, **kwargs):
        return handler(*args, **kwargs)


def mplbed_app_factory(*, enable_status_page=False, status_page_auth: MplPageAuth | None = None):
    from os.path import realpath
    if enable_status_page:
        if status_page_auth is None:
            raise ValueError("status_page_auth must be provided when enable_status_page is True")
        if not isinstance(status_page_auth, MplPageAuth):
            raise ValueError("status_page_auth must be an subclass of StatusPageAuth")
    routes = [
        Mount('/_static', app=StaticFiles(directory=realpath(FigureManagerWebAggExt.get_static_file_path())), name="static"),
        Mount('/_data', app=StaticFiles(directory=realpath(mpl.get_data_path())), name="data"),
        Route('/mpl.js', get_mpl_js, name="mpl_js"),
        Route('/webaggext.js', get_webaggext_js, name="webaggext_js"),
        WebSocketRoute('/ws/{fig_id:int}', handle_websocket, name="websocket"),
        Route('/download/{fig_id:int}.{fmt}', download_fig, name="download_fig"),
    ]
    if enable_status_page:
        assert status_page_auth is not None
        routes.append(Route('/status', lambda *args, **kwargs: status_page_auth(handle_status_page, *args, **kwargs), name="status"))
    app = Starlette(routes=routes)
    return app
