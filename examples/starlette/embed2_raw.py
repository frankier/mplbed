"""
Creates two embedded figures using raw string templates using Starlette/mplbed/string formatting.
"""
from matplotlib.figure import Figure

from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route

from mplbed import mplbed_starlette, raw_html


def homepage_template(*, head, fig1, fig2):
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    {head}
    <title>matplotlib</title>
  </head>

  <body>
    <div style="display: flex">
      <div>
        <h2>Figure 1</h2>
        {fig1}
      </div>
      <div>
        <h2>Figure 2</h2>
        {fig2}
      </div>
    </div>
  </body>
</html>
"""


def create_figure():
    import numpy as np
    fig = Figure()
    ax = fig.add_subplot()
    t = np.arange(0.0, 3.0, 0.01)
    s = np.sin(2 * np.pi * t)
    ax.plot(t, s)
    return fig


def homepage(request):
    fig1 = create_figure()
    fig2 = create_figure()
    return Response(
        homepage_template(
            head=raw_html.head_content(),
            fig1=raw_html.figure_html(fig1),
            fig2=raw_html.figure_html(fig2),
        ),
        media_type='text/html'
    )


app = Starlette(
    debug=True,
    routes=[Route('/', homepage)],
)
mplbed_starlette.setup(app)
