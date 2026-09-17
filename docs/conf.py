"""Sphinx configuration.

The API reference is generated from the docstrings rather than written out, so
a signature change cannot leave the docs behind. Prose that explains *why* VTOP
behaves the way it does lives in guide/ and is written by hand.
"""

import tomllib
from pathlib import Path

_pyproject = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text())

project = "vitap-vtop-client"
author = "Udhay Adithya"
copyright = "%Y, Udhay Adithya"
release = _pyproject["tool"]["poetry"]["version"]
version = ".".join(release.split(".")[:2])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",       # the codebase uses Google-style Args/Returns/Raises
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
    "myst_parser",               # so CHANGELOG.md can be included as-is
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Autodoc ---------------------------------------------------------------
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}
# Pydantic models render better without their inherited BaseModel surface.
autodoc_pydantic_model_show_json = False

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_rtype = False

# httpx does not publish an objects.inv, so it cannot be linked here.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# -- HTML ------------------------------------------------------------------
html_theme = "furo"
html_title = f"vitap-vtop-client {release}"
html_static_path = ["_static"]
# Copied verbatim into the build. Holds .nojekyll, which stops GitHub Pages
# running Jekyll -- Jekyll drops directories beginning with an underscore, and
# Sphinx puts every asset in _static.
html_extra_path = ["_extra"]
html_theme_options = {
    "source_repository": "https://github.com/Udhay-Adithya/vitap-vtop-client/",
    "source_branch": "main",
    "source_directory": "docs/",
}
