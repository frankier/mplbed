from contextvars import ContextVar, Token
from dataclasses import dataclass, field

from matplotlib import _api
from matplotlib._pylab_helpers import Gcf
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
    _new_figs_token: Token | None = field(default=None, init=False, repr=False, compare=False)
    _new_managers: list = field(default_factory=list, init=False, repr=False, compare=False)


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
        token = _new_figs_local.set((*_new_figs_local.get(), html))
        if show_context._new_figs_token is None:
            show_context._new_figs_token = token


def consume_figs(show_context):
    if show_context.global_scope:
        new_figs = _new_figs_global.copy()
        _new_figs_global.clear()
        return new_figs
    else:
        cur = _new_figs_local.get()
        if show_context._new_figs_token is not None:
            _new_figs_local.reset(show_context._new_figs_token)
            show_context._new_figs_token = None
        return cur


def deregister_manager(manager):
    """Remove *manager* from pyplot's global registry if still present.

    Once a figure's HTML has been handed off to the mplbed server (which keeps
    the manager alive in its own ``managers`` dict for the websocket), there is
    no reason to keep it registered with pyplot. Leaving it registered would
    cause ``plt.show()`` to re-show it on every later call, accumulating stale
    figures.
    """
    if Gcf.figs.get(manager.num) is manager:
        Gcf.destroy(manager)


def get_webaggext_js(name="webaggext"):
    from importlib import resources as impresources

    import mplbed

    js_file = impresources.files(mplbed) / "webaggext" / f"{name}.js"
    with js_file.open() as f:
        return f.read()


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

    @classmethod
    def get_javascript(cls, stream=None, image_root="_images/", flow_control=None):
        import json
        from io import StringIO, TextIOBase

        output = StringIO() if stream is None else stream
        output: TextIOBase
        output.write("window.mpl = {};\n")
        output.write(f"mpl.IMAGE_ROOT = '{image_root}';\n")
        if flow_control is not None:
            output.write(f"mpl.flow_control = {json.dumps(flow_control, separators=(',', ':'), sort_keys=True)};\n")

        output.write(get_webaggext_js("mpl"))

        toolitems = []
        for name, tooltip, image, method in cls.ToolbarCls.toolitems:
            if name is None:
                toolitems.append(["", "", "", ""])
            else:
                toolitems.append([name, tooltip, image, method])
        output.write(f"mpl.toolbar_items = {json.dumps(toolitems)};\n\n")

        extensions = []
        for _filetype, ext in sorted(FigureCanvasWebAggCore.get_supported_filetypes_grouped().items()):
            extensions.append(ext[0])
        output.write("mpl.extensions = ")
        json.dump(extensions, output)
        output.write(";\n\n")
        output.write("mpl.default_extension = ")
        json.dump(FigureCanvasWebAggCore.get_default_filetype(), output)
        output.write(";\n")

        output.write(get_webaggext_js("webaggext"))

        if stream is None:
            assert isinstance(output, StringIO)
            return output.getvalue()


class FigureCollector:
    def __init__(self, **kwargs):
        self.token = None
        self.show_context = ShowContext(**kwargs)

    def __enter__(self):
        self.token = _current_show_context.set(self.show_context)

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert self.token is not None
        _current_show_context.reset(self.token)
        for manager in self.show_context._new_managers:
            deregister_manager(manager)

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

    @classmethod
    def new_manager(cls, figure, num):
        manager = super().new_manager(figure, num)
        show_context = _current_show_context.get()
        if show_context is not None:
            show_context._new_managers.append(manager)
        return manager

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wants_delayed_draw = False
        self._delayed_draw_dirty = False
        self._pending_completions = []

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

    @classmethod
    def show(cls, *, block=None):
        show_context = _current_show_context.get()
        if show_context is None:
            return super().show(block=block)
        # Within a collector context, only show figures created during this
        # context. matplotlib's default `show` iterates every figure in the
        # global pyplot registry, which would leak figures from concurrent
        # requests (and stale figures) into this collector.
        for manager in show_context._new_managers:
            if Gcf.figs.get(manager.num) is manager:
                manager.show()
