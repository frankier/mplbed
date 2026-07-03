"""
Shows inline figures, external figures and popups using mplbed/Quart/jinja2.
"""

from quart import Quart, render_template
from mplbed import mplbed_quart
from mplbed import safe_html


app = Quart(__name__)
mplbed_quart.setup(app)


def mk_plot():
    import matplotlib.pyplot as plt
    import numpy as np

    t = np.arange(0.0, 2 * np.pi, 0.01)
    s = np.sin(t)

    fig, ax = plt.subplots()
    ax.plot(t, s)

    return fig


@app.route('/')
async def index():
    return await render_template(
        "index.html",
        inline_fig=safe_html.figure_html(mk_plot()),
        external_iframe=mplbed_quart.iframe_for("figure"),
        open_inline_popup=safe_html.figure_html(mk_plot(), target="modal")
    )


@app.route('/figure')
async def figure():
    return mplbed_quart.figure_standalone(mk_plot())


if __name__ == "__main__":
    import os
    app.run(debug=True, port=int(os.environ.get("PORT", 8000)))