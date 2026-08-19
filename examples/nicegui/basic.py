"""Shows two independently updating interactive mplbed figures in NiceGUI."""

import os

from nicegui import app, ui

from mplbed.integration.nicegui import matplotlib, setup

setup(app)


@ui.page("/")
def index() -> None:
    """Create a fresh pair of figures for each NiceGUI client."""
    with ui.row():
        with ui.column():
            first_plot = matplotlib(figsize=(4, 3)).classes("plot-one")
            with first_plot.figure as first_figure:
                first_axes = first_figure.subplots()
                (first_line,) = first_axes.plot([1, 2, 3], [1, 2, 3])

            def update_first() -> None:
                first_line.set_ydata([3, 1, 2])
                first_plot.update()

            ui.button("Update first", on_click=update_first)
            ui.button("Delete first", on_click=first_plot.delete)

        with ui.column():
            second_plot = matplotlib(figsize=(4, 3)).classes("plot-two")
            with second_plot.figure as second_figure:
                second_axes = second_figure.subplots()
                second_axes.plot([1, 2, 3], [2, 3, 1])


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8080)), reload=False, show=False)
