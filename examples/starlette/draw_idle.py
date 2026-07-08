"""
Shows draw_idle(...) working with webagg and webaggext --- pressing enter swaps the
colors of the two scatter plots.

Flags: USE_BASIC_WEBAGG_BACKEND
"""
import os
from matplotlib import pyplot as plt

from starlette.applications import Starlette
from starlette.routing import Route

from mplbed import mplbed_starlette


use_basic_webagg_backend = "USE_BASIC_WEBAGG_BACKEND" in os.environ


def page(request):
    fig, (ax1, ax2) = plt.subplots(nrows=2)

    x = [0, 1, 2]

    coll1 = ax1.scatter(x, x, c=["r", "g", "b"])
    coll2 = ax2.scatter(x, x, c=["b", "g", "r"])

    def accept(event):
        match event.key:
            case "enter":
                # swap facecolors
                fc1 = coll1.get_facecolors()
                fc2 = coll2.get_facecolors()
                coll1.set_facecolors(fc2)
                coll2.set_facecolors(fc1)
                fig.canvas.draw_idle()
            case _:
                pass

    fig.canvas.mpl_connect("key_press_event", accept)
    return mplbed_starlette.figure_standalone(fig)


app = Starlette(
    debug=True,
    routes=[Route('/', page)],
)
mplbed_starlette.setup(app, use_webaggext_backend=not use_basic_webagg_backend)
