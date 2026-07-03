project = "mplbed"
copyright = "2024, Frankie Robertson"
author = "Frankie Robertson"

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
