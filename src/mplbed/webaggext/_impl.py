from contextvars import ContextVar
from dataclasses import dataclass

from matplotlib import _api
from matplotlib.backend_bases import CloseEvent, _Backend
from matplotlib.backends.backend_webagg_core import (
    FigureCanvasWebAggCore,
    FigureManagerWebAgg,
    NavigationToolbar2WebAgg,
)


@dataclass
class ShowContext:
    target: str
    on_close: str
    global_scope: bool = False


class NoShowContextError(ValueError):
    def __init__(self, message=None, funcname=None):
        if message is None:
            if funcname is None:
                raise ValueError("Must provide either a message or a funcname")
            message = (
                f"Cannot call {funcname} without a ShowContext. "
                "Use `with FigureCollector(...):` to create a ShowContext."
            )
        super().__init__(message)


_new_figs_global: list[str] = []
_new_figs_local: ContextVar[tuple[str, ...]] = ContextVar("_new_figs", default=())
_current_show_context: ContextVar[ShowContext | None] = ContextVar("current_scope", default=None)


def require_show_context(funcname):
    show_context = _current_show_context.get()
    if show_context is None:
        raise NoShowContextError(funcname=funcname)
    return show_context


def add_fig(html: str):
    show_context = require_show_context("add_fig")
    if show_context.global_scope:
        _new_figs_global.append(html)
    else:
        _new_figs_local.set((*_new_figs_local.get(), html))


def consume_figs(show_context):
    if show_context.global_scope:
        new_figs = _new_figs_global.copy()
        _new_figs_global.clear()
        return new_figs
    else:
        cur = _new_figs_local.get()
        _new_figs_local.set(())
        return cur


class FigureManagerWebAggExt(FigureManagerWebAgg):
    canvas: FigureCanvasWebAggExt
    _toolbar2_class = NavigationToolbar2WebAgg

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wants_close = False
        self._retains = []

    def show(self):
        from mplbed.html.raw import figure_html_from_id
        from mplbed.server._impl import add_manager

        show_context = require_show_context("FigureManagerWebAggExt.show")
        add_manager(self)
        html = figure_html_from_id(self.num, target=show_context.target, on_close=show_context.on_close)
        add_fig(html)

    def destroy(self):
        CloseEvent("close_event", self.canvas)._process()  # ty: ignore

    def close(self):
        self._wants_close = True

    def add_retains(self, *retains):
        self._retains.extend(retains)

    @property
    def wants_close(self):
        return self._wants_close

    @property
    def wants_delayed_draw(self):
        return self.canvas._wants_delayed_draw


class FigureCollector:
    def __init__(self, **kwargs):
        self.token = None
        self.show_context = ShowContext(**kwargs)

    def __enter__(self):
        self.token = _current_show_context.set(self.show_context)

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert self.token is not None
        _current_show_context.reset(self.token)

    def consume_one(self):
        figs = consume_figs(self.show_context)
        if len(figs) != 1:
            raise ValueError(f"Expected exactly one figure, but got {len(figs)}")
        return figs[0]

    def consume_many(self, required=False):
        figs = consume_figs(self.show_context)
        if required and len(figs) == 0:
            raise ValueError("Expected at least one figure, but got none")
        return figs


class FigureCanvasWebAggExt(FigureCanvasWebAggCore):
    manager: None | FigureManagerWebAggExt
    manager_class = _api.classproperty(lambda cls: FigureManagerWebAggExt)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wants_delayed_draw = False
        self._delayed_draw_dirty = False

    def handle_close(self, event):
        if self.manager is not None:
            self.manager.close()
        else:
            # Close immediately if no manager is present
            CloseEvent("close_event", self)._process()  # ty: ignore

    def draw(self):
        self._wants_delayed_draw = False
        self._delayed_draw_dirty = False
        super().draw()

    def draw_idle(self):
        self._wants_delayed_draw = True
        self._delayed_draw_dirty = True


@_Backend.export
class _BackendWebAggExt(_Backend):
    FigureCanvas = FigureCanvasWebAggExt
    FigureManager = FigureManagerWebAggExt
