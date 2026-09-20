import os

project = "mplbed"
copyright = "2024, Frankie Robertson"
author = "Frankie Robertson"

# When built by sphinx-polyversion (see docs/poly.py), the metadata of the
# revision being built is passed via the environment. It is added to
# `html_context` as `current`, `latest`, `tags` and `branches`, which
# `_templates/versioning.html` uses to render the version selector.
if os.environ.get("POLYVERSION_DATA"):
    from sphinx_polyversion import load

    # importing GitRef registers it with the json decoder used by `load`
    from sphinx_polyversion.git import GitRef  # noqa: F401

    load(globals())

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build"]

html_theme = "furo"
html_static_path = ["_static"]
html_css_files = ["css/version-selector.css"]

# The version selector is added below the toc, but inside the scrollable area.
html_sidebars = {
    "**": [
        "sidebar/brand.html",
        "sidebar/search.html",
        "sidebar/scroll-start.html",
        "sidebar/navigation.html",
        "sidebar/ethical-ads.html",
        "versioning.html",
        "sidebar/scroll-end.html",
        "sidebar/variant-selector.html",
    ],
}

# MyST
myst_enable_extensions = ["colon_fence"]

# Napoleon — NumPy-style docstrings
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_use_param = True
napoleon_use_rtype = True

# autodoc
autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}

# sphinx-autodoc-typehints
always_document_param_types = False
typehints_fully_qualified = False
simplify_optional_unions = True

# Starlette has an unresolvable WebSocket forward-ref in its type annotations
suppress_warnings = ["sphinx_autodoc_typehints.forward_reference"]
