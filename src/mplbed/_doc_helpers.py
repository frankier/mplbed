from typing import Any

from .consts import DEFAULT_PREFIX


def doc(s):
    def decorator(func):
        func.__doc__ = s
        return func

    return decorator


def fdf(s):
    """_F_ix _D_ocstring _F_ragment for inclusion in a docstring template."""
    from inspect import cleandoc
    from textwrap import indent

    return indent(cleandoc(s), "    ").strip()


class DotAccessDict(dict[str, Any]):
    __getattr__ = dict.get


PARAMS_DS: Any = DotAccessDict(
    prefix=fdf(f"""
    prefix : str, optional
        The URL prefix for the routes handleded by `mplbed`. Default is '{DEFAULT_PREFIX}'.
    """),
    mplbed_starlette_app=lambda name="mplbed_starlette_app": fdf(f"""
    {name} : Starlette, optional
        The Starlette app to use for the `mplbed` routes, as returned by `mplbed_starlette_app_factory`.
        If not provided, a new app will be created using the provided `mplbed_starlette_app_kwargs`.
    """),
    mplbed_starlette_app_kwargs=lambda name="mplbed_starlette_app_kwargs": fdf(f"""
    {name} : dict, optional
        Keyword arguments to pass to the Mplbed app factory if `mplbed_starlette_app` is not provided.
    """),
    manage_routing=fdf("""
    manage_routing : bool, optional
        Whether the ASGI middleware should manage routing. Default is True.
        If you set this to False, you are responsible for routing requests to
        the Mplbed app under the given `prefix`.
    """),
    native_app=fdf("""
    native_app : Any, optional
        The native app, e.g. the `Starlette` or `Quart` instance, which will
        typically be saved in cased it is needed by the specific integration,
        e.g. for rendering templates.
    """),
    prevent_default_navigation=fdf("""
    prevent_default_navigation : bool, optional
        Prevent the browser's default scrolling behavior for wheel, Arrow,
        PageUp/PageDown, Home/End, and Space events directed at the plot.
        Events are still sent to Matplotlib. Default is False.
    """),
)
