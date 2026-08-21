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
that standard NiceGUI classes and layout containers remain available.

```{literalinclude} ../../examples/nicegui/basic.py
:language: python
```
