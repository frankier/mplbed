# Django

The Django integration is typically imported as
`from mplbed import mplbed_django` (although it is also available as
`mplbed.integration.django`). It requires an ASGI deployment.

Wrap the Django ASGI application in the project's `asgi.py`:

```python
import os

from django.core.asgi import get_asgi_application

from mplbed import mplbed_django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

application = mplbed_django.setup(get_asgi_application())
```

To display a figure at a particular route, decorate a Django view that returns
a Matplotlib figure:

```python
import matplotlib.pyplot as plt
from django.urls import path

from mplbed import mplbed_django


@mplbed_django.figure_page
def figure(request):
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [4, 5, 6])
    return fig


urlpatterns = [path("figure/", figure, name="figure")]
```

The `setup` function installs the mplbed middleware and selects the interactive
Matplotlib backend. Unlike the other framework integrations, it returns the
wrapped ASGI application:

```{eval-rst}
.. autofunction:: mplbed.mplbed_django.setup
```

The `figure_page` helper wraps a view that returns a Matplotlib figure in a
Django `HttpResponse`:

```{eval-rst}
.. autofunction:: mplbed.mplbed_django.figure_page
```

For a figure page rendered with the Django template language, use
`figure_page_dtl`. The template receives `mplbed_head` and `fig`:

```{eval-rst}
.. autofunction:: mplbed.mplbed_django.figure_page_dtl
```

`iframe_for` creates an iframe for a named Django URL:

```{eval-rst}
.. autofunction:: mplbed.mplbed_django.iframe_for
```

## Further examples

### Inline, iframe, and popup figures (`asgi.py` + `mysite/`)

The complete example runs Django under Daphne. It configures the ASGI
middleware, registers the mplbed template context processor, and demonstrates
inline, iframe, popup, raw figure-page, and Django-template figure-page usage.

**`asgi.py`**

```{literalinclude} ../../examples/django/asgi.py
:language: python
```

**`mysite/settings.py`**

```{literalinclude} ../../examples/django/mysite/settings.py
:language: python
```

**`mysite/urls.py`**

```{literalinclude} ../../examples/django/mysite/urls.py
:language: python
```

**`mysite/views.py`**

```{literalinclude} ../../examples/django/mysite/views.py
:language: python
```

The Django templates used by the example:

**`mysite/templates/base.html`**

```{literalinclude} ../../examples/django/mysite/templates/base.html
:language: html
```

**`mysite/templates/index.html`**

```{literalinclude} ../../examples/django/mysite/templates/index.html
:language: html
```

**`mysite/templates/figure.html`**

```{literalinclude} ../../examples/django/mysite/templates/figure.html
:language: html
```
