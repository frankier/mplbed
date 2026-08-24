import inspect

from mplbed import raw_html, safe_html
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
