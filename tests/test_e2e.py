"""
End-to-end tests: for each example, load every route in a real browser via
Playwright, find every embedded matplotlib/webagg figure (including ones
inside iframes, and popups spawned as a side effect of interacting with a
figure), pan it, and check that the canvas actually changed and is not left
blank.
"""
import base64
import io
import json

import pytest
from PIL import Image

from conftest import EXAMPLES, mne_sample_data_available, running_example

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


def test_datapoints_reappear_after_parent_display_none(page):
    """A hidden and reshown canvas renders the same scatter datapoints."""
    spec = next(s for s in EXAMPLES if s.id == "starlette-display_none")
    browser_errors = []
    sent_frames = []
    page.on(
        "console",
        lambda message: browser_errors.append(message.text) if message.type == "error" else None,
    )
    page.on("pageerror", lambda error: browser_errors.append(str(error)))
    page.on(
        "websocket",
        lambda websocket: websocket.on("framesent", lambda frame: sent_frames.append(frame)),
    )
    with running_example(spec) as (base_url, proc):
        response = page.goto(base_url, wait_until="load")
        assert response is not None and response.ok, page.content()
        canvas = page.locator("#plot-parent canvas.mpl-canvas")
        page.wait_for_timeout(1000)
        assert canvas.count(), browser_errors
        canvas.wait_for(state="visible", timeout=15000)
        page.wait_for_timeout(int(SETTLE_SECONDS * 1000))

        def red_pixel_count():
            return canvas.evaluate(
                """el => {
                    const pixels = el.getContext('2d').getImageData(
                        0, 0, el.width, el.height
                    ).data;
                    let count = 0;
                    for (let i = 0; i < pixels.length; i += 4) {
                        if (pixels[i] > 180 && pixels[i + 1] < 100 && pixels[i + 2] < 100) {
                            count += 1;
                        }
                    }
                    return count;
                }"""
            )

        before = red_pixel_count()
        assert before > 0, "scatter datapoints were not rendered initially"
        sent_frames.clear()

        page.get_by_role("button", name="Hide plot").click()
        canvas.wait_for(state="hidden")
        page.get_by_role("button", name="Show plot").click()
        canvas.wait_for(state="visible")
        page.wait_for_timeout(int(SETTLE_SECONDS * 1000))

        assert red_pixel_count() == before, "scatter datapoints did not reappear"
        message_types = {
            json.loads(frame).get("type")
            for frame in sent_frames
            if isinstance(frame, str) and frame.startswith("{")
        }
        assert message_types.isdisjoint({"resize", "refresh"})
        assert not browser_errors
        assert proc.poll() is None, f"{spec.id} exited early"


def test_resize_storm_is_bounded_and_completes_after_each_image(page):
    """Rapid resize observations render the final size without a FIFO backlog."""
    spec = next(s for s in EXAMPLES if s.id == "starlette-display_none")
    traffic = []

    def observe_websocket(websocket):
        websocket.on("framesent", lambda frame: traffic.append(("sent", frame)))
        websocket.on("framereceived", lambda frame: traffic.append(("received", frame)))

    page.on("websocket", observe_websocket)
    with running_example(spec) as (base_url, proc):
        page.goto(base_url, wait_until="load")
        canvas = page.locator("#plot-parent canvas.mpl-canvas")
        canvas.wait_for(state="visible", timeout=15000)
        page.wait_for_timeout(int(SETTLE_SECONDS * 1000))
        traffic.clear()

        final_size = canvas.evaluate(
            """async el => {
                const container = el.parentElement;
                for (let offset = 0; offset < 40; offset += 1) {
                    container.style.width = `${520 + offset}px`;
                    container.style.height = `${360 + offset}px`;
                    await new Promise(resolve => setTimeout(resolve, 5));
                }
                return {width: container.clientWidth, height: container.clientHeight};
            }"""
        )

        page.wait_for_function(
            """size => {
                const canvas = document.querySelector('#plot-parent canvas.mpl-canvas');
                return canvas && canvas.clientWidth === size.width && canvas.clientHeight === size.height;
            }""",
            arg=final_size,
            timeout=15000,
        )
        page.wait_for_timeout(1000)

        outstanding = set()
        maximum_outstanding = 0
        sent_resizes = []
        completions = []
        image_since_send = {}
        for direction, frame in traffic:
            if direction == "received" and not isinstance(frame, str):
                for seq in outstanding:
                    image_since_send[seq] = True
                continue
            if not isinstance(frame, str) or not frame.startswith("{"):
                continue
            message = json.loads(frame)
            if direction == "sent" and message.get("type") == "resize":
                sent_resizes.append(message)
                outstanding.add(message["seq"])
                image_since_send[message["seq"]] = False
                maximum_outstanding = max(maximum_outstanding, len(outstanding))
            elif direction == "received" and message.get("type") == "resize_completion":
                seq = message["seq"]
                assert image_since_send[seq], f"resize {seq} completed before its image"
                outstanding.remove(seq)
                completions.append(message)

        assert sent_resizes
        assert len(sent_resizes) < 40
        assert maximum_outstanding == 1
        assert not outstanding
        assert [message["seq"] for message in completions] == [message["seq"] for message in sent_resizes]
        assert round(sent_resizes[-1]["width"]) == final_size["width"]
        assert round(sent_resizes[-1]["height"]) == final_size["height"]
        assert proc.poll() is None, f"{spec.id} exited early"


