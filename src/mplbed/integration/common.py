from functools import wraps
import inspect


def figure_standalone_docstring_factory(*, response_name, template_comment, is_async, params_extra):
    async_str = "async " if is_async else ""
    await_str = "await " if is_async else ""
    return f"""
    Create a {response_name} object containing the HTML for the given figure using {template_comment}.

    Example
    -------

    {async_str}def my_handler(request):
        fig = Figure()
        return {await_str}figure_page(fig)

    Parameters
    ----------
    fig : matplotlib.figure.Figure or callable
        A matplotlib Figure object or a callable that returns a Figure object.
    {params_extra}
    """


def figure_page_docstring_factory(*, response_name, template_comment, is_generic, wraps, params_extra):
    async_str = "(async) " if is_generic else ""
    await_str = "(await) " if is_generic else ""
    generic_note = "All usages are generic with regards to async/sync" if is_generic else ""
    return f"""
    Decorator to create a {response_name} object containing the HTML for the given figure using {template_comment}.

    This function can be called in two ways:
    
    1. As a decorator for a function taking any number of arguments and
       returning a matplotlib Figure object, making it appropriate to use as a
       decorator for view/handler function.
    2. As a decorator for a function taking no arguments and returning a
       matplotlib Figure object, making it appropriate to use as a decorator for a
       figure closure within a view/handler.
    
    {generic_note}

    Internally this decorator uses the function {wraps} to generate the HTML and create the {response_name}.

    Example
    -------

    # Usage 1
    @figure_page
    {async_str} def my_handler(request):
        return Figure()
    
    # Usage 2
    {async_str} def my_handler(request):
        # ...
        @figure_page
        {async_str} def create_figure():
            return Figure()
        return {await_str} create_figure()

    Parameters
    ----------
    {params_extra}
    """


def _has_parameters(func):
    return len(inspect.signature(func).parameters) > 0


def figure_standalone_factory(
    name,
    generate_html,
    response_factory,
    *,
    kwarg_defaults=None,
    response_factory_kwarg_keys=(),
    make_async=None,
    ds_response_name="response",
    ds_template_comment="a template",
    ds_params_extra,
):
    need_async = inspect.iscoroutinefunction(generate_html) or inspect.iscoroutinefunction(response_factory)
    if make_async is None:
        make_async = need_async
    if need_async and not make_async:
        raise ValueError("generate_html or response_factory is async, but make_async is False. Set make_async to True to allow async usage.")
    def process_kwargs(kwargs):
        kwargs = {**(kwarg_defaults or {}), **kwargs}
        response_factory_kwargs = {}
        for k in response_factory_kwarg_keys:
            if k in kwargs:
                response_factory_kwargs[k] = kwargs.pop(k)
        return kwargs, response_factory_kwargs
    if make_async:
        async def figure_standalone(fig, **kwargs):
            generate_html_kwargs, response_factory_kwargs = process_kwargs(kwargs)
            if inspect.iscoroutinefunction(generate_html):
                html = await generate_html(fig, **generate_html_kwargs)
            else:
                html = generate_html(fig, **generate_html_kwargs)
            if inspect.iscoroutinefunction(response_factory):
                return await response_factory(html, **response_factory_kwargs)
            else:
                return response_factory(html, **response_factory_kwargs)
    else:
        def figure_standalone(fig, **kwargs):
            generate_html_kwargs, response_factory_kwargs = process_kwargs(kwargs)
            return response_factory(generate_html(fig, **generate_html_kwargs), **response_factory_kwargs)
    figure_standalone.__name__ = name
    figure_standalone.__doc__ = figure_standalone_docstring_factory(
        response_name=ds_response_name,
        template_comment=ds_template_comment,
        is_async=make_async,
        params_extra=ds_params_extra
    )
    return figure_standalone


