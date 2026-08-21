# Starlette

The starlette integration is typically imported as `from mplbed import mplbed_starlette` (although is also available as `mplbed.integration.starlette`).

To display a figure at a particular route

```python
import starlette
from starlette.applications import Starlette
from starlette.routing import Route

from mplbed import mplbed_starlette

@mplbed_starlette.figure_page
def figure(request):
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [4, 5, 6])
    return fig

app = mywebframework.App(...)
setup(app)

app = Starlette(
    debug=True,
    routes=[Route('/', figure)],
)
mplbed_starlette.setup(app)
```

The above example sets up mplbed using the `setup` function which offers several options for customization:

```{eval-rst}
.. autofunction:: mplbed.mplbed_starlette.setup
```

The figure_page helper is used as a decorator to wrap a route handler that returns a matplotlib figure.
Other ways of using it are possible:

```{eval-rst}
.. autofunction:: mplbed.mplbed_starlette.figure_page
```

## Further examples

### Single standalone figure (`draw_idle.py`)

Demonstrates `draw_idle` with an interactive keyboard event: pressing Enter
swaps the colors of two scatter plots.

```{literalinclude} ../../examples/starlette/draw_idle.py
:language: python
```

### Two embedded figures (`embed2_raw.py`)

Embeds two figures side-by-side in a single page using raw string templates.

```{literalinclude} ../../examples/starlette/embed2_raw.py
:language: python
```

### Popup figure (`demo_popup.py`)

A button on the main figure spawns a popup figure in a modal dialog.

```{literalinclude} ../../examples/starlette/demo_popup.py
:language: python
```

### Manual routing (`mount_app.py`)

Shows how to manually create the mplbed Starlette sub-app and mount it at a
custom prefix instead of using `setup()`.

```{literalinclude} ../../examples/starlette/mount_app.py
:language: python
```

### MNE integration (`integrate_mne.py`)

Embeds an interactive MNE raw-data plot in a Starlette page.

```{literalinclude} ../../examples/starlette/integrate_mne.py
:language: python
```
