# ASGI

```{admonition} TODO
:class: note

Add a framework-agnostic end-to-end example showing how to mount the mplbed
application, retain the native application context, and generate route URLs.
Until then, prefer a framework-specific integration when one is available.
```

The lower-level ASGI API provides middleware and context helpers used by the
framework integrations.

## API reference

```{eval-rst}
.. autoclass:: mplbed.asgi.MplbedMiddleware
   :members:
   :no-index:

.. autofunction:: mplbed.asgi.get_native_app
   :no-index:

.. autofunction:: mplbed.asgi.get_asgi_app
   :no-index:

.. autofunction:: mplbed.asgi.url_path_for
   :no-index:
```
