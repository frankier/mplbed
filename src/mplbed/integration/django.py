from mplbed._doc_helpers import PARAMS_DS as D
from mplbed._doc_helpers import doc, fdf
from mplbed.asgi import MplbedMiddleware
from mplbed.consts import DEFAULT_PREFIX, HEAD_TEMPLATE_VARIABLE_NAME
from mplbed.html._impl import default_figure_page_template, figure_page_html
from mplbed.html.safe import head_content
from mplbed.integration._common import mk_figure_page_variants, setup_page_docstring

try:
    import django  # noqa: F401 (existence check, submodules are imported lazily)
except ModuleNotFoundError as e:
    e.add_note(
        "The mplbed Django integration requires the Django package. Please install it with `pip install django`."
    )
    raise


def _mk_django_response(html):
    from django.http import HttpResponse

    return HttpResponse(html)


def _figure_page_html_dtl(fig, *, template, prevent_default_navigation=False):
    from django.template.loader import render_to_string

    from mplbed.html.safe import figure_html

    fig_html = figure_html(
        fig,
        target="body",
        prevent_default_navigation=prevent_default_navigation,
    )
    return render_to_string(
        template,
        {
            HEAD_TEMPLATE_VARIABLE_NAME: head_content(core=False),
            "fig": fig_html,
        },
    )


globals().update(
    mk_figure_page_variants(
        suffix="",
        generate_html=figure_page_html,
        response_factory=_mk_django_response,
        kwarg_defaults=dict(template=default_figure_page_template),
        ds_response_name="Django HttpResponse",
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
        suffix="_dtl",
        generate_html=_figure_page_html_dtl,
        response_factory=_mk_django_response,
        ds_response_name="Django HttpResponse",
        ds_template_comment="a Django template",
        ds_params_extra=fdf(f"""
    template : str
        The name of a Django template which will be passed the template
        variables `{HEAD_TEMPLATE_VARIABLE_NAME}` and `fig`.
    """),
    )
)


@doc(
    f"""
    Install the mplbed middleware on the given Django ASGI application.

    This is intended to be used in your project's ``asgi.py``, wrapping the
    application returned by `django.core.asgi.get_asgi_application`, as
    described in the Django documentation for
    `deploying with ASGI <https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/>`_.

    Parameters
    ----------
    application : ASGI3Application, optional
        The Django ASGI application to install the middleware on, e.g. the
        result of `django.core.asgi.get_asgi_application`. If not provided it
        will be fetched via `get_asgi_application`, which requires
        ``DJANGO_SETTINGS_MODULE`` to be set in the environment.

    Returns
    -------
    ASGI3Application
        The wrapped application, ready to be assigned to ``application`` in
        your ``asgi.py``.

    Other Parameters
    ----------------
    {D.prefix}
    {D.mplbed_starlette_app()}
    {D.mplbed_starlette_app_kwargs()}
    {D.manage_routing}
    """
)
def install_middleware(
    application=None,
    *,
    prefix=DEFAULT_PREFIX,
    mplbed_starlette_app=None,
    mplbed_starlette_app_kwargs=None,
    manage_routing=True,
):
    if application is None:
        from django.core.asgi import get_asgi_application

        application = get_asgi_application()
    return MplbedMiddleware(
        application,
        prefix=prefix,
        app=mplbed_starlette_app,
        app_kwargs=mplbed_starlette_app_kwargs,
        manage_routing=manage_routing,
        native_app=application,
    )


def context_processor(request):
    """Return the mplbed head content as a context processor.

    Add this function to the ``context_processors`` option of your template
    backend settings to make the template variable `mplbed_head` available in
    all templates.

    Parameters
    ----------
    request : django.http.HttpRequest
        The request being processed.

    Returns
    -------
    dict
        A dict setting the `mplbed_head` template variable to the head content
        as a markup-safe string.

    """
    return {
        HEAD_TEMPLATE_VARIABLE_NAME: head_content(core=False),
    }


@setup_page_docstring(
    lambda p: (
        f"""
    Setup the mplbed integration for a Django ASGI application.

    This function performs all the integration steps necessary to use mplbed
    with Django, including installing middleware and configuring the
    matplotlib backend. The default parameter values are suitable for most
    use cases, but can be overridden as needed.

    Unlike the other integrations, the wrapped application is returned rather
    than mutated, so that it can be exported from your ``asgi.py``, e.g.::

        application = mplbed_django.setup(get_asgi_application())

    Parameters
    ----------
    application : ASGI3Application, optional
        The Django ASGI application to integrate with mplbed, e.g. the result
        of `django.core.asgi.get_asgi_application`. If not provided it will
        be fetched via `get_asgi_application`, which requires
        ``DJANGO_SETTINGS_MODULE`` to be set in the environment.
    {p.do_install_middleware}
    {p.prefix}
    {p.mplbed_starlette_app()}
    {p.mplbed_starlette_app_kwargs()}
    {p.manage_routing}
    {p.do_use_mpl_backend}
    {p.use_webaggext_backend}
"""
    )
)
def setup(
    application=None,
    *,
    do_install_middleware=True,
    prefix=DEFAULT_PREFIX,
    mplbed_starlette_app=None,
    mplbed_starlette_app_kwargs=None,
    manage_routing=True,
    do_use_mpl_backend=True,
    use_webaggext_backend=True,
):
    if do_install_middleware:
        application = install_middleware(
            application,
            prefix=prefix,
            mplbed_starlette_app=mplbed_starlette_app,
            mplbed_starlette_app_kwargs=mplbed_starlette_app_kwargs,
            manage_routing=manage_routing,
        )
    if do_use_mpl_backend:
        from mplbed import webaggext

        webaggext.use(ext=use_webaggext_backend)
    return application


def iframe_for(endpoint, **kwargs):
    """Generate an iframe HTML snippet for the given Django URL name.

    Parameters
    ----------
    endpoint : str
        The name of the Django URL to generate the iframe for.
    **kwargs
        Additional keyword arguments to pass to `django.urls.reverse`.

    Returns
    -------
    markupsafe.Markup
        The HTML snippet for the iframe.

    """
    from django.urls import reverse
    from markupsafe import Markup

    url = reverse(endpoint, **kwargs)
    return Markup(f'<iframe src="{url}" width="100%" height="600" frameborder="0"></iframe>')


# ruff: disable[F822]
__all__ = [
    "install_middleware",
    "context_processor",
    "setup",
    "figure_standalone",
    "figure_standalone_async",
    "figure_standalone_jinja",
    "figure_page",
    "figure_page_async",
    "figure_page_jinja",
    "iframe_for",
]
# ruff: enable[F822]
