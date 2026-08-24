# Implementation Plan: Request Flow Control

## Overview

Implement the accepted flow-control design around the browser's WebAgg request path, complete resize requests only after their rendered image is sent, and expose opt-in motion and scroll throttles through the existing app factory.

## Architecture Decisions

- Keep scheduling connection-local in `webaggext.js`, with the original `send_message` retained as the raw transport.
- Inject validated factory configuration into the generated `mpl.js` bundle so every integration inherits the same behavior.
- Associate resize sequence numbers with the delayed dirty draw and emit completions synchronously after Matplotlib sends its binary image.
- Preserve queue position across coalescing and treat lossless ordered input as a flush barrier for throttled events.

## Task List

### Phase 1: Contracts and server completion

- [x] Task 1: Specify factory validation, bundle configuration, and image-before-completion behavior with tests.
- [x] Task 2: Implement validated flow-control configuration and delayed-draw completion tracking.

### Checkpoint: Server

- [x] Focused server/configuration tests pass.

### Phase 2: Client scheduling

- [x] Task 3: Specify resize backpressure, completion matching, throttling, reduction, barriers, bypass, and cleanup with client tests.
- [x] Task 4: Implement the policy registry and connection-local scheduler.

### Checkpoint: Client

- [x] Client tests and focused integration tests pass.

### Phase 3: Documentation and release gates

- [x] Task 5: Document the factory API, defaults, validation, and callback sampling effects; accept the ADR.
- [x] Task 6: Run full tests, lint, format check, typecheck, docs build, and a five-axis diff review.
- [x] Task 7: Commit, push, and open a PR against `main`.

### Checkpoint: Complete

- [x] All ADR acceptance criteria and repository quality gates pass.
- [x] Changes are committed in reviewable increments and submitted for human review.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| A completion is emitted before its image | High | Test captured worker-socket ordering around a real canvas draw path. |
| Coalescing reorders a lossless input event | High | Model ordered barriers explicitly and test resize/motion sequences on both sides of them. |
| Timers survive socket closure | Medium | Centralize scheduler cleanup and cover timer/queue reset. |
| Configuration diverges across integrations | Medium | Keep all options on the shared app factory and generated bundle. |

## Open Questions

None; `design/flow-control.md` and the implementation assumptions define the first-version behavior.
