# NiceGUI

```{admonition} TODO
:class: note

Expand this guide with an explanation of the element lifecycle, client-owned
figures, redraw behavior, and cleanup. The API reference and runnable example
below document the currently supported interface.
```

Install the optional integration with `uv add "mplbed[nicegui]"`. Call
`setup(app)` before creating a `matplotlib` element or starting NiceGUI with
`ui.run()`.

Plots that use wheel or navigation-key input can opt out of the corresponding
browser scrolling behavior:

```python
plot = matplotlib(prevent_default_navigation=True)
```

This covers wheel, Arrow, PageUp/PageDown, Home/End, and Space events. Tab and
non-navigation keys retain their normal browser behavior.

Use `matplotlib(fit="width")` to match the element's width while keeping the
figure's initial aspect ratio. Use `matplotlib(fit="container").style("height:
400px")` to fill a sized element. Fitted figures hide the manual resize
handle by default; `resize_handle=True` shows it.

## API reference

```{eval-rst}
.. autofunction:: mplbed.integration.nicegui.setup
   :no-index:

.. autofunction:: mplbed.integration.nicegui.matplotlib
   :no-index:

.. autoclass:: mplbed.integration.nicegui.Matplotlib
   :members: figure, update
   :no-index:
```

## Further examples

### Two live figures (`basic.py`)

Creates two client-owned figures, updates one independently, and demonstrates
that standard NiceGUI classes and layout containers remain available. Its
``/navigation`` page demonstrates opt-in browser navigation suppression, and
``/fit`` shows both parent-fitting modes.

```{literalinclude} ../../examples/nicegui/basic.py
:language: python
```
