import importlib.util

from .asgi import MplbedMiddleware
from .html import raw as raw_html
from .html import safe as safe_html
from .integration import starlette as mplbed_starlette
from .server import mplbed_app_factory

__all__ = [
    "mplbed_starlette",
    "mplbed_app_factory",
    "raw_html",
    "safe_html",
    "MplbedMiddleware",
]

if importlib.util.find_spec("quart") is not None:
    from .integration import quart as mplbed_quart  # noqa: F401

    __all__.append("mplbed_quart")

if importlib.util.find_spec("django") is not None:
    from .integration import django as mplbed_django  # noqa: F401

    __all__.append("mplbed_django")
