from contextvars import ContextVar
from typing import Any

from starlette.applications import Starlette
from starlette.routing import Match, Mount

from mplbed.doc_helpers import PARAMS_DS as D
from mplbed.doc_helpers import doc

_native_app: ContextVar[Any] = ContextVar("_native_app", default=None)
_prefix_and_app: ContextVar[tuple[str, Starlette] | None] = ContextVar(
    "_prefix_and_app", default=None
)


class MplbedMiddleware:
    @doc(
        f"""
        Initialize the MplbedMiddleware.

        Parameters
        ----------
        default_app : ASGI3Application
            The default ASGI app to use (i.e. the main app, typically yours).
        {D.prefix}
        {D.mplbed_starlette_app("app")}
        {D.mplbed_starlette_app_kwargs("app_kwargs")}
        {D.manage_routing}
        {D.native_app}
        """
    )
    def __init__(
        self,
        default_app,
        *,
        prefix: str,
        app=None,
        app_kwargs=None,
        manage_routing=True,
        native_app=None,
    ):
        from mplbed.server import mplbed_app_factory

        self.main_app = default_app
        if app is None and not manage_routing:
            raise ValueError(
                "If manage_routing is False, you must construct and provide the app yourself "
                "(otherwise how do you plan to route to it?)"
            )
        if app is not None:
            self.mplbed_app = app
        elif app_kwargs is not None:
            self.mplbed_app = mplbed_app_factory(**app_kwargs)
        else:
            self.mplbed_app = mplbed_app_factory()
        self.prefix = prefix
        self.manage_routing = manage_routing
        self.native_app = native_app
        if manage_routing:
            self.mount = Mount(prefix, self.mplbed_app)

    async def __call__(self, scope, receive, send):
        with (
            _native_app.set(self.native_app),
            _prefix_and_app.set((self.prefix, self.mplbed_app)),
        ):
            if self.manage_routing:
                assert self.mount
                match, child_scope = self.mount.matches(scope)
                if match != Match.NONE:
                    scope.update(child_scope)
                    await self.mplbed_app(scope, receive, send)
                    return
            await self.main_app(scope, receive, send)


def get_native_app():
    """
    Get the native app from the current context.

    Returns
    -------
    Any
        The native app, or None if not set.
    """
    return _native_app.get()


def get_asgi_app():
    """
    Get the ASGI app from the current context.

    Returns
    -------
    ASGI3Application | None
        The ASGI app, or None if not set.
    """
    val = _prefix_and_app.get()
    if val is not None:
        _, app = val
        return app
    return None


def url_path_for(name, **path_params):
    prefix_and_app = path_params.pop("_prefix_and_app", None)
    if prefix_and_app is None:
        prefix_and_app = _prefix_and_app.get()
        if prefix_and_app is None:
            raise RuntimeError(
                "Missing current prefix_and_app in context! "
                "Did you install the MlpbedMiddleware? (_prefix_and_app was not passed)"
            )
    prefix, app = prefix_and_app
    path = app.url_path_for(name, **path_params)
    return prefix + path
