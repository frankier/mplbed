# Implementation Plan: NiceGUI Integration

## Overview

Add an optional NiceGUI element that owns one Matplotlib WebAgg figure, reuses mplbed's Starlette routing and figure registry, and wires browser and server lifecycle cleanup without changing core integration contracts.

## Architecture Decisions

- Configure an explicit mplbed Starlette sub-app in `setup` so NiceGUI head assets and element WebSocket URLs use the exact configured prefix and router.
- Implement a small NiceGUI Vue component whose only responsibility is creating and closing the existing `_mpl_webaggext` figure inside its own DOM node.
- Keep figure creation, manager registration, redraw, and cleanup in the Python element; reuse the existing mplbed manager registry rather than adding another registry.
- Keep all NiceGUI imports inside `mplbed.integration.nicegui` so the core package remains importable without the optional dependency.

## Task List

### Phase 1: Foundation and contract

- [x] Task 1: Add NiceGUI optional/development metadata and inspect the pinned 3.15 API.
- [x] Task 2: Add failing unit tests for setup, element ownership, context redraw, explicit redraw, and cleanup.

### Checkpoint: Foundation

- [x] Focused unit tests demonstrate the missing behavior and dependency metadata is valid.

### Phase 2: Live integration

- [x] Task 3: Implement setup, the owned figure element, and lifecycle cleanup.
- [x] Task 4: Add the lifecycle-only Vue component and in-process integration tests.
- [x] Task 5: Add the NiceGUI example and browser tests for rendering, update-without-replacement, independence, pan, and cleanup.

### Checkpoint: Integration

- [x] NiceGUI-focused unit and browser tests pass.

### Phase 3: Documentation and release gates

- [x] Task 6: Update README, API docs, examples docs, and example launcher support.
- [x] Task 7: Run full tests, lint, formatting, typecheck, docs, build, and packaging/import-isolation checks.
- [x] Task 8: Review the full diff for correctness, architecture, security, performance, and scope; address required findings.

### Checkpoint: Complete

- [x] All spec acceptance criteria and repository quality gates pass.
- [x] Changes are committed in reviewable increments and ready for human review.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| NiceGUI reconnect/delete semantics close a live figure too early | High | Use NiceGUI 3.15's documented delete lifecycle for terminal cleanup and cover reconnect/disconnect behavior in browser tests. |
| Component mount races with mplbed asset loading | High | Register scripts in the shared page head during `setup` and test the real browser startup path. |
| A redraw before WebSocket connection is lost | High | Keep `draw_idle` state on the existing WebAgg canvas and verify the first connected client receives the latest state. |
| Optional dependency leaks into core imports | Medium | Confine imports to the integration module and test core import with NiceGUI unavailable. |
| Manager/WebSocket resources leak | High | Make cleanup idempotent on both element deletion and client deletion, then assert registry removal and clean browser console output. |

## Open Questions

None; the source spec explicitly resolves the first-version scope.
