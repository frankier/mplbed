# Examples

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
```

## Starlette

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
