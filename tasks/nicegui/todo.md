# NiceGUI Integration Tasks

## Task 1: Package and verify NiceGUI 3.15

**Acceptance criteria:**
- [x] `nicegui>=3.15.0` exists only in the `nicegui` extra and development/docs environments.
- [x] The lockfile resolves and plain mplbed metadata does not require NiceGUI.

**Verification:** `uv lock --check` and package metadata tests.

**Dependencies:** None.

## Task 2: Specify the Python API with tests

**Acceptance criteria:**
- [x] Tests cover setup delegation/assets/idempotency and actionable pre-setup errors.
- [x] Tests cover owned figures, forwarded kwargs, context redraw, explicit redraw, chaining, and idempotent cleanup.

**Verification:** `uv run pytest tests/test_nicegui.py`.

**Dependencies:** Task 1.

## Task 3: Implement the live element path

**Acceptance criteria:**
- [x] `setup`, `matplotlib`, and `Matplotlib` implement the public contract.
- [x] The Vue component mounts one existing mplbed WebAgg figure and closes it on unmount.
- [x] Server managers are released when the element or client is deleted.

**Verification:** NiceGUI unit/integration tests pass.

**Dependencies:** Task 2.

## Checkpoint: Core API

- [x] Focused tests pass.
- [x] Lint and typecheck pass for changed source.

## Task 4: Prove browser behavior

**Acceptance criteria:**
- [x] Browser tests cover rendering, toolbar pan, live update without DOM replacement, independent plots, and cleanup.
- [x] No browser console errors occur during deletion/disconnect.

**Verification:** `uv run pytest tests/test_e2e.py -k nicegui`.

**Dependencies:** Task 3.

## Task 5: Document and package the integration

**Acceptance criteria:**
- [x] README, API docs, examples docs, runnable example, and harness match the public API.
- [x] Built wheel exposes the optional extra and includes the component asset.

**Verification:** Sphinx build, distribution build, and artifact inspection pass.

**Dependencies:** Task 3.

## Task 6: Complete quality gates and review

**Acceptance criteria:**
- [x] Full tests, lint, format, typecheck, docs, and build pass.
- [x] Five-axis code review has no unresolved required findings.

**Verification:** Run every command listed in the spec.

**Dependencies:** Tasks 4 and 5.