def figure_page_factory(
    name,
    figure_standalone,
    *,
    ds_response_name="response",
    ds_template_comment="a template",
    ds_params_extra,
):
    needs_async = inspect.iscoroutinefunction(figure_standalone)
    def figure_page(inner, **figure_page_kwargs):
        if inspect.iscoroutinefunction(inner):
            if _has_parameters(inner):
                # Async view style figure creating function
                @wraps(inner)
                async def wrapper(*args, **kwargs):
                    actual_fig = await inner(*args, **kwargs)
                    figure_standalone_kwargs = kwargs.pop("figure_standalone_kwargs", {})
                    if needs_async:
                        return await figure_standalone(actual_fig, **{**figure_page_kwargs, **figure_standalone_kwargs})
                    else:
                        return figure_standalone(actual_fig, **{**figure_page_kwargs, **figure_standalone_kwargs})
            else:
                # Async closure style figure creating function
                @wraps(inner)
                async def wrapper(*, figure_standalone_kwargs=()):
                    actual_fig = await inner()
                    if needs_async:
                        return await figure_standalone(actual_fig, **{**figure_page_kwargs, **figure_standalone_kwargs})
                    else:
                        return figure_standalone(actual_fig, **{**figure_page_kwargs, **figure_standalone_kwargs})

        else:
            if needs_async:
                raise ValueError(f"Decorated function must be async for {name} (wrapping {figure_standalone.__name__})")
            if _has_parameters(inner):
                # View style figure creating function
                @wraps(inner)
                def wrapper(*args, **kwargs):
                    actual_fig = figure_standalone(*args, **kwargs)
                    figure_standalone_kwargs = kwargs.pop("figure_standalone_kwargs", {})
                    return figure_page(actual_fig, **{**figure_page_kwargs, **figure_standalone_kwargs})
            else:
                # Closure style figure creating function
                @wraps(inner)
                def wrapper(*, figure_standalone_kwargs=()):
                    actual_fig = figure_standalone()
                    return figure_page(actual_fig, **{**figure_page_kwargs, **figure_standalone_kwargs})

        wrapper.__name__ = name
        return wrapper
    figure_page.__doc__ = figure_page_docstring_factory(
        response_name=ds_response_name,
        template_comment=ds_template_comment,
        wraps=figure_standalone.__name__,
        is_generic=not needs_async,
        params_extra=ds_params_extra
    )
    return figure_page


def mk_figure_page_variants(
    suffix,
    generate_html,
    response_factory,
    *,
    kwarg_defaults=None,
    response_factory_kwarg_keys=(),
    ds_response_name="response",
    ds_template_comment="a template",
    ds_params_extra
):
    need_async = inspect.iscoroutinefunction(generate_html) or inspect.iscoroutinefunction(response_factory)
    results = {}
    standalone_args = dict(
        generate_html=generate_html,
        response_factory=response_factory,
        kwarg_defaults=kwarg_defaults,
        response_factory_kwarg_keys=response_factory_kwarg_keys,
        ds_response_name=ds_response_name,
        ds_template_comment=ds_template_comment,
        ds_params_extra=ds_params_extra
    )
    page_args = dict(
        ds_response_name=ds_response_name,
        ds_template_comment=ds_template_comment,
        ds_params_extra=ds_params_extra
    )
    if need_async:
        figure_standalone = figure_standalone_factory(
            f"figure_standalone{suffix}",
            **standalone_args,
            make_async=True
        )
        results[f"figure_standalone{suffix}"] = figure_standalone 
        results[f"figure_page{suffix}"] = figure_page_factory(
            f"figure_page{suffix}",
            figure_standalone,
            **page_args
        )
    else:
        figure_standalone = figure_standalone_factory(
            f"figure_standalone{suffix}",
            **standalone_args,
            make_async=False,
        )
        results[f"figure_standalone{suffix}"] = figure_standalone 
        results[f"figure_page{suffix}"] = figure_page_factory(
            f"figure_page{suffix}",
            figure_standalone,
            **page_args
        )
        figure_standalone_async = figure_standalone_factory(
            f"figure_standalone{suffix}_async",
            **standalone_args,
            make_async=True
        )
        results[f"figure_standalone{suffix}_async"] = figure_standalone_async
        results[f"figure_page{suffix}_async"] = figure_page_factory(
            f"figure_page{suffix}_async",
            figure_standalone_async,
            **page_args
        )
    return results


def setup_page_docstring(template_func):
    from mplbed.doc_helpers import fdf, PARAMS_DS, DotAccessDict

    def decorator(wrapped):
        wrapped.__doc__ = template_func(DotAccessDict(
            **PARAMS_DS,
            do_install_middleware=fdf("""
            do_install_middleware : bool, optional
                Whether to install the mplbed middleware on the given app. Default is True.
            """),
            do_register_context_processor=fdf("""
            do_register_context_processor : bool, optional
                Whether to register the mplbed context processor on the given app. Default is True.
            """),
            do_use_mpl_backend=fdf("""
            do_use_mpl_backend : bool, optional
                Whether to setup the matplotlib backend for rendering figures. Default is True.
            """),
            use_webaggext_backend=fdf("""
            use_webaggext_backend : bool, optional
                Whether to use webaggext rather than the basic webagg backend for rendering figures. Default is True.
            """)
        ))
        return wrapped
    return decorator