# Request flow control

## Status

Accepted.

## Context

Matplotlib's WebAgg client sends a request for every observed resize and mouse
motion. A complex figure can render more slowly than the browser produces
resize or pan-drag requests, so the WebSocket and server event loop accumulate
obsolete work. Once interaction stops, the user must wait for every
intermediate state to render before seeing the final state.

The useful properties of a request are not captured by FIFO delivery alone:

- Some requests have a known completion message and can use completion-based
  flow control.
- Some pending requests are invalidated by newer requests of the same kind.
- Some unpaired event streams can be sampled or reduced at a configured rate.
- Some events must remain lossless and should be sent without an arbitrary
  pacing delay.

The browser and server are shipped together, so this design treats their
protocol as one implementation. It does not add version negotiation.

## Goals

- Keep resize and pan work bounded while always rendering the final state.
- Describe request behavior declaratively rather than hard-coding a resize-only
  debounce.
- Support completion-based maximum-in-flight limits.
- Support optional leading-and-trailing throttling for unpaired motion and
  scroll events.
- Preserve causal ordering for lossless input events.
- Keep the defaults useful without configuration.

## Non-goals

- Multiple viewers connected to one figure manager.
- Server-to-browser frame backpressure or acknowledgement after browser paint.
- Protocol negotiation between independently versioned clients and servers.
- Anti-abuse limits, connection quotas, or hostile-client handling.
- Cancelling a Matplotlib draw that has already started.
- Coalescing non-pan motion or scroll events by default.

## Request semantics

Known request types are assigned a policy:

```text
RequestPolicy:
    retention:      all | latest | reduce
    completion:     none | <request-type>_completion
    max_in_flight:  positive integer | unlimited
    throttle_ms:    positive integer | disabled
    ordering:       ordered | bypass
    coalesce_across_barriers: yes | no
```

`retention` applies only to requests that have not been sent:

- `all` retains every request.
- `latest` keeps one pending request and replaces its payload in place.
- `reduce` keeps one pending request and combines new values into it.

Unknown request types use `all`, no completion, no throttle, and `ordered`.
This is conservative: extensions must opt into lossy behavior explicitly.

Initial policies are:

| Request | Retention | Completion | Maximum in flight | Throttle | Ordering |
|---|---|---|---:|---:|---|
| `resize` | latest | `resize_completion` | 1 | disabled | ordered |
| pan `motion_notify` | latest | `motion_notify_completion` | 1 | disabled | ordered |
| other `motion_notify` | all | none | unlimited | disabled | ordered |
| `scroll` | all | none | unlimited | disabled | ordered |
| `refresh` | latest | none | unlimited | disabled | ordered |
| button, key, and toolbar events | all | none | unlimited | disabled | ordered |
| `ack` and connection maintenance | latest | none | unlimited | disabled | bypass |
| `close` | terminal | connection close | 1 | disabled | bypass |

Resize, pan motion, and refresh set `coalesce_across_barriers`; the other
policies do not.

The client tracks `navigate_mode` from Matplotlib's `navigate_mode` message.
Button-held motion in `PAN` mode uses completion control; hover motion and
motion in other navigation modes remain ordinary motion. Motion and scroll
throttling become active only when their respective `throttle_ms` value is
configured. With the default disabled value, non-pan motion and scroll retain
and send every event.

For motion, coalescing replaces the pending event with the latest coordinates
and button/modifier state. For scroll, reduction adds the pending and incoming
`step` values while retaining the latest coordinates and modifier state. This
preserves total scroll distance better than dropping intermediate deltas.

Pan coalescing is enabled by default because intermediate drag positions are
invalidated by the latest position and each position can trigger a render.
Coalescing other motion changes observable callback behavior: application
callbacks receive sampled events rather than every browser event. That is why
non-pan motion throttling remains opt-in.

## Client scheduler

The scheduler sits around `mpl.figure.prototype.send_message` in
`webaggext.js`. It owns an ordered queue, in-flight counts by request type, and
optional throttle state.

### Completion-controlled requests

