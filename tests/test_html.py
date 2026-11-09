import inspect

from mplbed import raw_html, safe_html
from mplbed.html import _impl
from mplbed.integration import django, quart, starlette
from mplbed.server import mplbed_app_factory
from mplbed.webaggext import FigureCollector


def _prefix_and_app():
    return "/plots", mplbed_app_factory()


def test_navigation_suppression_defaults_to_disabled():
    for helper in (
        raw_html.figure_html_from_id,
        raw_html.figure_html,
        raw_html.figure_page_html,
        safe_html.figure_html_from_id,
        safe_html.figure_html,
    ):
        parameter = inspect.signature(helper).parameters["prevent_default_navigation"]
        assert parameter.default is False

    assert inspect.signature(FigureCollector).parameters["prevent_default_navigation"].default is False
    for helper in (
        starlette._figure_page_html_jinja,
        quart._figure_page_html_jinja,
        django._figure_page_html_dtl,
    ):
        parameter = inspect.signature(helper).parameters["prevent_default_navigation"]
        assert parameter.default is False


def test_figure_html_from_id_serializes_navigation_suppression():
    kwargs = {"prefix_and_app": _prefix_and_app()}

    default_html = raw_html.figure_html_from_id(1, **kwargs)
    opted_in_html = raw_html.figure_html_from_id(2, prevent_default_navigation=True, **kwargs)

    assert '"msg_discrete",\n        false' in default_html
    assert '"msg_discrete",\n        true' in opted_in_html


def test_borderless_defaults_to_enabled():
    for helper in (
        raw_html.head_content,
        safe_html.head_content,
        raw_html.figure_page_html,
        starlette._figure_page_html_jinja,
        quart._figure_page_html_jinja,
        django._figure_page_html_dtl,
    ):
        assert inspect.signature(helper).parameters["borderless"].default is True


def test_head_content_can_restore_figure_frame():
    kwargs = {"core": True, "prefix_and_app": _prefix_and_app()}

    borderless_head = raw_html.head_content(**kwargs)
    framed_head = raw_html.head_content(borderless=False, **kwargs)

    assert ".mpl-figure-root > .ui-dialog-titlebar" in borderless_head
    assert ".mpl-figure-root > .mpl-canvas-container" in borderless_head
    assert ".mpl-figure-root > .ui-dialog-titlebar" not in framed_head
    assert ".mpl-figure-root > .mpl-canvas-container" not in framed_head


def test_figure_page_html_passes_borderless_to_head_content(monkeypatch):
    seen = []
    monkeypatch.setattr(_impl, "figure_html", lambda *args, **kwargs: "<div>plot</div>")
    monkeypatch.setattr(_impl, "head_content", lambda **kwargs: seen.append(kwargs) or "assets")

    raw_html.figure_page_html(object())
    raw_html.figure_page_html(object(), borderless=False)

    assert seen == [{"core": True, "borderless": True}, {"core": True, "borderless": False}]
