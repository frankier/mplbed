from starlette.templating import Jinja2Templates
from starlette.responses import Response

from mplbed.asgi import MplbedMiddleware
from mplbed.consts import DEFAULT_PREFIX, HEAD_TEMPLATE_VARIABLE_NAME
from mplbed.doc_helpers import PARAMS_DS as D, fdf
from mplbed.html.impl import default_figure_page_template, figure_page_html
from mplbed.html.safe import head_content
from mplbed.integration.common import mk_figure_page_variants, setup_page_docstring


def _mk_starlette_response(html):
    return Response(html, media_type="text/html")


def _require_native_app(app=None):
    if app is None:
        from mplbed.asgi import get_native_app

        app = get_native_app()
        if app is None:
            raise RuntimeError(
                "No current app found. Please provide a Starlette app or ensure that the MplbedMiddleware is installed."
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
        response_factory=_mk_starlette_response,
        kwarg_defaults=dict(template=default_figure_page_template),
        ds_response_name="Starlette Response",
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
        response_factory=_mk_starlette_response,
        ds_response_name="Starlette Response",
        ds_template_comment="a Jinja template",
        ds_params_extra=fdf(f"""
    template : str
        The path to a Jinja template which will be passed the template variables
        `{HEAD_TEMPLATE_VARIABLE_NAME}` and `fig`.
    app : Starlette, optional
        The Starlette app to use for rendering the Jinja template. If not provided,
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
    Install the mplbed middleware on the given Starlette app.

    Parameters
    ----------
    app : Starlette
        The Starlette app to install the middleware on.
    {D.prefix}
    {D.mplbed_starlette_app()}
    {D.mplbed_starlette_app_kwargs()}
    {D.manage_routing}
    """
    app.add_middleware(
        MplbedMiddleware,
        prefix=prefix,
        app=mplbed_starlette_app,
        app_kwargs=mplbed_starlette_app_kwargs,
        manage_routing=manage_routing,
        native_app=app,
    )


def register_context_processor(templates: Jinja2Templates):
    """
    Register a context processor for the given Starlette Jinja2Templates instance to inject head content.

    Parameters
    ----------
    templates : Jinja2Templates
        The Jinja2Templates instance to register the context processor on.
    """

    def inject_head_content(request):
        return {
            HEAD_TEMPLATE_VARIABLE_NAME: lambda core=False: head_content(core=core),
        }

    templates.context_processors.append(inject_head_content)


@setup_page_docstring(
    lambda p: (
        f"""
    Setup the mplbed integration for the given Starlette app.
    
    This function performs all the integration steps necessary to use mplbed
    with Starlette, including installing middleware, registering context processors,
    and configuring the matplotlib backend. The default parameter values are
    suitable for most use cases, but can be overridden as needed.
    
    Parameters
    ----------
    app : Starlette
        The Starlette app to integrate with mplbed.
    templates : Jinja2Templates | None, optional
        The Jinja2Templates instance to use for rendering templates. If None, no
        context processor will be registered. Default is None.
    {p.do_install_middleware}
    {p.prefix}
    {p.mplbed_starlette_app}
    {p.mplbed_starlette_app_kwargs}
    {p.manage_routing}
    do_register_context_processor : bool, optional
        Whether to register the mplbed context processor on the given app. By
        default this will be true when the `templates` parameter is set to a
        Jinja2Templates instance.
    {p.do_use_mpl_backend}
    {p.use_webaggext_backend}
"""
    )
)
def setup(
    app,
    *,
    templates: Jinja2Templates | None = None,
    do_install_middleware=True,
    prefix=DEFAULT_PREFIX,
    mplbed_starlette_app=None,
    mplbed_starlette_app_kwargs=None,
    manage_routing=True,
    do_register_context_processor=None,
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
    if not (isinstance(templates, Jinja2Templates) or templates is None):
        raise ValueError("templates must be None or a Jinja2Templates instance")
    if do_register_context_processor is None:
        do_register_context_processor = templates is not None
    if do_register_context_processor:
        register_context_processor(templates)
    if do_use_mpl_backend:
        from mplbed import webaggext

        webaggext.use(ext=use_webaggext_backend)
