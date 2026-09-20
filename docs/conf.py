import os

project = "mplbed"
copyright = "2024, Frankie Robertson"
author = "Frankie Robertson"

# When built by sphinx-polyversion (see docs/poly.py), the metadata of the
# revision being built is passed via the environment and made available to the
# templates as `current`, `latest`, `tags` and `branches`.
current = None
if os.environ.get("POLYVERSION_DATA"):
    from sphinx_polyversion import load
    from sphinx_polyversion.git import GitRef  # registers GitRef with the decoder

    current: GitRef | None = load(globals())["current"]

version = release = current.name if current else ""

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

# The version selector is added below the toc, before furo's own sidebar items.
html_sidebars = {
    "**": [
        "sidebar/brand.html",
        "sidebar/search.html",
        "sidebar/scroll-start.html",
        "sidebar/navigation.html",
        "sidebar/ethical-ads.html",
        "sidebar/scroll-end.html",
        "versioning.html",
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
