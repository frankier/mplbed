"""
Shows manual creation and routing of the `mplbed` Starlette app.
"""
from matplotlib.figure import Figure

from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route, Mount

from mplbed import raw_html, mplbed_starlette, mplbed_app_factory


def homepage_template(*, head, fig1):
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    {head}
    <title>Sine wave plot</title>
  </head>

  <body>
    <h2>Sine wave plot</h2>
    {fig1}
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
    return Response(
        homepage_template(
            head=raw_html.head_content(),
            fig1=raw_html.figure_html(fig1),
        ),
        media_type='text/html'
    )


mplbed_app = mplbed_app_factory()
MPLBED_PREFIX = "/mymplbedprefix"
app = Starlette(
    debug=True,
    routes=[Route('/', homepage), Mount(MPLBED_PREFIX, app=mplbed_app, name="webagg")],
)
mplbed_starlette.setup(app, prefix=MPLBED_PREFIX, mplbed_starlette_app=mplbed_app, manage_routing=False)