def _nicegui_example():
    return next(s for s in EXAMPLES if s.id == "nicegui-basic")


def _nicegui_canvas(page, plot_class):
    return page.locator(f".{plot_class} canvas.mpl-canvas")


def _wait_for_canvas_change(page, plot_class, before):
    page.wait_for_function(
        """([selector, previous]) =>
            document.querySelector(selector)?.toDataURL('image/png') !== previous""",
        arg=[f".{plot_class} canvas.mpl-canvas", before],
        timeout=15000,
    )


def test_nicegui_update_preserves_dom_and_other_figure(page):
    spec = _nicegui_example()
    with running_example(spec) as (base_url, proc):
        page.goto(base_url, wait_until="load")
        first = _nicegui_canvas(page, "plot-one")
        second = _nicegui_canvas(page, "plot-two")
        first.wait_for(state="visible", timeout=15000)
        second.wait_for(state="visible", timeout=15000)
        page.wait_for_timeout(int(SETTLE_SECONDS * 1000))
        first_before = first.evaluate("el => el.toDataURL('image/png')")
        second_before = second.evaluate("el => el.toDataURL('image/png')")
        first.evaluate("el => el.dataset.originalNode = 'true'")

        page.get_by_role("button", name="Update first").click()
        _wait_for_canvas_change(page, "plot-one", first_before)

        assert first.evaluate("el => el.dataset.originalNode") == "true"
        assert second.evaluate("el => el.toDataURL('image/png')") == second_before
        assert proc.poll() is None, f"{spec.id} exited early"


def test_nicegui_clients_own_independent_figures(page):
    spec = _nicegui_example()
    with running_example(spec) as (base_url, proc):
        other_page = page.context.new_page()
        try:
            page.goto(base_url, wait_until="load")
            other_page.goto(base_url, wait_until="load")
            first_canvas = _nicegui_canvas(page, "plot-one")
            other_canvas = _nicegui_canvas(other_page, "plot-one")
            first_canvas.wait_for(state="visible", timeout=15000)
            other_canvas.wait_for(state="visible", timeout=15000)
            page.wait_for_timeout(int(SETTLE_SECONDS * 1000))
            first_before = first_canvas.evaluate("el => el.toDataURL('image/png')")
            other_before = other_canvas.evaluate("el => el.toDataURL('image/png')")

            assert page.locator(".plot-one").get_attribute("data-figure-id") != other_page.locator(
                ".plot-one"
            ).get_attribute("data-figure-id")
            page.get_by_role("button", name="Update first").click()
            _wait_for_canvas_change(
                page,
                "plot-one",
                first_before,
            )
            assert other_canvas.evaluate("el => el.toDataURL('image/png')") == other_before
        finally:
            other_page.close()
        assert proc.poll() is None, f"{spec.id} exited early"


def test_nicegui_delete_and_disconnect_release_managers(page):
    spec = _nicegui_example()
    browser_errors = []
    page.on("console", lambda message: browser_errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: browser_errors.append(str(error)))
    with running_example(spec) as (base_url, proc):
        page.goto(base_url, wait_until="load")
        first = _nicegui_canvas(page, "plot-one")
        second = _nicegui_canvas(page, "plot-two")
        first.wait_for(state="visible", timeout=15000)
        second.wait_for(state="visible", timeout=15000)
        first_id = page.locator(".plot-one").get_attribute("data-figure-id")
        second_id = page.locator(".plot-two").get_attribute("data-figure-id")
        assert first_id and second_id

        page.get_by_role("button", name="Delete first").click()
        page.locator(".plot-one").wait_for(state="detached", timeout=15000)
        page.wait_for_timeout(500)
        assert page.request.get(f"{base_url}/webagg/download/{first_id}.png").status == 404

        page.goto("about:blank")
        page.wait_for_timeout(500)
        assert page.request.get(f"{base_url}/webagg/download/{second_id}.png").status == 404
        assert not browser_errors
        assert proc.poll() is None, f"{spec.id} exited early"


