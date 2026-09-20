"""Configuration for building the versioned docs with `sphinx-polyversion`.

Build every released version and the main branch into one site with::

    uv run sphinx-polyversion docs/poly.py

Or build only the working tree for a quick check (output goes to `build/local`)::

    uv run sphinx-polyversion -l docs/poly.py
"""

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from sphinx_polyversion import apply_overrides
from sphinx_polyversion.builder import BuildError
from sphinx_polyversion.driver import DefaultDriver
from sphinx_polyversion.git import Git, GitRef, GitRefType, file_predicate, refs_by_type
from sphinx_polyversion.pyvenv import VenvWrapper, VirtualPythonEnvironment
from sphinx_polyversion.sphinx import SphinxBuilder


class Uv(VirtualPythonEnvironment):
    """Build environment created with `uv sync` from a revision's lockfile.

    The docs are built with the dependencies the revision shipped with, so
    `uv` resolves the `docs` dependency group of the revision to build.

    Parameters
    ----------
    path : Path
        The location of the checked out revision.
    name : str
        The name of the revision, used for logging.
    args : Sequence[str]
        Arguments to pass to `uv sync`.

    """

    def __init__(self, path: Path, name: str, args: Sequence[str]) -> None:
        """Create the environment, but sync it only when entering it."""
        super().__init__(path, name, path / ".venv", creator=VenvWrapper())
        self.args = args

    async def __aenter__(self) -> Uv:
        """Sync the `docs` group of the revision into a fresh environment.

        Raises
        ------
        BuildError
            If `uv sync` fails.

        """
        await super().__aenter__()
        _, err, rc = await self.run("uv", "sync", *self.args, cwd=self.path)
        if rc:
            raise BuildError(f"`uv sync` failed: {err}")
        return self


#: Branches to build docs for, matched in full
BRANCH_REGEX = r"main"

#: Tags to build docs for, matched in full
TAG_REGEX = r"v\d+\.\d+\.\d+"

#: Output directory of the merged site, relative to the project root
OUTPUT_DIR = "build"

#: Arguments to pass to `uv sync` for each revision
UV_ARGS = ["--group", "docs", "--frozen"]

#: Arguments to pass to `sphinx-build` for each revision
SPHINX_ARGS = ["-a"]

#: Metadata mocked when building the working tree locally (see the module docstring)
MOCK_DATA = {
    "revisions": [],
    "current": GitRef("local", "", "", GitRefType.BRANCH, datetime.fromtimestamp(0)),
}

#: Whether to build only the working tree instead of every revision
MOCK = False

#: Whether to build revisions one after another instead of in parallel
SEQUENTIAL = False


def data(driver: DefaultDriver, rev: GitRef, env: Uv) -> dict[str, Any]:
    """Return the versioning data made available to `conf.py` and its templates."""
    branches, tags = refs_by_type(driver.targets)
    return {
        "current": rev,
        "revisions": driver.targets,
        "branches": branches,
        "tags": tags,
        # The newest revision: what the root of the site redirects to, see `root_data`.
        "latest": max(driver.targets),
    }


def root_data(driver: DefaultDriver) -> dict[str, Any]:
    """Return the variables for the root templates, i.e. `docs/templates/index.html`."""
    return {"latest": max(driver.builds, default=None)}


# Load overrides read from the command line into the global scope
apply_overrides(globals())
root = Git.root(Path(__file__).parent)
src = Path("docs")

DefaultDriver(
    root,
    root / OUTPUT_DIR,
    vcs=Git(
        branch_regex=BRANCH_REGEX,
        tag_regex=TAG_REGEX,
        # only refs that contain the docs can be built
        predicate=file_predicate([src / "conf.py", Path("pyproject.toml")]),
    ),
    builder=SphinxBuilder(src, args=SPHINX_ARGS),
    env=Uv.factory(args=UV_ARGS),
    template_dir=root / src / "templates",
    data_factory=data,
    root_data_factory=root_data,
    mock=MOCK_DATA,
).run(MOCK, SEQUENTIAL)
