"""Sphinx configuration.

The API reference is generated from docstrings, so this file should not need to
change when the API does.
"""

from importlib.metadata import version as installed_version

project = "tofasta"
author = "Matt McCormick"
copyright = "2026, Matt McCormick"  # noqa: A001

# Read from package metadata so the docs cannot drift from the release.
release = installed_version("tofasta")
version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "myst_parser",
    "sphinxarg.ext",
]

exclude_patterns = ["_build"]

# Docstrings in this project are NumPy style.
napoleon_numpy_docstring = True
napoleon_google_docstring = False

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented_params"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
}

myst_enable_extensions = ["colon_fence", "deflist"]
myst_heading_anchors = 3

html_theme = "furo"
html_title = f"tofasta {release}"
