import matplotlib

matplotlib.use("module://mplbed.webaggext._impl")

import matplotlib.pyplot as plt
import pytest
from matplotlib._pylab_helpers import Gcf
from matplotlib.figure import Figure
from starlette.testclient import TestClient

from mplbed import FigureCollector, raw_html
from mplbed.asgi import _prefix_and_app
from mplbed.server._impl import add_manager, close_fig, managers, mplbed_app_factory


@pytest.fixture(autouse=True)
def server():
    Gcf.destroy_all()
    managers.clear()
    app = mplbed_app_factory()
    token = _prefix_and_app.set(("", app))
    with TestClient(app) as client:
        yield client
    _prefix_and_app.reset(token)
    Gcf.destroy_all()
    managers.clear()


def collect(title, number, close):
    collector = FigureCollector(target="inline", on_close="remove")
    with collector:
        figure = plt.figure(num=number)
        figure.subplots().set_title(title)
        plt.show()
        if close:
            plt.close(figure)
    return figure.canvas.manager, collector.consume_one()


@pytest.mark.parametrize("number", [None, 17])
@pytest.mark.parametrize("close", [False, True])
def test_reused_pyplot_numbers_keep_downloads_events_and_cleanup_isolated(server, number, close):
    first, first_html = collect("FIRST", number, close)
    first_id = add_manager(first)
    assert Gcf.get_all_fig_managers() == []

    def acknowledge(manager, title):
        manager.canvas.mpl_connect(
            "key_press_event",
            lambda event: manager._send_event("test_key", title=title, key=event.key),
        )

    acknowledge(first, "FIRST")
    with server.websocket_connect(f"/ws/{first_id}") as first_ws:
        first_ws.send_json({"figure_id": first_id, "type": "supports_binary", "value": True})
        assert first_ws.receive_json()["type"] == "resize"
        assert first_ws.receive_json()["type"] == "refresh"
        first_ws.send_json({"figure_id": first_id, "type": "key_press", "key": "kshift"})
        assert first_ws.receive_json() == {"type": "test_key", "title": "FIRST", "key": "shift"}

        second, second_html = collect("SECOND", number, close)
        second_id = add_manager(second)
        assert first.num == second.num
        assert first_id != second_id
        assert first_html != second_html
        assert managers[first_id] is first
        assert managers[second_id] is second
        assert Gcf.get_all_fig_managers() == []
        for fig_id, html, title in ((first_id, first_html, "FIRST"), (second_id, second_html, "SECOND")):
            assert f'"/ws/{fig_id}"' in html
            assert f"/download/{fig_id}.{{fmt}}" in html
            response = server.get(f"/download/{fig_id}.svg")
            assert response.status_code == 200
            assert title in response.text
            assert ("SECOND" if title == "FIRST" else "FIRST") not in response.text

        acknowledge(second, "SECOND")
        with server.websocket_connect(f"/ws/{second_id}") as second_ws:
            second_ws.send_json({"figure_id": second_id, "type": "supports_binary", "value": True})
            assert second_ws.receive_json()["type"] == "resize"
            assert second_ws.receive_json()["type"] == "refresh"
            for ws, fig_id, title in ((first_ws, first_id, "FIRST"), (second_ws, second_id, "SECOND")):
                ws.send_json({"figure_id": fig_id, "type": "key_press", "key": "kcontrol"})
                assert ws.receive_json() == {"type": "test_key", "title": title, "key": "control"}
            second_ws.send_json({"figure_id": second_id, "type": "close"})
            assert second_ws.receive_json() == {"type": "closed", "figure_id": second_id}
        assert second_id not in managers
        assert managers[first_id] is first
        first_ws.send_json({"figure_id": first_id, "type": "key_press", "key": "kalt"})
        assert first_ws.receive_json() == {"type": "test_key", "title": "FIRST", "key": "alt"}
    assert first_id not in managers


def test_registration_is_stable_and_rejects_collisions():
    first, _ = collect("FIRST", None, False)
    fig_id = add_manager(first)
    assert add_manager(first) == fig_id
    second, _ = collect("SECOND", None, False)
    second._mplbed_fig_id = fig_id
    with pytest.raises(ValueError, match="already registered"):
        add_manager(second)
    assert managers[fig_id] is first


def test_cleanup_preserves_a_new_pyplot_manager_with_the_same_number():
    first, _ = collect("FIRST", 17, False)
    fig_id = add_manager(first)
    replacement = plt.figure(num=17).canvas.manager
    close_fig(None, fig_id, False)
    assert Gcf.figs[17] is replacement
    assert fig_id not in managers


def test_direct_html_uses_server_identity(server):
    figure = Figure()
    html = raw_html.figure_html(figure)
    fig_id = add_manager(figure.canvas.manager)
    assert f'"/ws/{fig_id}"' in html
    assert f"/download/{fig_id}.{{fmt}}" in html
    assert server.get(f"/download/{fig_id}.svg").status_code == 200


def test_sequential_collectors_keep_both_managers_registered():
    first, first_html = collect("FIRST", None, False)
    second, second_html = collect("SECOND", None, False)
    assert first.num == second.num
    assert first is not second
    assert len(managers) == 2
    assert first_html != second_html
