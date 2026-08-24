# API Reference

## Integrations

### NiceGUI

Install the optional integration with `uv add "mplbed[nicegui]"`.

```{eval-rst}
.. automodule:: mplbed.integration.nicegui
   :members:
   :undoc-members:
```

### Starlette

```{eval-rst}
.. automodule:: mplbed.integration.starlette
   :members:
   :undoc-members:
```

### Quart

```{eval-rst}
.. automodule:: mplbed.integration.quart
   :members:
   :undoc-members:
```

### Django

```{eval-rst}
.. automodule:: mplbed.integration.django
   :members:
   :undoc-members:
```

## ASGI Middleware

```{eval-rst}
.. automodule:: mplbed.asgi
   :members:
   :undoc-members:
```

## HTML Helpers

Two variants are provided: `mplbed.html.raw` returns plain Python strings,
while `mplbed.html.safe` returns `markupsafe.Markup` objects safe for direct
use in Jinja2 templates.

### Raw strings (`mplbed.html.raw`)

```{eval-rst}
.. automodule:: mplbed.html.raw
   :members:
   :undoc-members:
```

### Markup-safe strings (`mplbed.html.safe`)

```{eval-rst}
.. automodule:: mplbed.html.safe
   :members:
   :undoc-members:
```

## App Factory

`mplbed_app_factory` accepts shared browser request-flow options. Resize
requests default to one request in flight, so repeated observations retain only
the latest pending non-zero size until rendering completes. Set
`resize_max_in_flight` to another positive integer only when experimenting with
additional concurrent resize work.

`motion_throttle_ms` and `scroll_throttle_ms` default to `None`, preserving all
callbacks and their current ordering. A positive integer enables independent
leading-and-trailing throttling in milliseconds. Motion callbacks then receive
the latest sampled state, while scroll callbacks receive summed steps with the
latest coordinates and modifiers. Zero and negative values are invalid. Pass
these options through an integration's `mplbed_starlette_app_kwargs`, or create
and supply a configured app directly.

```{eval-rst}
.. automodule:: mplbed.server
   :members:
   :undoc-members:
```

## Backend

```{eval-rst}
.. automodule:: mplbed.webaggext
   :members:
   :undoc-members:
```