def test_popup_spawn_dismiss_respawn(page):
    """
    For the popup example specifically: clicking the in-figure button spawns
    a popup dialog, clicking away from the popup dismisses it (removing the
    dialog from the DOM entirely), and clicking the button again spawns
    another popup.
    """
    spec = next(s for s in EXAMPLES if s.id == "starlette-demo_popup")
    with running_example(spec) as (base_url, proc):
        page.goto(base_url + "/", wait_until="load")
        root = page.locator(".mpl-figure-root").first
        canvas = _canvas_for_root(root)
        canvas.wait_for(state="visible", timeout=15000)
        page.wait_for_timeout(int(SETTLE_SECONDS * 1000))

        for round_num in range(2):
            label = f"{spec.id} round {round_num}"
            assert page.locator("dialog").count() == 0, (
                f"{label}: a dialog is present before clicking the button"
            )

            # The Button widget fills the figure's only Axes, so a click in
            # the middle of the canvas lands on it.
            box = canvas.bounding_box()
            assert box is not None, f"{label}: main canvas has no bounding box"
            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

            dialog = page.locator("dialog[open]")
            dialog.wait_for(state="visible", timeout=15000)
            popup_canvas = dialog.locator("canvas.mpl-canvas")
            popup_canvas.wait_for(state="visible", timeout=15000)
            # Besides letting the canvas render, this also gets us past the
            # ~1s window after showModal() during which mk_modal suppresses
            # light dismissal (to swallow the mouseup of the opening click).
            page.wait_for_timeout(int(SETTLE_SECONDS * 1000))
            assert not _is_blank(_canvas_png_bytes(popup_canvas)), (
                f"{label}: popup canvas is blank"
            )

            # Click away from the popup: pick a viewport corner that is
            # outside the dialog's box (it sits top-centre, so the bottom
            # corners normally qualify).
            viewport = page.viewport_size
            dialog_box = dialog.bounding_box()
            assert dialog_box is not None, f"{label}: dialog has no bounding box"

            def outside_dialog(x, y):
                return not (
                    dialog_box["x"] <= x <= dialog_box["x"] + dialog_box["width"]
                    and dialog_box["y"] <= y <= dialog_box["y"] + dialog_box["height"]
                )

            corners = [
                (10, viewport["height"] - 10),
                (viewport["width"] - 10, viewport["height"] - 10),
                (viewport["width"] - 10, 10),
                (10, 10),
            ]
            away = next((p for p in corners if outside_dialog(*p)), None)
            assert away is not None, f"{label}: dialog covers the whole viewport"
            page.mouse.click(*away)

            # Dismissal closes the figure's websocket, which removes the
            # dialog from the DOM entirely (on_close="remove_dialog").
            dialog.wait_for(state="detached", timeout=15000)
            assert page.locator("dialog").count() == 0, (
                f"{label}: dialog still in DOM after clicking away"
            )

        assert proc.poll() is None, f"{spec.id} exited early"


def test_mne_help_popup_reopens(page):
    """
    For the integrate_mne example: pressing '?' over the raw-browser figure
    spawns MNE's help window as a popup dialog, dismissing it removes the
    dialog, and pressing '?' again spawns it again.
    """
    spec = next(s for s in EXAMPLES if s.id == "starlette-integrate_mne")
    if spec.requires_mne_data and not mne_sample_data_available():
        pytest.skip("MNE sample dataset not available locally")
    with running_example(spec) as (base_url, proc):
        page.goto(base_url + "/", wait_until="load")
        root = page.locator(".mpl-figure-root").first
        canvas = _canvas_for_root(root)
        canvas.wait_for(state="visible", timeout=15000)
        page.wait_for_timeout(int(SETTLE_SECONDS * 1000))

        for round_num in range(2):
            label = f"{spec.id} round {round_num}"
            assert page.locator("dialog").count() == 0, (
                f"{label}: a dialog is present before opening help"
            )

            # The canvas grabs keyboard focus on mouseover, so hovering it is
            # enough for '?' to reach MNE's keypress handler server-side. Raw
            # mouse coordinates are used because the rubberband layer stacked
            # on top of the canvas intercepts pointer actions like hover().
            box = canvas.bounding_box()
            assert box is not None, f"{label}: canvas has no bounding box"
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.keyboard.press("?")

            dialog = page.locator("dialog[open]")
            dialog.wait_for(state="visible", timeout=15000)
            popup_canvas = dialog.locator("canvas.mpl-canvas")
            popup_canvas.wait_for(state="visible", timeout=15000)
            # Also gets us past the ~1s window after showModal() during which
            # mk_modal suppresses cancellation.
            page.wait_for_timeout(int(SETTLE_SECONDS * 1000))
            assert not _is_blank(_canvas_png_bytes(popup_canvas)), (
                f"{label}: help popup canvas is blank"
            )

            # Dismiss the dialog; its websocket closes and
            # on_close="remove_dialog" removes it from the DOM entirely.
            page.keyboard.press("Escape")
            dialog.wait_for(state="detached", timeout=15000)
            assert page.locator("dialog").count() == 0, (
                f"{label}: dialog still in DOM after Escape"
            )

        assert proc.poll() is None, f"{spec.id} exited early"
