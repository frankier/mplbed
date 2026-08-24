import importlib
import subprocess
import sys
from importlib.metadata import requires
from pathlib import Path
from unittest.mock import Mock

import pytest
from matplotlib.figure import Figure
from nicegui import app
from nicegui.client import Client
from nicegui.element import Element
from nicegui.page import page
from nicegui.testing.general import nicegui_reset_globals
from packaging.requirements import Requirement
from starlette.applications import Starlette

from mplbed.server import mplbed_app_factory
from mplbed.server._impl import managers

REPO_ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.filterwarnings("ignore:coroutine 'Outbox.loop' was never awaited:RuntimeWarning")


@pytest.fixture(autouse=True)
def reset_nicegui():
    """Isolate NiceGUI and mplbed's process-global integration state."""
    with nicegui_reset_globals():
        module = sys.modules.get("mplbed.integration.nicegui")
        if module is not None:
            module._setup_state = None
        managers.clear()
        yield
        managers.clear()


def nicegui_integration():
    """Import the optional integration after the test reset fixture runs."""
    return importlib.import_module("mplbed.integration.nicegui")


def client_context():
    """Create an explicit client context without enabling NiceGUI script mode."""
    return Client(page("/test"))


def test_setup_delegates_to_starlette_and_registers_assets_once(monkeypatch):
    integration = nicegui_integration()
    mplbed_app = Starlette()
    starlette_setup = Mock()
    add_head_html = Mock()
    monkeypatch.setattr(integration.starlette, "setup", starlette_setup)
    monkeypatch.setattr(integration.ui, "add_head_html", add_head_html)
    monkeypatch.setattr(integration, "head_content", lambda **kwargs: f"assets:{kwargs!r}")

    kwargs = {
        "prefix": "/plots",
        "mplbed_starlette_app": mplbed_app,
        "mplbed_starlette_app_kwargs": {"debug": True},
        "manage_routing": False,
        "do_use_mpl_backend": False,
        "use_webaggext_backend": False,
    }
    integration.setup(app, **kwargs)
    integration.setup(app, **kwargs)

    starlette_setup.assert_called_once_with(app, **kwargs)
    add_head_html.assert_called_once_with(
        f"assets:{{'core': True, 'prefix_and_app': ('/plots', {mplbed_app!r})}}",
        shared=True,
    )


def test_setup_creates_the_subapp_used_for_assets(monkeypatch):
    integration = nicegui_integration()
    mplbed_app = mplbed_app_factory()
    app_factory = Mock(return_value=mplbed_app)
    monkeypatch.setattr(integration, "mplbed_app_factory", app_factory)
    starlette_setup = Mock()
    monkeypatch.setattr(integration.starlette, "setup", starlette_setup)
    monkeypatch.setattr(integration.ui, "add_head_html", Mock())

    integration.setup(app, mplbed_starlette_app_kwargs={"debug": True})

    app_factory.assert_called_once_with(debug=True)
    starlette_setup.assert_called_once_with(
        app,
        prefix=integration.DEFAULT_PREFIX,
        mplbed_starlette_app=mplbed_app,
        mplbed_starlette_app_kwargs={"debug": True},
        manage_routing=True,
        do_use_mpl_backend=True,
        use_webaggext_backend=True,
    )


def test_setup_requires_a_subapp_when_routing_is_not_managed():
    integration = nicegui_integration()

    with pytest.raises(ValueError, match="construct and provide"):
        integration.setup(app, manage_routing=False)


def test_setup_rejects_a_different_configuration():
    integration = nicegui_integration()
    integration.setup(app, prefix="/first")

    with pytest.raises(RuntimeError, match="already configured"):
        integration.setup(app, prefix="/second")


def test_matplotlib_requires_setup():
    integration = nicegui_integration()

    with pytest.raises(RuntimeError, match=r"setup\(app\)"):
        integration.matplotlib()


def test_matplotlib_owns_a_read_only_figure_and_forwards_kwargs():
    integration = nicegui_integration()
    integration.setup(app)

    with client_context():
        plot = integration.matplotlib(figsize=(6, 4), dpi=80)

    assert isinstance(plot, Element)
    assert isinstance(plot.figure, Figure)
    assert plot.figure.get_size_inches().tolist() == [6.0, 4.0]
    assert plot.figure.dpi == 80
    with pytest.raises(AttributeError):
        plot.figure = Figure()


