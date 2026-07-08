"""
Creates a figures which spawns a popup figure when a button is pressed.

Flags: REUSE_POPUP
"""
import os
from matplotlib import pyplot as plt

from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route

from mplbed import raw_html
from mplbed.integration.starlette import setup


reuse_popup = "REUSE_POPUP" in os.environ


def homepage_template(*, head, fig):
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    {head}
    <title>matplotlib</title>
  </head>

  <body>
    <div style="display: flex">
      <div>
        <h2>Figure</h2>
        {fig}
      </div>
    </div>
  </body>
</html>
"""


class PopupDemoMpl:
    def __init__(self):
        from matplotlib.widgets import Button
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot()
        self.button = Button(self.ax, "Create popup global")
        self.button.on_clicked(self.create_popup)
        self.popup_fig = None

    def create_popup(self, event):
        if not reuse_popup or self.popup_fig is None:
            self.popup_fig = plt.figure()
            ax = self.popup_fig.add_axes((0.01, 0.01, 0.98, 0.98))
            ax.set_axis_off()
            ax.text(0.42, 0.5, "Hello from the popup", ma="left", ha="left")
        self.popup_fig.show()

    def into_html(self):
        return raw_html.figure_html(self.fig, self)


def homepage(request):
    demo = PopupDemoMpl()
    return Response(
        homepage_template(
            head=raw_html.head_content(),
            fig=demo.into_html()
        ),
        media_type='text/html'
    )


app = Starlette(
    debug=True,
    routes=[Route('/', homepage)],
)
setup(app)
