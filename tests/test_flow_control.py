import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from mplbed.server import mplbed_app_factory
from mplbed.server._impl import _draw_and_complete
from mplbed.webaggext._impl import FigureManagerWebAggExt

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize(
    ("option", "value"),
    [
        ("resize_max_in_flight", 0),
        ("resize_max_in_flight", -1),
        ("resize_max_in_flight", True),
        ("motion_throttle_ms", 0),
        ("motion_throttle_ms", -1),
        ("scroll_throttle_ms", False),
    ],
)
def test_app_factory_rejects_non_positive_flow_control_values(option, value):
    """Factory construction rejects invalid flow-control intervals and limits."""
    with pytest.raises(ValueError, match=option):
        mplbed_app_factory(**{option: value})


def test_app_factory_embeds_flow_control_configuration():
    """The generated client bundle contains the validated factory settings."""
    app = mplbed_app_factory(
        resize_max_in_flight=3,
        motion_throttle_ms=20,
        scroll_throttle_ms=None,
    )
    javascript = FigureManagerWebAggExt.get_javascript(flow_control=app.state.flow_control)
    expected = json.dumps(
        {
            "resize_max_in_flight": 3,
            "motion_throttle_ms": 20,
            "scroll_throttle_ms": None,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    assert f"mpl.flow_control = {expected};" in javascript


def test_delayed_draw_sends_completions_after_image():
    """Request completions follow the image produced by their shared draw."""
    events = []

    class Canvas:
        _delayed_draw_dirty = True
        _pending_completions = [("resize", 17), ("motion_notify", 18)]

        def draw(self):
            events.append(("binary", b"image"))
            self._delayed_draw_dirty = False

    class WebSocket:
        def send_json(self, message):
            events.append(("json", message))

    manager = SimpleNamespace(canvas=Canvas())
    _draw_and_complete(manager, WebSocket())

    assert events == [
        ("binary", b"image"),
        ("json", {"type": "resize_completion", "seq": 17}),
        ("json", {"type": "motion_notify_completion", "seq": 18}),
    ]
    assert manager.canvas._pending_completions == []


def test_completion_survives_an_intervening_synchronous_draw():
    """A draw that already cleared dirty state still releases resize capacity."""
    events = []
    canvas = SimpleNamespace(
        _delayed_draw_dirty=False,
        _pending_completions=[("motion_notify", 19)],
        draw=lambda: pytest.fail("the clean canvas must not be drawn again"),
    )
    websocket = SimpleNamespace(send_json=lambda message: events.append(message))

    _draw_and_complete(SimpleNamespace(canvas=canvas), websocket)

    assert events == [{"type": "motion_notify_completion", "seq": 19}]
    assert canvas._pending_completions == []


def test_client_scheduler_contract():
    """The JavaScript scheduler satisfies its deterministic client contract."""
    result = subprocess.run(
        ["node", "--test", "tests/js/test_flow_control.mjs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
