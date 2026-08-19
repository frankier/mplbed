from __future__ import annotations

import asyncio
import weakref
from dataclasses import dataclass
from typing import Any

import anyio
from matplotlib._pylab_helpers import Gcf
from matplotlib.figure import Figure
from matplotlib.pyplot import _get_backend_mod

try:
    from nicegui import ui
    from nicegui.element import Element
except ImportError as error:
    raise ImportError("NiceGUI support requires the 'mplbed[nicegui]' extra.") from error

from mplbed.asgi import url_path_for
from mplbed.consts import DEFAULT_PREFIX
from mplbed.html.raw import head_content
from mplbed.integration import starlette
from mplbed.server import mplbed_app_factory
from mplbed.server._impl import add_manager, managers

__all__ = ["Matplotlib", "matplotlib", "setup"]


@dataclass
class _SetupState:
    app: Any
    options: dict[str, Any]
    prefix_and_app: tuple[str, Any]


_setup_state: _SetupState | None = None


class MplbedFigure(Figure):
    """A Matplotlib figure owned by a NiceGUI element."""

    def __init__(self, element: Matplotlib, **figure_kwargs: Any) -> None:
        super().__init__(**figure_kwargs)
        self._element = weakref.ref(element)

    def __enter__(self) -> MplbedFigure:
        return self

    def __exit__(self, *_: object) -> None:
        element = self._element()
        if element is not None:
            element.update()


class Matplotlib(Element, component="nicegui.js", default_classes="mplbed-nicegui"):
    """Embed an owned Matplotlib figure as an interactive NiceGUI element.

    Parameters
    ----------
    **figure_kwargs
        Keyword arguments forwarded to :class:`matplotlib.figure.Figure`.
    """

    def __init__(self, **figure_kwargs: Any) -> None:
        if _setup_state is None:
            raise RuntimeError("Call mplbed.integration.nicegui.setup(app) before creating a matplotlib element.")

        super().__init__()
        self._figure = MplbedFigure(self, **figure_kwargs)
        self._manager = _get_backend_mod().new_figure_manager_given_figure(id(self._figure), self._figure)
        if not hasattr(self._manager, "add_web_socket"):
            raise RuntimeError("The configured Matplotlib backend does not support WebAgg connections.")
        add_manager(self._manager)
        self._draw_tasks: set[asyncio.Task[None]] = set()

        prefix_and_app = _setup_state.prefix_and_app
        self._props["figureId"] = self._manager.num
        self._props["websocketUrl"] = url_path_for(
            "websocket",
            fig_id=self._manager.num,
            _prefix_and_app=prefix_and_app,
        )
        self._props["downloadUrl"] = url_path_for(
            "download_fig",
            fig_id=self._manager.num,
            fmt="{fmt}",
            _prefix_and_app=prefix_and_app,
        )

    @property
    def figure(self) -> Figure:
        """The Matplotlib figure owned by this element."""
        return self._figure

    def update(self) -> None:
        """Schedule a redraw of the figure for connected clients."""
        has_web_sockets = bool(self._manager.web_sockets)  # ty: ignore
        if hasattr(self._manager, "wants_delayed_draw"):
            should_wake_clients = has_web_sockets and not self._manager.wants_delayed_draw
            self.figure.canvas.draw_idle()
            if should_wake_clients:
                self._run_in_worker(self.figure.canvas.send_event, "draw")  # ty: ignore
        elif has_web_sockets:
            self._run_in_worker(self.figure.canvas.draw_idle)
        else:
            self.figure.canvas.draw_idle()
        super().update()

    def _run_in_worker(self, function: Any, *args: Any) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        awaitable = anyio.to_thread.run_sync(function, *args)  # ty: ignore
        task = loop.create_task(awaitable)
        self._draw_tasks.add(task)
        task.add_done_callback(self._finish_draw_task)

    def _finish_draw_task(self, task: asyncio.Task[None]) -> None:
        self._draw_tasks.discard(task)
        if not task.cancelled():
            task.exception()

    def _handle_delete(self) -> None:
        self.run_method("dispose")
        manager = managers.get(self._manager.num)
        if manager is self._manager and not manager.web_sockets:
            Gcf.destroy(manager)
            managers.pop(manager.num, None)
        super()._handle_delete()


def matplotlib(**figure_kwargs: Any) -> Matplotlib:
    """Create an interactive Matplotlib element with an owned figure.

    Parameters
    ----------
    **figure_kwargs
        Keyword arguments forwarded to :class:`matplotlib.figure.Figure`.

    Returns
    -------
    Matplotlib
        The newly created NiceGUI element.
    """
    return Matplotlib(**figure_kwargs)


def setup(
    app: Any,
    *,
    prefix: str = DEFAULT_PREFIX,
    mplbed_starlette_app: Any = None,
    mplbed_starlette_app_kwargs: dict[str, Any] | None = None,
    manage_routing: bool = True,
    do_use_mpl_backend: bool = True,
    use_webaggext_backend: bool = True,
) -> None:
    """Configure a NiceGUI app for interactive mplbed elements.

    Parameters
    ----------
    app
        The NiceGUI application to configure before ``ui.run()``.
    prefix
        URL prefix used for mplbed's routes.
    mplbed_starlette_app
        An optional pre-built mplbed Starlette sub-application.
    mplbed_starlette_app_kwargs
        Optional arguments used to create the mplbed Starlette application.
    manage_routing
        Whether mplbed should route requests under ``prefix``.
    do_use_mpl_backend
        Whether to select mplbed's Matplotlib backend.
    use_webaggext_backend
        Whether to select WebAggExt instead of Matplotlib's base WebAgg backend.
    """
    global _setup_state

    options = {
        "prefix": prefix,
        "mplbed_starlette_app": mplbed_starlette_app,
        "mplbed_starlette_app_kwargs": mplbed_starlette_app_kwargs,
        "manage_routing": manage_routing,
        "do_use_mpl_backend": do_use_mpl_backend,
        "use_webaggext_backend": use_webaggext_backend,
    }
    if _setup_state is not None:
        if _setup_state.app is app and _setup_state.options == options:
            return
        raise RuntimeError("mplbed's NiceGUI integration is already configured with different options.")

    if not manage_routing and mplbed_starlette_app is None:
        raise ValueError(
            "If manage_routing is False, you must construct and provide the mplbed Starlette app yourself."
        )
    resolved_mplbed_app = (
        mplbed_starlette_app
        if mplbed_starlette_app is not None
        else mplbed_app_factory(**(mplbed_starlette_app_kwargs or {}))
    )
    resolved_options = {**options, "mplbed_starlette_app": resolved_mplbed_app}
    starlette.setup(app, **resolved_options)
    ui.add_head_html(
        head_content(core=True, prefix_and_app=(prefix, resolved_mplbed_app)),
        shared=True,
    )
    _setup_state = _SetupState(
        app=app,
        options=options,
        prefix_and_app=(prefix, resolved_mplbed_app),
    )