Resize ignores zero-width or zero-height observations without discarding the
last pending non-zero size. Resize and pan `motion_notify` otherwise follow the
same completion-controlled steps:

1. If fewer than `max_in_flight` requests of that type are outstanding,
   allocate a connection-local monotonically increasing `seq` and send the
   request immediately.
2. Otherwise retain one pending request. Each later request of the same type
   replaces that pending payload in place.
3. On the matching completion, remove `seq` from that type's in-flight set and
   immediately send its latest pending request, if present.

Sequence numbers are allocated only when a request is sent. Locally replaced
requests therefore do not need a completion. Sequence state is discarded when
the WebSocket closes, so no session identifier is needed.

Example request and completion:

```json
{"type": "resize", "figure_id": 12, "width": 900, "height": 600, "seq": 17}
```

```json
{"type": "resize_completion", "seq": 17}
```

Pan motion uses the same shape with request type `motion_notify` and completion
type `motion_notify_completion`. A motion request only enters this policy when
the client is in PAN mode and at least one mouse button is held.

Completion message names follow the `<request-type>_completion` convention.
Apart from the required `type`, a completion contains only `seq`.

### Throttled requests without completion

A positive `throttle_ms` enables leading-and-trailing throttling independently
for motion or scroll:

1. The first event in an idle period is sent immediately.
2. A timer starts for `throttle_ms`.
3. Events arriving before the timer expires update one pending entry in place.
4. At expiry, the pending event is sent and another interval starts if events
   continue to arrive.
5. If no event is pending at expiry, the stream becomes idle and the next event
   is again sent immediately.

This bounds a sustained stream to approximately one request per interval
without imposing a leading-edge delay.

A lossless ordered event acts as a barrier. Before sending a mouse release,
button press, key event, or toolbar event, the scheduler flushes any earlier
pending throttled event. For example, a pending drag motion must not be sent
after the corresponding mouse release.

### Ordering

Coalescing replaces an entry at its existing queue position; it does not drop
or move intervening events. Resize, pan motion, and refresh may find and replace
their pending entry across such events. This prevents drag-related
`motion_notify`, `button_release`, and `figure_leave` traffic from splitting a
resize backlog, and prevents refresh requests from accumulating. Other
coalescing policies stop at a lossless ordered barrier.

`bypass` is reserved for connection maintenance and termination. Ordinary
interactive events do not gain numeric priorities because reordering a click
ahead of a resize can make Matplotlib interpret its coordinates against stale
figure geometry.

Requests that are neither completion-controlled nor throttled are passed
through immediately whenever preceding ordered work permits it. They do not
wait for a fixed debounce or rate-limit timer.

## Server completion behavior

The server continues to process requests in WebSocket order. It treats `seq`
as transport metadata; Matplotlib handlers may otherwise process the message
normally.

When a resize or pan motion with `seq` schedules a delayed draw, the server
records its request type and sequence as waiting for an image. After the draw
has finished and the updated binary image has been sent, it sends the matching
completion:

```text
receive resize(seq=17)
    -> apply figure size and resize callbacks
    -> draw updated figure
    -> send binary image
    -> send resize_completion(seq=17)
```

WebSocket message ordering guarantees that the image is placed on the outgoing
stream before its completion. No browser-to-server frame acknowledgement is
required. Completion therefore means "the server finished the requested draw
and sent its updated image", not "the browser painted the image".

The delayed-draw path retains request-type/sequence pairs associated with the
dirty state. If several completion-controlled operations are folded into one
draw, the server sends each matching completion after that shared image, in
request order. If processing a completion-controlled request schedules no
draw, the server completes it immediately so client capacity cannot deadlock.

If handling or drawing fails, the normal WebSocket error/close path clears the
client scheduler. This design does not introduce a separate error-completion
message.

## Configuration

Defaults:

```text
resize_max_in_flight = 1
motion_throttle_ms = disabled
scroll_throttle_ms = disabled
```

The app factory should accept these flow-control options and expose them to the
served `webaggext.js` client. `None` disables a throttle; positive integer
values enable it. Zero and negative values are invalid rather than aliases for
disabled behavior.

