# mplbed

```
|[]mpl
|======|
|  bed |
```

`mplbed` is a library of support code for embedding interactive, server-side matplotlib figures in web applications.

Supporting, in principle any ASGI-compatible Python application, it provides convenient integration for a number of frameworks ones out of the box.
It aims to have "usually-works" defaults useful for quick demos, while providing a lot of flexibility and options as well as utilities to deal with advanced issues such as style isolation, and connection and resource management to enable some degree of scaling up to use-cases like internal dashboards.

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

## Install as a library

Currently you can install this package from Github:

    $ uv add git+https://github.com/frankier/mplbed

## Run the examples

The documentation is currently limited to example code.

You can run the examples with the following commands:

    $ uv sync -U --all-groups --all-extras
    $ cd examples/starlette && uv run uvicorn --port 8001 --workers 1 one_fig:app
    $ cd examples/starlette && uv run uvicorn --port 8001 --workers 1 demo_popup:app
