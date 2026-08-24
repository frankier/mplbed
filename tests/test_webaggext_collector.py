import threading

import matplotlib

matplotlib.use("module://mplbed.webaggext._impl")

import matplotlib.pyplot as plt
import pytest
from matplotlib._pylab_helpers import Gcf

from mplbed import FigureCollector
from mplbed.webaggext._impl import FigureManagerWebAggExt


@pytest.fixture(autouse=True)
def _clean_gcf():
    Gcf.destroy_all()
    yield
    Gcf.destroy_all()


def test_show_only_shows_figures_created_in_context(monkeypatch):
    shown = []
    monkeypatch.setattr(FigureManagerWebAggExt, "show", lambda self: shown.append(self.num))

    # A stale figure left over from an earlier request.
    plt.figure()

    with FigureCollector(target="inline", on_close="remove"):
        plt.figure()
        plt.show()

    assert shown == [2]


def test_figures_are_deregistered_on_exit(monkeypatch):
    monkeypatch.setattr(FigureManagerWebAggExt, "show", lambda self: None)

    with FigureCollector(target="inline", on_close="remove"):
        plt.figure()
        plt.show()

    assert Gcf.get_all_fig_managers() == []


def test_concurrent_collectors_do_not_cross_contaminate(monkeypatch):
    shown = {}
    monkeypatch.setattr(
        FigureManagerWebAggExt,
        "show",
        lambda self: shown.setdefault(threading.current_thread().name, []).append(self.num),
    )

    barrier = threading.Barrier(3)

    def render(name):
        with FigureCollector(target="inline", on_close="remove"):
            plt.figure()
            barrier.wait()  # both figures exist in Gcf before either shows
            plt.show()

    threads = [threading.Thread(target=render, args=(name,), name=name) for name in ("A", "B")]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()

    assert len(shown["A"]) == 1
    assert len(shown["B"]) == 1
    assert set(shown["A"] + shown["B"]) == {1, 2}
    assert Gcf.get_all_fig_managers() == []


@pytest.mark.parametrize("prevent_default_navigation", [False, True])
def test_show_forwards_navigation_suppression(monkeypatch, prevent_default_navigation):
    generated = []
    monkeypatch.setattr(
        "mplbed.html.raw.figure_html_from_id",
        lambda fig_id, **kwargs: generated.append((fig_id, kwargs)) or "<figure>",
    )

    collector = FigureCollector(
        target="inline",
        on_close="remove",
        prevent_default_navigation=prevent_default_navigation,
    )
    with collector:
        plt.figure()
        plt.show()

    assert generated == [
        (
            1,
            {
                "target": "inline",
                "on_close": "remove",
                "prevent_default_navigation": prevent_default_navigation,
            },
        )
    ]
    assert collector.consume_one() == "<figure>"
