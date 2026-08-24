import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

globalThis.window = globalThis;
globalThis.mpl = {
    figure: function Figure() {},
    flow_control: {
        resize_max_in_flight: 1,
        motion_throttle_ms: null,
        scroll_throttle_ms: null,
    },
    get_websocket_type() {
        return function WebSocket() {};
    },
};
mpl.figure.prototype.send_message = function(type, properties) {
    properties.type = type;
    properties.figure_id = this.id;
    this.ws.send(JSON.stringify(properties));
};

vm.runInThisContext(fs.readFileSync("src/mplbed/webaggext/webaggext.js", "utf8"));

function figure(config = {}) {
    Object.assign(mpl.flow_control, {
        resize_max_in_flight: 1,
        motion_throttle_ms: null,
        scroll_throttle_ms: null,
        ...config,
    });
    const sent = [];
    const closeListeners = [];
    const fig = Object.create(mpl.figure.prototype);
    fig.id = 12;
    fig.ws = {
        send(payload) {
            sent.push(JSON.parse(payload));
        },
        addEventListener(type, callback) {
            if (type === "close") closeListeners.push(callback);
        },
    };
    return {fig, sent, close: () => closeListeners.forEach((callback) => callback())};
}

const delay = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

test("resize sends immediately and retains only the latest non-zero pending size", () => {
    const {fig, sent} = figure();
    fig.send_message("resize", {width: 100, height: 100});
    fig.send_message("resize", {width: 200, height: 200});
    fig.send_message("resize", {width: 0, height: 300});
    fig.send_message("resize", {width: 300, height: 300});

    assert.deepEqual(sent, [{type: "resize", figure_id: 12, width: 100, height: 100, seq: 1}]);
    fig.handle_resize_completion(fig, {type: "resize_completion", seq: 999});
    assert.equal(sent.length, 1);
    fig.handle_resize_completion(fig, {type: "resize_completion", seq: 1});
    assert.deepEqual(sent[1], {type: "resize", figure_id: 12, width: 300, height: 300, seq: 2});
    fig.handle_resize_completion(fig, {type: "resize_completion", seq: 1});
    assert.equal(sent.length, 2);
});

test("ordered barriers keep resize coalescing within its causal segment", () => {
    const {fig, sent} = figure();
    fig.send_message("resize", {width: 100, height: 100});
    fig.send_message("resize", {width: 200, height: 200});
    fig.send_message("button_release", {button: 0});
    fig.send_message("resize", {width: 300, height: 300});

    fig.handle_resize_completion(fig, {seq: 1});
    assert.deepEqual(sent.map((message) => message.type), ["resize", "resize", "button_release"]);
    fig.handle_resize_completion(fig, {seq: 2});
    assert.deepEqual(sent.map((message) => message.type), ["resize", "resize", "button_release", "resize"]);
});

test("configured resize capacity allocates sequences only to sent requests", () => {
    const {fig, sent} = figure({resize_max_in_flight: 2});
    fig.send_message("resize", {width: 100, height: 100});
    fig.send_message("resize", {width: 200, height: 200});
    fig.send_message("resize", {width: 300, height: 300});
    fig.send_message("resize", {width: 400, height: 400});

    assert.deepEqual(sent.map((message) => message.seq), [1, 2]);
    fig.handle_resize_completion(fig, {seq: 1});
    assert.deepEqual(sent.map((message) => message.seq), [1, 2, 3]);
    assert.equal(sent[2].width, 400);
});

test("motion and scroll remain lossless when throttles are disabled", () => {
    const {fig, sent} = figure();
    fig.send_message("motion_notify", {x: 1});
    fig.send_message("motion_notify", {x: 2});
    fig.send_message("scroll", {x: 1, step: 2});
    fig.send_message("scroll", {x: 2, step: 3});
    assert.deepEqual(sent.map((message) => message.x), [1, 2, 1, 2]);
});

test("motion throttle sends a leading event and the latest trailing event", async () => {
    const {fig, sent} = figure({motion_throttle_ms: 15});
    fig.send_message("motion_notify", {x: 1});
    fig.send_message("motion_notify", {x: 2});
    fig.send_message("motion_notify", {x: 3});
    assert.deepEqual(sent.map((message) => message.x), [1]);
    await delay(30);
    assert.deepEqual(sent.map((message) => message.x), [1, 3]);
});

test("scroll reduction preserves distance and flushes before a lossless barrier", () => {
    const {fig, sent, close} = figure({scroll_throttle_ms: 1000});
    fig.send_message("scroll", {x: 1, step: 1, modifiers: []});
    fig.send_message("scroll", {x: 2, step: 2, modifiers: ["shift"]});
    fig.send_message("scroll", {x: 3, step: -1, modifiers: ["ctrl"]});
    fig.send_message("button_release", {button: 0});

    assert.deepEqual(sent.map((message) => message.type), ["scroll", "scroll", "button_release"]);
    assert.equal(sent[1].step, 1);
    assert.equal(sent[1].x, 3);
    assert.deepEqual(sent[1].modifiers, ["ctrl"]);
    close();
});

test("close bypasses blocked work and clears scheduler state", () => {
    const {fig, sent, close} = figure();
    fig.send_message("resize", {width: 100, height: 100});
    fig.send_message("resize", {width: 200, height: 200});
    fig.send_message("close", {});
    close();
    fig.handle_resize_completion(fig, {seq: 1});
    assert.deepEqual(sent.map((message) => message.type), ["resize", "close"]);
});

test("socket closure cancels throttled trailing work", async () => {
    const {fig, sent, close} = figure({motion_throttle_ms: 15});
    fig.send_message("motion_notify", {x: 1});
    fig.send_message("motion_notify", {x: 2});
    close();
    await delay(30);
    assert.deepEqual(sent.map((message) => message.x), [1]);
});
