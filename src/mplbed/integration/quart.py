try:
    import quart
except ImportError as e:
    e.add_note(
        "The mplbed Quart integration requires the Quart package. Please install it with `pip install quart`."
    )
    raise


from mplbed.asgi import MplbedMiddleware
from mplbed.consts import DEFAULT_PREFIX, HEAD_TEMPLATE_VARIABLE_NAME
from mplbed.doc_helpers import PARAMS_DS as D
from mplbed.doc_helpers import fdf
from mplbed.html.impl import default_figure_page_template
from mplbed.html.raw import figure_page_html
from mplbed.html.safe import head_content
from mplbed.integration.common import mk_figure_page_variants, setup_page_docstring


def _mk_quart_response(html):
    return quart.Response(html, mimetype="text/html")


def _require_native_app(app=None):
    if app is None:
        from mplbed.asgi import get_native_app

        app = get_native_app()
        if app is None:
            raise RuntimeError(
                "No current app found. Please provide a Quart app or ensure that the MplbedMiddleware is installed."
            )
    return app


async def _figure_page_html_jinja(fig, *, template, app=None):
    from mplbed.html.safe import figure_html

    app = _require_native_app(app)
    fig_html = figure_html(fig, target="body")
    return await app.render_template(
        template,
        HEAD_TEMPLATE_VARIABLE_NAME=lambda core=False: head_content(core=core),
        fig=fig_html,
    )


globals().update(
    mk_figure_page_variants(
        suffix="",
        generate_html=figure_page_html,
        response_factory=_mk_quart_response,
        kwarg_defaults=dict(template=default_figure_page_template),
        ds_response_name="Quart Response",
        ds_template_comment="a function taking and returning raw strings",
        ds_params_extra=fdf("""
    template : callable, optional
        A callable taking the raw strings `head`, `title` and `fig` as keyword
        arguments and returning the HTML template to use for rendering the
        figure page as a raw string. Will default to
        `default_figure_page_template` if not provided.
    """),
    )
)


globals().update(
    mk_figure_page_variants(
        suffix="_jinja",
        generate_html=_figure_page_html_jinja,
        response_factory=_mk_quart_response,
        ds_response_name="Quart Response",
        ds_template_comment="a Jinja template",
        ds_params_extra=fdf(f"""
    template : str
        The path to a Jinja template which will be passed the template variables
        `{HEAD_TEMPLATE_VARIABLE_NAME}` and `fig`.
    app : Quart, optional
        The Quart app to use for rendering the Jinja template. If not provided,
        the app passed to setup(...) and/or `MplbedMiddleware` will be used.
        Typically this does not need to be provided.
    """),
    )
)


def install_middleware(
    app,
    *,
    prefix=DEFAULT_PREFIX,
    mplbed_starlette_app=None,
    mplbed_starlette_app_kwargs=None,
    manage_routing=True,
):
    f"""
    Install the mplbed middleware on the given Quart app.

    Parameters
    ----------
    app : Quart
        The Quart app to install the middleware on.
    {D.prefix} 
    {D.mplbed_starlette_app()}
    {D.mplbed_starlette_app_kwargs()}
    {D.manage_routing}
    {D.native_app}
    """
    app.asgi_app = MplbedMiddleware(
        app.asgi_app,
        prefix=prefix,
        app=mplbed_starlette_app,
        app_kwargs=mplbed_starlette_app_kwargs,
        manage_routing=manage_routing,
        native_app=app,
    )


def register_context_processor(app):
    """
    Register a context processor for the given Quart app to inject head content.

    Parameters
    ----------
    app : Quart
        The Quart app to register the context processor on.
    """

    @app.context_processor
    async def inject_head_content():
        return {
            HEAD_TEMPLATE_VARIABLE_NAME: lambda core=False: head_content(core=core),
        }

    return inject_head_content


@setup_page_docstring(
    lambda p: (
        f"""
    Setup the mplbed integration for the given Quart app.
    
    This function performs all the integration steps necessary to use mplbed
    with Quart, including installing middleware, registering context processors,
    and configuring the matplotlib backend. The default parameter values are
    suitable for most use cases, but can be overridden as needed.
    
    Parameters
    ----------
    app : Quart
        The Quart app to integrate with mplbed.
    {p.do_install_middleware}
    {p.prefix}
    {p.mplbed_starlette_app}
    {p.mplbed_starlette_app_kwargs}
    {p.manage_routing}
    {p.do_register_context_processor}
    {p.do_use_mpl_backend}
    {p.use_webaggext_backend}
"""
    )
)
def setup(
    app,
    *,
    do_install_middleware=True,
    prefix=DEFAULT_PREFIX,
    mplbed_starlette_app=None,
    mplbed_starlette_app_kwargs=None,
    manage_routing=True,
    do_register_context_processor=True,
    do_use_mpl_backend=True,
    use_webaggext_backend=True,
):
    if do_install_middleware:
        install_middleware(
            app,
            prefix=prefix,
            mplbed_starlette_app=mplbed_starlette_app,
            mplbed_starlette_app_kwargs=mplbed_starlette_app_kwargs,
            manage_routing=manage_routing,
        )
    if do_register_context_processor:
        register_context_processor(app)
    if do_use_mpl_backend:
        from mplbed import webaggext

        webaggext.use(ext=use_webaggext_backend)


def iframe_for(endpoint, *, app=None, **kwargs):
    """
    Generate an iframe HTML snippet for the given Quart endpoint.

    Parameters
    ----------
    endpoint : str
        The name of the Quart endpoint to generate the iframe for.
    app : Quart, optional
        The Quart app to use for URL generation. If not provided, the current
        app will be used.
    **kwargs
        Additional keyword arguments to pass to `quart.url_for`.

    Returns
    -------
    str
        The HTML snippet for the iframe.
    """
    from markupsafe import Markup

    app = _require_native_app(app)
    url = app.url_for(endpoint, **kwargs)
    return Markup(
        f'<iframe src="{url}" width="100%" height="600" frameborder="0"></iframe>'
    )
