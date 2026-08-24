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


def _navigation_plot(*, captured: bool, plot_class: str):
    plot = matplotlib(
        figsize=(4, 3),
        prevent_default_navigation=captured,
    ).classes(plot_class)
    axes = plot.figure.subplots()
    axes.plot([1, 2, 3], [1, 2, 3])
    event_count = 0

    def update_on_input(event) -> None:
        nonlocal event_count
        event_count += 1
        axes.set_title(f"Input events: {event_count}")
        plot.update()

    plot.figure.canvas.mpl_connect("key_press_event", update_on_input)
    plot.figure.canvas.mpl_connect("scroll_event", update_on_input)
    plot.update()
    return plot


@ui.page("/navigation")
def navigation() -> None:
    """Compare normal page navigation with a plot that captures it."""
    ui.html('<div style="height: 40rem">Scroll down to the plots.</div>')
    with ui.row():
        with ui.column():
            ui.label("Browser navigation enabled")
            _navigation_plot(captured=False, plot_class="navigation-default")
        with ui.column():
            ui.label("Browser navigation captured")
            _navigation_plot(captured=True, plot_class="navigation-captured")
    ui.html('<div style="height: 80rem">Page content after the plots.</div>')


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8080)), reload=False, show=False)