def test_matplotlib_exposes_navigation_suppression_without_forwarding_it_to_figure():
    integration = nicegui_integration()
    integration.setup(app)

    with client_context():
        default_plot = integration.matplotlib()
        opted_in_plot = integration.matplotlib(prevent_default_navigation=True, figsize=(6, 4))

    assert default_plot._props["preventDefaultNavigation"] is False
    assert opted_in_plot._props["preventDefaultNavigation"] is True
    assert opted_in_plot.figure.get_size_inches().tolist() == [6.0, 4.0]


def test_update_schedules_a_redraw_and_preserves_element_updates(monkeypatch):
    integration = nicegui_integration()
    integration.setup(app)
    with client_context():
        plot = integration.matplotlib()
    draw_idle = Mock()
    element_update = Mock()
    monkeypatch.setattr(plot.figure.canvas, "draw_idle", draw_idle)
    monkeypatch.setattr(Element, "update", element_update)

    result = plot.update()

    assert result is None
    draw_idle.assert_called_once_with()
    element_update.assert_called_once_with()


def test_figure_context_exit_updates_even_after_an_exception(monkeypatch):
    integration = nicegui_integration()
    integration.setup(app)
    with client_context():
        plot = integration.matplotlib()
    update = Mock()
    monkeypatch.setattr(plot, "update", update)

    with pytest.raises(ValueError, match="expected"), plot.figure as figure:
        assert figure is plot.figure
        raise ValueError("expected")

    update.assert_called_once_with()


def test_standard_element_styling_remains_chainable():
    integration = nicegui_integration()
    integration.setup(app)

    with client_context():
        plot = integration.matplotlib()

    assert plot.classes("w-full") is plot
    assert plot.style("min-height: 10rem") is plot


def test_basic_webagg_backend_can_update_before_connection():
    integration = nicegui_integration()
    integration.setup(app, use_webaggext_backend=False)

    with client_context():
        plot = integration.matplotlib()

    plot.update()


def test_deleting_an_unconnected_element_releases_its_manager():
    integration = nicegui_integration()
    integration.setup(app)
    with client_context():
        plot = integration.matplotlib()
        figure_id = plot.figure.canvas.manager.num
        assert managers[figure_id] is plot.figure.canvas.manager

        plot.delete()

    assert figure_id not in managers


def test_deleting_a_client_releases_unconnected_managers():
    integration = nicegui_integration()
    integration.setup(app)
    with client_context():
        plot = integration.matplotlib()
        figure_id = plot.figure.canvas.manager.num

        plot.client.delete()

    assert figure_id not in managers
    assert not Client.instances


def test_core_import_does_not_require_nicegui():
    code = """
import importlib.abc
import sys

class BlockNiceGUI(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'nicegui' or fullname.startswith('nicegui.'):
            raise ModuleNotFoundError("blocked NiceGUI", name=fullname)

sys.meta_path.insert(0, BlockNiceGUI())
import mplbed
assert 'nicegui' not in sys.modules
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


def test_optional_import_error_points_to_the_extra():
    code = """
import importlib.abc
import sys

class BlockNiceGUI(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'nicegui' or fullname.startswith('nicegui.'):
            raise ModuleNotFoundError("blocked NiceGUI", name=fullname)

sys.meta_path.insert(0, BlockNiceGUI())
try:
    import mplbed.integration.nicegui
except ImportError as error:
    assert 'mplbed[nicegui]' in str(error)
else:
    raise AssertionError('expected ImportError')
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


def test_distribution_metadata_keeps_nicegui_optional():
    requirements = requires("mplbed") or []
    nicegui_requirements = [Requirement(requirement) for requirement in requirements if requirement.lower().startswith("nicegui")]

    assert len(nicegui_requirements) == 1
    requirement = nicegui_requirements[0]
    assert str(requirement.specifier) == ">=3.15.0"
    assert requirement.marker is not None
    assert requirement.marker.evaluate({"extra": "nicegui"})
    assert not requirement.marker.evaluate({"extra": ""})
