"""
End-to-end tests: for each example, load every route in a real browser via
Playwright, find every embedded matplotlib/webagg figure (including ones
inside iframes, and popups spawned as a side effect of interacting with a
figure), pan it, and check that the canvas actually changed and is not left
blank.
"""
import base64
import io

import pytest
from PIL import Image

from conftest import running_example

pytestmark = pytest.mark.e2e

SETTLE_SECONDS = 1.5
PAN_DELTA = (70, 50)
MAX_ROUNDS = 5  # bound on figures-spawning-figures (e.g. popups) per page
# Vertical fractions of the canvas to try dragging from. A single fixed point
# doesn't work for every figure layout: e.g. two stacked subplots have a gap
# around the middle that belongs to no Axes, while some single-Axes figures
# (like MNE's raw browser) reserve their edges for chrome that doesn't pan.
PAN_Y_FRACTIONS = (0.5, 0.3, 0.7, 0.2, 0.8)

_ASSIGN_IDS_JS = """() => {
    const roots = Array.from(document.querySelectorAll('.mpl-figure-root'));
    const created = [];
    for (const el of roots) {
        if (!el.dataset.e2eId) {
            el.dataset.e2eId = 'e2e-' + Math.random().toString(36).slice(2);
            created.push(el.dataset.e2eId);
        }
    }
    return created;
}"""


def _canvas_png_bytes(canvas_locator):
    data_url = canvas_locator.evaluate("el => el.toDataURL('image/png')")
    _, b64data = data_url.split(",", 1)
    return base64.b64decode(b64data)


def _is_blank(png_bytes, threshold=8):
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    extrema = img.getextrema()
    spread = max(mx - mn for mn, mx in extrema)
    return spread < threshold


def _canvas_for_root(root):
    # Scoped to *direct* children so a nested popup's `.mpl-figure-root`
    # (which can end up inside this root, see below) isn't matched too.
    return root.locator(":scope > div > canvas.mpl-canvas")


def _pan_button_for_root(root):
    return root.locator(":scope > div.mpl-toolbar img[alt*='pans']")


def _pan_and_verify(page, figure_root, *, label):
    canvas = _canvas_for_root(figure_root)
    canvas.wait_for(state="visible", timeout=15000)
    # A previously-closed dialog can leave the page scrolled to wherever it
    # used to be, so re-anchor before trusting any bounding box.
    canvas.scroll_into_view_if_needed()
    page.wait_for_timeout(int(SETTLE_SECONDS * 1000))

    before = _canvas_png_bytes(canvas)
    assert not _is_blank(before), f"{label}: canvas is blank before panning"

    _pan_button_for_root(figure_root).click()
    # The button click has to make a WS round trip to the server before pan
    # mode is actually active; without this, a fast drag can be missed.
    page.wait_for_timeout(400)

    box = canvas.bounding_box()
    assert box is not None, f"{label}: canvas has no bounding box"
    cx = box["x"] + box["width"] / 2

    after = before
    changed = False
    for y_fraction in PAN_Y_FRACTIONS:
        cy = box["y"] + box["height"] * y_fraction
        page.mouse.move(cx, cy)
        page.mouse.down()
        page.mouse.move(cx + PAN_DELTA[0], cy + PAN_DELTA[1], steps=10)
        page.mouse.up()
        page.wait_for_timeout(int(SETTLE_SECONDS * 1000))
        after = _canvas_png_bytes(canvas)
        if after != before:
            changed = True
            break

    assert changed, f"{label}: canvas did not change after panning at any point tried"
    assert not _is_blank(after), f"{label}: canvas is blank after panning"


def _pan_all_figures_in_frame(page, frame, *, label_prefix):
    """
    Pan every `.mpl-figure-root` in `frame`, including ones that only appear
    as a side effect of panning an earlier figure (e.g. a popup). Each root
    is tagged with a stable id as soon as it's seen so it can be located
    again reliably, then re-queried for newly-appeared roots until none show
    up.
    """
    tested = 0
    for _ in range(MAX_ROUNDS):
        new_ids = frame.evaluate(_ASSIGN_IDS_JS)
        if not new_ids:
            break
        roots = [frame.locator(f'[data-e2e-id="{i}"]') for i in new_ids]
        # An open native <dialog> (used for popups) blocks pointer events to
        # the rest of the page, so it must be dealt with first.
        roots.sort(key=lambda r: not r.evaluate("el => !!el.closest('dialog[open]')"))
        for root in roots:
            in_dialog = root.evaluate("el => !!el.closest('dialog[open]')")
            _pan_and_verify(page, root, label=f"{label_prefix} figure #{tested}")
            tested += 1
            if in_dialog:
                # Free up the rest of the page for subsequent figures.
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
    return tested


def test_pan_each_figure(example_spec, page):
    with running_example(example_spec) as (base_url, proc):
        for route in example_spec.routes:
            # Figures keep an open WebSocket for live updates, so "load" is
            # used rather than "networkidle" (which would never fire).
            page.goto(base_url + route, wait_until="load")
            page.main_frame.wait_for_load_state("domcontentloaded")
            total = _pan_all_figures_in_frame(
                page, page.main_frame, label_prefix=f"{example_spec.id}{route}"
            )
            # Fetched fresh (rather than up front) so a frame that's still
            # loading, or is only created a little later, isn't missed or
            # stale by the time it's used. A frame can also be a stale
            # leftover from the *previous* route's navigation that hasn't
            # finished detaching yet, so skip anything no longer attached.
            for child in page.main_frame.child_frames:
                if child.is_detached():
                    continue
                child.wait_for_load_state("domcontentloaded")
                total += _pan_all_figures_in_frame(
                    page, child, label_prefix=f"{example_spec.id}{route}"
                )
            assert total, f"{example_spec.id}{route}: no figures found"
        assert proc.poll() is None, f"{example_spec.id} exited early"
