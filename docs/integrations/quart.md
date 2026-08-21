# Quart

The Quart integration is typically imported as `from mplbed import mplbed_quart`
(although it is also available as `mplbed.integration.quart`).

To display a figure at a particular route:

```python
import matplotlib.pyplot as plt
from quart import Quart

from mplbed import mplbed_quart


app = Quart(__name__)
mplbed_quart.setup(app)


@app.route("/figure")
@mplbed_quart.figure_page
async def figure():
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [4, 5, 6])
    return fig
```

The `setup` function installs the mplbed middleware, registers the template
context processor, and selects the interactive Matplotlib backend:

```{eval-rst}
.. autofunction:: mplbed.mplbed_quart.setup
```

The `figure_page` helper wraps a route handler that returns a Matplotlib figure
in a Quart `Response`:

```{eval-rst}
.. autofunction:: mplbed.mplbed_quart.figure_page
```

For a figure page rendered with a Jinja template, use `figure_page_jinja`. The
template receives `mplbed_head` and `fig`:

```{eval-rst}
.. autofunction:: mplbed.mplbed_quart.figure_page_jinja
```

`iframe_for` creates an iframe for a named Quart endpoint:

```{eval-rst}
.. autofunction:: mplbed.mplbed_quart.iframe_for
```

## Further examples

### Inline, iframe, and popup figures (`basic.py`)

Shows three embedding styles in a single Quart/Jinja app: an inline figure, a
figure loaded inside an iframe, and a figure opened in a modal popup.

```{literalinclude} ../../examples/quart/basic.py
:language: python
```

The Jinja templates used by the example:

**`templates/base.html`**

```{literalinclude} ../../examples/quart/templates/base.html
:language: html
```

**`templates/index.html`**

```{literalinclude} ../../examples/quart/templates/index.html
:language: html
```
