# mplbed

[`mplbed`](https://github.com/frankier/mplbed/) is a library of support code for embedding interactive, server-side matplotlib figures in web applications.

It can be as easy as:

```python
import mywebframework
from mplbed import mplbed_mywebframework

@mywebframework.route("/myplot")
@mplbed_mywebframework.figure_page
def my_plot_page(request):
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [4, 5, 6])
    return fig

app = mywebframework.App(...)
setup(app)
```

`mplbed` provides the above interface fairly uniformly across the following "classical" web frameworks:

 * Starlette
 * Django
 * Quart

`mplbed` also provides integration for single file GUI-builder -style frameworks such as:

 * NiceGUI

In this case, the interface is different per-framework to attempt to follow each framework's established idioms, especially since many of these already have functionality for embedding (typically static) matplotlib figures.

Finally, `mplbed` provides a "framework-agnostic" interface for use with any ASGI-compatible web framework.

```{toctree}
:maxdepth: 2
:hidden:

installing
```

```{toctree}
:caption: Integrations
:maxdepth: 2
:hidden:

integrations/starlette
integrations/django
integrations/quart
integrations/nicegui
integrations/asgi
```


```{toctree}
:caption: Reference
:maxdepth: 2
:hidden:

examples
api
```
