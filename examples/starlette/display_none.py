"""Hide and show a scatter plot by toggling ``display: none`` on its parent."""

from matplotlib.figure import Figure
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route

from mplbed import mplbed_starlette, raw_html


def homepage(request):
    """Render a scatter plot inside a parent with optional initial hiding."""
    fig = Figure()
    ax = fig.add_subplot()
    ax.scatter([1, 2, 3], [1, 4, 2], color="red", s=200)
    initially_hidden = "initially-hidden" in request.query_params
    hidden_after_init = "hidden-after-init" in request.query_params
    fit = request.query_params.get("fit", "none")
    resize_handle = request.query_params.get("resize_handle")
    if resize_handle is not None:
        resize_handle = resize_handle == "true"
    styles = ["display: none"] if initially_hidden else []
    if fit != "none":
        styles.append("width: 600px")
    if fit == "container":
        styles.append("height: 400px")
    parent_style = f' style="{"; ".join(styles)}"' if styles else ""
    button_label = "Show plot" if initially_hidden or hidden_after_init else "Hide plot"
    hide_after_init = (
        '<script>document.getElementById("plot-parent").style.display = "none";</script>'
        if hidden_after_init
        else ""
    )

    return Response(
        f"""<!DOCTYPE html>
<html lang="en">
  <head>
    {raw_html.head_content()}
    <title>Toggle a plot</title>
  </head>
  <body>
    <button id="toggle-plot" type="button">{button_label}</button>
    <div id="plot-parent"{parent_style}>
      {raw_html.figure_html(fig, fit=fit, resize_handle=resize_handle)}
    </div>
    {hide_after_init}
    <script>
      const button = document.getElementById("toggle-plot");
      const parent = document.getElementById("plot-parent");
      button.addEventListener("click", () => {{
        const hidden = parent.style.display === "none";
        parent.style.display = hidden ? "block" : "none";
        button.textContent = hidden ? "Hide plot" : "Show plot";
      }});
    </script>
  </body>
</html>
""",
        media_type="text/html",
    )


app = Starlette(debug=True, routes=[Route("/", homepage)])
mplbed_starlette.setup(app)