`resize_max_in_flight` remains configurable for experimentation, but one is the
default because it provides direct render backpressure and permits unambiguous
request/completion pairing.

## Why not use only a debounce or rate limit?

A trailing debounce delays the first response and can prevent updates during a
continuous resize. A fixed requests-per-second limit also cannot adapt to the
difference between a cheap plot and a multi-second render.

Completion-controlled pacing sends the first request immediately and adapts to
the actual server render time. The one pending latest value provides
backpressure without accumulating obsolete work. Time-based throttling remains
useful for non-pan motion and scroll, which do not have completion messages.

## Implementation plan

### 1. Add the client policy registry and scheduler

- Add the policy representation and defaults to `webaggext.js`.
- Route `mpl.figure.prototype.send_message` through the scheduler.
- Preserve the original raw-send function for scheduler dispatch.
- Add connection-local sequence allocation and in-flight tracking.
- Add completion handlers that replenish resize and pan-motion capacity.
- Clear timers, pending entries, and in-flight state when the socket closes.

Verification:

- The first resize or pan motion is sent immediately.
- While it is in flight, any number of matching requests occupy one pending slot.
- Its completion sends exactly the latest pending state.
- A mismatched or duplicate completion does not release unrelated capacity.

### 2. Emit request completions after the image

- Carry completion-controlled request types and `seq` values through
  `handle_websocket` and the delayed-draw path.
- Associate request-type/sequence pairs with the dirty draw that incorporates
  them.
- Send each completion only after `draw()` returns and its binary image has
  been sent.
- Preserve current behavior for messages without completion semantics.

Verification:

- Captured WebSocket output orders the binary image before
  `resize_completion`.
- The completion echoes the request sequence exactly.
- No completion is emitted before rendering or for an unsent/coalesced client
  request.

### 3. Add optional motion and scroll throttling

- Implement the leading-and-trailing timer behavior.
- Replace motion payloads and reduce scroll deltas as described above.
- Flush pending throttled input before a later lossless ordering barrier.
- Keep both throttles disabled by default.

Verification:

- An enabled throttle sends the leading event immediately.
- A burst produces at most one trailing event per interval.
- Motion uses the latest state; scroll preserves the summed step.
- Mouse release cannot overtake a pending motion event.
- With throttling disabled, existing event counts and ordering are unchanged.

### 4. Plumb configuration and document the API

- Add typed flow-control options to `mplbed_app_factory`.
- Make the configured values available when serving the client extension.
- Document defaults, valid values, and the callback sampling consequences.

Verification:

- All integrations inherit the defaults without changes.
- App-factory overrides reach the browser.
- Invalid throttle and in-flight values fail during app construction.

### 5. Add end-to-end resize- and pan-storm tests

- Use a deliberately slow or instrumented draw.
- Generate many resize observations or pan motions before one draw completes.
- Record handled requests and completion ordering.
- Confirm ordinary button, key, and non-pan motion interactions still work.

Verification:

- At most one resize is active and one is pending on the client.
- At most one pan motion is active and one is pending on the client.
- Intermediate resize count does not create a proportional render backlog.
- Once input stops, the final non-zero size is rendered.
- The canvas remains interactive after the storm.

## Acceptance criteria

- Resize queue storage remains constant during a resize storm.
- The first resize is sent without delay.
- The final non-zero requested size is eventually rendered after healthy draws
  complete.
- Every sent resize has one matching `resize_completion` with the same `seq`,
  sent after its updated image.
- Every sent pan motion has one matching `motion_notify_completion` with the
  same `seq`; it follows the updated image when a draw was scheduled, or follows
  request processing when no draw was needed.
- Superseded, unsent resize values are never rendered and require no
  completion.
- Intervening ordered events are neither dropped nor moved when resize, pan,
  or refresh requests coalesce across them.
- Motion and scroll throttling are disabled by default and independently
  configurable in milliseconds.
- Enabling throttling preserves leading-edge responsiveness and produces a
  trailing coalesced event.
- Existing applications require no configuration changes.
