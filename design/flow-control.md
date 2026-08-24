# Request flow control

## Status

Proposed.

## Context

Matplotlib's WebAgg client sends a request for every observed resize. A complex
figure can render more slowly than the browser produces these requests, so the
WebSocket and server event loop accumulate obsolete work. Once resizing stops,
the user must wait for every intermediate size to render before seeing the
final size.

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

- Keep resize work bounded while always rendering the final non-zero size.
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
- Coalescing motion or scroll events by default.

## Request semantics

Known request types are assigned a policy:

```text
RequestPolicy:
    retention:      all | latest | reduce
    completion:     none | <request-type>_completion
    max_in_flight:  positive integer | unlimited
    throttle_ms:    positive integer | disabled
    ordering:       ordered | bypass
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
| `motion_notify` | latest | none | unlimited | disabled | ordered |
| `scroll` | reduce | none | unlimited | disabled | ordered |
| button, key, and toolbar events | all | none | unlimited | disabled | ordered |
| `ack` and connection maintenance | latest | none | unlimited | disabled | bypass |
| `close` | terminal | connection close | 1 | disabled | bypass |

Motion and scroll coalescing become active only when their respective
`throttle_ms` value is configured. With the default disabled value, both retain
and send every event exactly as they do now.

For motion, coalescing replaces the pending event with the latest coordinates
and button/modifier state. For scroll, reduction adds the pending and incoming
`step` values while retaining the latest coordinates and modifier state. This
preserves total scroll distance better than dropping intermediate deltas.

Coalescing changes observable callback behavior: when enabled, application
callbacks receive sampled motion events or aggregated scroll events rather
than every browser event. That is why it is opt-in.

## Client scheduler

The scheduler sits around `mpl.figure.prototype.send_message` in
`webaggext.js`. It owns an ordered queue, in-flight counts by request type, and
optional throttle state.

### Completion-controlled requests

For `resize`:

1. Ignore zero-width or zero-height observations without discarding the last
   pending non-zero size.
2. If fewer than `max_in_flight` resize requests are outstanding, allocate a
   connection-local monotonically increasing `seq` and send the resize
   immediately.
3. Otherwise retain one pending resize. Each later resize replaces that
   pending payload in place.
4. On `resize_completion`, match `seq`, remove that request from the in-flight
   set, and immediately send the latest pending resize, if present.

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

Coalescing replaces an entry at its existing queue position; it does not move
the newest event ahead of intervening ordered requests. A matching request can
be replaced only when no lossless ordered event separates the two.

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

When a resize with `seq` schedules a delayed draw, the server records that
sequence as waiting for an image. After the draw has finished and the updated
binary image has been sent, it sends the matching completion:

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

The delayed-draw path must retain the sequence numbers associated with the
dirty state. If several future completion-controlled operations are folded
into one draw, the server sends each matching completion after that shared
image, in request order. The initial resize policy allows only one resize in
flight, so this is primarily an extension rule.

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
useful for streams such as motion and scroll that do not have completion
messages.

## Implementation plan

### 1. Add the client policy registry and scheduler

- Add the policy representation and defaults to `webaggext.js`.
- Route `mpl.figure.prototype.send_message` through the scheduler.
- Preserve the original raw-send function for scheduler dispatch.
- Add connection-local sequence allocation and in-flight tracking.
- Add a `resize_completion` handler that replenishes resize capacity.
- Clear timers, pending entries, and in-flight state when the socket closes.

Verification:

- The first resize is sent immediately.
- While it is in flight, any number of resizes occupy one pending slot.
- Its completion sends exactly the latest pending size.
- A mismatched or duplicate completion does not release unrelated capacity.

### 2. Emit resize completion after the image

- Carry the resize `seq` through `handle_websocket` and the delayed-draw path.
- Associate completion sequences with the dirty draw that incorporates them.
- Send `resize_completion` only after `draw()` returns and its binary image has
  been sent.
- Preserve current behavior for messages without completion semantics.

Verification:

- Captured WebSocket output orders the binary image before
  `resize_completion`.
- The completion echoes the request sequence exactly.
- No completion is emitted before rendering or for an unsent/coalesced client
  resize.

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

### 5. Add an end-to-end resize-storm test

- Use a deliberately slow or instrumented draw.
- Generate many resize observations before one draw completes.
- Record handled resize sizes and completion ordering.
- Confirm ordinary button, key, and pan interactions still work.

Verification:

- At most one resize is active and one is pending on the client.
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
- Superseded, unsent resize values are never rendered and require no
  completion.
- Lossless ordered events are neither dropped nor moved across pending events.
- Motion and scroll throttling are disabled by default and independently
  configurable in milliseconds.
- Enabling throttling preserves leading-edge responsiveness and produces a
  trailing coalesced event.
- Existing applications require no configuration changes.
