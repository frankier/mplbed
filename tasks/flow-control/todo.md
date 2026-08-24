# Request Flow-Control Tasks

## Task 1: Specify and implement server completions

**Acceptance criteria:**
- [x] App-factory values are validated and embedded in the generated client bundle.
- [x] Each sent resize sequence completes after the binary image that incorporates it.
- [x] Existing messages without sequence metadata retain current behavior.

**Verification:** Focused Python tests for configuration and delayed drawing.

**Dependencies:** None.

## Task 2: Specify and implement the client scheduler

**Acceptance criteria:**
- [x] Resize work is one in flight plus the latest pending value by default.
- [x] Only matching completions replenish capacity; close clears connection-local state.
- [x] Optional motion/scroll throttles are leading-and-trailing, with latest motion, reduced scroll, and ordered barriers.

**Verification:** Deterministic JavaScript scheduler tests executed from pytest.

**Dependencies:** Task 1.

## Checkpoint: Core behavior

- [x] Focused Python and JavaScript tests pass.

## Task 3: Integrate and document

**Acceptance criteria:**
- [x] Default applications require no changes and remain lossless for motion/scroll.
- [x] Public docs describe defaults, valid values, and sampling consequences.
- [x] The ADR records the implemented decision.

**Verification:** Integration tests and Sphinx build.

**Dependencies:** Tasks 1 and 2.

## Task 4: Complete quality gates and PR

**Acceptance criteria:**
- [x] Full tests, lint, format check, typecheck, docs, and review pass.
- [x] Atomic commits are pushed and a PR targeting `main` is open.

**Verification:** Repository quality commands, staged-diff review, and PR URL.

**Dependencies:** Task 3.
