from mplbed.asgi import url_path_for


def figure_html_from_id(
    fig_id,
    *,
    target="inline",
    on_close="msg_discrete",
    prefix_and_app=None,
    prevent_default_navigation=False,
):
    """Generate embeddable HTML for an existing figure manager.

    Parameters
    ----------
    fig_id
        The registered Matplotlib figure-manager identifier.
    target
        Where to create the figure: ``"inline"``, ``"body"``, or ``"modal"``.
    on_close
        Browser behavior to use when the figure WebSocket closes.
    prefix_and_app
        Optional explicit mplbed URL prefix and ASGI application pair.
    prevent_default_navigation
        Prevent browser scrolling for wheel, Arrow, PageUp/PageDown, Home/End,
        and Space events while still forwarding them to Matplotlib.

    Returns
    -------
    str
        The figure's HTML container and setup script.
    """
    from json import dumps

    ws_uri = url_path_for("websocket", fig_id=fig_id, _prefix_and_app=prefix_and_app)
    ws_uri_str = dumps(ws_uri)
    download_fig_uri = url_path_for("download_fig", fig_id=fig_id, fmt="{fmt}", _prefix_and_app=prefix_and_app)
    download_fig_uri_str = dumps(download_fig_uri)
    container = ""
    setup_container = ""
    if target == "inline":
        container = "<div></div>"
        target_js = "document.currentScript.previousElementSibling"
    elif target == "body":
        target_js = "document.body"
    elif target == "modal":
        container = """
            <dialog closedby="any" style="padding: 1em; margin: 0 auto;"></dialog>
            """.strip()
        target_js = "document.currentScript.previousElementSibling"
        setup_container = """
            _mpl_webaggext.mk_modal(document.currentScript.previousElementSibling, fig);
            """.strip()
    else:
        raise ValueError(f"Invalid target: {target}")
    if on_close == "remove_dialog":
        on_close = ["remove_parent", "dialog"]
    on_close_js = dumps(on_close)
    prevent_default_navigation_js = dumps(prevent_default_navigation)
    create_figure = f"""
    let fig = _mpl_webaggext.new_fig(
        {target_js},
        {fig_id},
        {ws_uri_str},
        {download_fig_uri_str},
        {on_close_js},
        {prevent_default_navigation_js}
    );
    """.strip()
    bits = (
        container,
        """
        <script>
        (function() {
        """.strip(),
        create_figure,
        setup_container,
        """
        })();
        </script>
        """.strip(),
    )
    return "\n".join(bits)


def figure_html(
    figure,
    *retains,
    target="inline",
    on_close="msg_discrete",
    prevent_default_navigation=False,
):
    """Register and generate embeddable HTML for a Matplotlib figure.

    Parameters
    ----------
    figure
        The Matplotlib figure to embed.
    *retains
        Objects to keep alive with the figure manager.
    target
        Where to create the figure: ``"inline"``, ``"body"``, or ``"modal"``.
    on_close
        Browser behavior to use when the figure WebSocket closes.
    prevent_default_navigation
        Prevent browser scrolling for wheel, Arrow, PageUp/PageDown, Home/End,
        and Space events while still forwarding them to Matplotlib.

    Returns
    -------
    str
        The figure's HTML container and setup script.
    """
    from matplotlib.pyplot import _get_backend_mod as get_backend_mod

    from mplbed.server._impl import add_manager

    manager = get_backend_mod().new_figure_manager_given_figure(id(figure), figure)
    if hasattr(manager, "add_retains"):
        manager.add_retains(*retains)  # ty: ignore
    else:
        if not hasattr(figure, "_retains"):
            figure._retains = []
        figure._retains.extend(retains)
    add_manager(manager)
    return figure_html_from_id(
        manager.num,
        target=target,
        on_close=on_close,
        prevent_default_navigation=prevent_default_navigation,
    )


def default_figure_page_template(*, head, fig, title):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    {head}
    <title>{title}</title>
</head>
<body>
    {fig}
</body>
</html>
"""


_template_preview = default_figure_page_template(head="{head}", fig="{fig}", title="{title}")
_indented = "\n".join("    " + line for line in _template_preview.splitlines())
default_figure_page_template.__doc__ = (
    "Applies the following template to the given ``head``, ``fig`` and ``title``:\n\n"
    ".. code-block:: html\n\n" + _indented + "\n"
)
del _template_preview, _indented


def head_content(*, core=False, prefix_and_app=None):
    css_files = []
    if not core:
        css_files.extend(["page", "boilerplate", "fbm"])
    css_files.append("mpl")
    head_bits = []
    for css_file in css_files:
        static_url = url_path_for("static", path=f"css/{css_file}.css", _prefix_and_app=prefix_and_app)
        head_bits.append(
            f"""
                <link rel="stylesheet" href="{static_url}" type="text/css">
            """.strip()
        )
    mpl_js_uri = url_path_for("mpl_js", _prefix_and_app=prefix_and_app)
    head_bits.append(
        f"""
        <script src="{mpl_js_uri}"></script>
    """.strip()
    )
    head_bits.append(
        """
        <style>
        .mpl-toolbar {
            position: relative;
            padding-bottom: 2em;
        }
        .mpl-message {
            position: absolute;
            left: 0;
            bottom: 0;
            white-space: nowrap;
            overflow-x: auto;
            width: 100%;
        }
        .mpl-figure-root {
            display: inline-flex !important;
            flex-direction: column;
        }
        </style>
    """.strip()
    )
    return "\n".join(head_bits)


def figure_page_html(
    fig,
    *,
    template=default_figure_page_template,
    prevent_default_navigation=False,
):
    """Generate a complete HTML page containing a Matplotlib figure.

    Parameters
    ----------
    fig
        The Matplotlib figure to embed.
    template
        A callable receiving the ``head``, ``title``, and ``fig`` HTML strings.
    prevent_default_navigation
        Prevent browser scrolling for wheel, Arrow, PageUp/PageDown, Home/End,
        and Space events while still forwarding them to Matplotlib.

    Returns
    -------
    str
        A complete HTML page.
    """
    fig_html = figure_html(
        fig,
        target="body",
        prevent_default_navigation=prevent_default_navigation,
    )
    head = head_content(core=True)
    resp_html = template(head=head, title="figure", fig=fig_html)
    return resp_html
