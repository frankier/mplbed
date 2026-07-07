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

## Installation

Currently you can install this package from Github:

    $ uv add git+https://github.com/frankier/mplbed

## Documentation

The documentation includes [API docs](https://frankier.github.io/mplbed/api.html) and [examples](https://frankier.github.io/mplbed/examples.html).

## Contributing

Contributions are welcome. Please discuss any larger changes in the issues
before making a pull request to avoid wasted work. You, the human contributor,
must personally have reviewed and understood any code submitted.

Set up a dev environment with [uv](https://docs.astral.sh/uv/):

    $ uv sync --all-groups --all-extras

Run the tests (end-to-end tests need Playwright browsers: `uv run playwright install chromium`):

    $ uv run pytest

Lint, format and typecheck:

    $ uv run ruff check ./src
    $ uv run ruff format ./src
    $ uv run ty check ./src

Install the [prek](https://prek.j178.dev/) hook to run these automatically on commit:

    $ prek install
