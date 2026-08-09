"""
Shows inline figures, external figures and popups using mplbed/Django.
"""

from django.shortcuts import render

from mplbed import mplbed_django
from mplbed import safe_html


def mk_plot():
    import matplotlib.pyplot as plt
    import numpy as np

    t = np.arange(0.0, 2 * np.pi, 0.01)
    s = np.sin(t)

    fig, ax = plt.subplots()
    ax.plot(t, s)

    return fig


def index(request):
    return render(
        request,
        "index.html",
        {
            "inline_fig": safe_html.figure_html(mk_plot()),
            "external_iframe": mplbed_django.iframe_for("figure"),
            "open_inline_popup": safe_html.figure_html(mk_plot(), target="modal"),
        },
    )


@mplbed_django.figure_page
def figure(request):
    return mk_plot()


@mplbed_django.figure_page_dtl(template="figure.html")
def figure_dtl(request):
    return mk_plot()
