# Examples index

All examples live under the `examples/` directory. Run them with:

```bash
uv sync -U --all-groups --all-extras
cd examples && uv run python run_example.py
```

Or directly:

```bash
# Starlette (via daphne/uvicorn)
cd examples/starlette && uv run daphne -p 8000 draw_idle:app

# Quart
cd examples/quart && uv run python basic.py

# Django (via daphne)
cd examples/django && uv run daphne -p 8000 asgi:application

# NiceGUI
uv run python examples/nicegui/basic.py
```

## NiceGUI

Install the optional integration with `uv add "mplbed[nicegui]"`. Call
`setup(app)` before `ui.run()`, then configure each element through its owned
`figure`. Calling `update()` after changing an artist redraws the live WebAgg
canvas without replacing the NiceGUI element.

### Two live figures (`basic.py`)

Creates two client-owned figures, updates one independently, and demonstrates
that standard NiceGUI classes and layout containers remain available.

```{literalinclude} ../examples/nicegui/basic.py
:language: python
```

## Starlette

### Plot inside a toggled parent (`display_none.py`)

Demonstrates hiding and showing a scatter plot by toggling `display: none` on
its parent element.

```{literalinclude} ../examples/starlette/display_none.py
:language: python
```

### Single standalone figure (`draw_idle.py`)

Demonstrates `draw_idle` with an interactive keyboard event: pressing Enter
swaps the colors of two scatter plots.

```{literalinclude} ../examples/starlette/draw_idle.py
:language: python
```

### Two embedded figures (`embed2_raw.py`)

Embeds two figures side-by-side in a single page using raw string templates.

```{literalinclude} ../examples/starlette/embed2_raw.py
:language: python
```

### Popup figure (`demo_popup.py`)

A button on the main figure spawns a popup figure in a modal dialog.

```{literalinclude} ../examples/starlette/demo_popup.py
:language: python
```

### Manual routing (`mount_app.py`)

Shows how to manually create the mplbed Starlette sub-app and mount it at a
custom prefix instead of using `setup()`.

```{literalinclude} ../examples/starlette/mount_app.py
:language: python
```

### MNE integration (`integrate_mne.py`)

Embeds an interactive MNE raw-data plot in a Starlette page.

```{literalinclude} ../examples/starlette/integrate_mne.py
:language: python
```

## Quart

### Inline, iframe, and popup figures (`basic.py`)

Shows three embedding styles in a single Quart/Jinja2 app: an inline figure,
a figure loaded inside an `<iframe>`, and a figure that opens as a modal popup.

```{literalinclude} ../examples/quart/basic.py
:language: python
```

The Jinja2 templates used by this example:

**`templates/base.html`**

```{literalinclude} ../examples/quart/templates/base.html
:language: html
```

**`templates/index.html`**

```{literalinclude} ../examples/quart/templates/index.html
:language: html
```

## Django

### Inline, iframe, and popup figures (`asgi.py` + `mysite/`)

Runs a Django project under Daphne, following the
[Django + Daphne deployment docs](https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/daphne/).
`asgi.py` wraps the Django ASGI application with the mplbed middleware, and
`mysite/views.py` embeds figures inline, inside an `<iframe>`, and as a modal
popup, as well as demonstrating the raw and Django-template figure page
decorators. Django templates get the `mplbed_head` variable from the mplbed
context processor registered in `mysite/settings.py`.

**`asgi.py`**

```{literalinclude} ../examples/django/asgi.py
:language: python
```

**`mysite/settings.py`**

```{literalinclude} ../examples/django/mysite/settings.py
:language: python
```

**`mysite/urls.py`**

```{literalinclude} ../examples/django/mysite/urls.py
:language: python
```

**`mysite/views.py`**

```{literalinclude} ../examples/django/mysite/views.py
:language: python
```

The Django templates used by this example:

**`mysite/templates/base.html`**

```{literalinclude} ../examples/django/mysite/templates/base.html
:language: html
```

**`mysite/templates/index.html`**

```{literalinclude} ../examples/django/mysite/templates/index.html
:language: html
```

**`mysite/templates/figure.html`**

```{literalinclude} ../examples/django/mysite/templates/figure.html
:language: html
```
