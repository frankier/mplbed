(function() {

const raw_send_message = mpl.figure.prototype.send_message;

const FLOW_CONTROL_DEFAULTS = {
    resize_max_in_flight: 1,
    motion_throttle_ms: null,
    scroll_throttle_ms: null,
};

const REQUEST_POLICIES = {
    resize: {
        retention: "latest",
        completion: "resize_completion",
        max_in_flight: "resize_max_in_flight",
        throttle_ms: null,
        ordering: "ordered",
    },
    motion_notify: {
        retention: "latest",
        completion: null,
        max_in_flight: null,
        throttle_ms: "motion_throttle_ms",
        ordering: "ordered",
    },
    scroll: {
        retention: "reduce",
        completion: null,
        max_in_flight: null,
        throttle_ms: "scroll_throttle_ms",
        ordering: "ordered",
    },
    ack: {
        retention: "latest",
        completion: null,
        max_in_flight: null,
        throttle_ms: null,
        ordering: "bypass",
    },
    close: {
        retention: "terminal",
        completion: null,
        max_in_flight: 1,
        throttle_ms: null,
        ordering: "bypass",
    },
};

for (const type of ["supports_binary", "send_image_mode", "set_device_pixel_ratio"]) {
    REQUEST_POLICIES[type] = REQUEST_POLICIES.ack;
}

const DEFAULT_POLICY = {
    retention: "all",
    completion: null,
    max_in_flight: null,
    throttle_ms: null,
    ordering: "ordered",
};

class RequestScheduler {
    constructor(fig) {
        this.fig = fig;
        this.config = {...FLOW_CONTROL_DEFAULTS, ...(mpl.flow_control || {})};
        this.queue = [];
        this.in_flight = new Map();
        this.throttles = new Map();
        this.next_seq = 1;
        this.closed = false;
        fig.ws.addEventListener("close", () => this.clear());
    }

    policy(type) {
        const registered = REQUEST_POLICIES[type] || DEFAULT_POLICY;
        const policy = {...registered};
        if (typeof policy.max_in_flight === "string") {
            policy.max_in_flight = this.config[policy.max_in_flight];
        }
        if (typeof policy.throttle_ms === "string") {
            policy.throttle_ms = this.config[policy.throttle_ms];
            if (policy.throttle_ms === null) {
                policy.retention = "all";
            }
        }
        return policy;
    }

    send(type, properties) {
        if (this.closed) {
            return;
        }
        const policy = this.policy(type);
        const payload = {...properties};
        if (type === "close") {
            this.clear();
            raw_send_message.call(this.fig, type, payload);
            return;
        }
        if (policy.ordering === "bypass") {
            raw_send_message.call(this.fig, type, payload);
            return;
        }
        if (type === "resize" && (payload.width === 0 || payload.height === 0)) {
            return;
        }

        if (policy.retention === "all") {
            for (const entry of this.queue) {
                if (entry.policy.throttle_ms !== null) {
                    entry.force = true;
                }
            }
        }

        if (!this.coalesce(type, payload, policy)) {
            this.queue.push({type, payload, policy, force: false});
        }
        this.drain();
    }

    coalesce(type, payload, policy) {
        if (policy.retention === "all") {
            return false;
        }
        for (let index = this.queue.length - 1; index >= 0; index -= 1) {
            const entry = this.queue[index];
            if (entry.type === type) {
                if (policy.retention === "reduce") {
                    const step = (entry.payload.step || 0) + (payload.step || 0);
                    entry.payload = {...payload, step};
                } else {
                    entry.payload = payload;
                }
                return true;
            }
            if (entry.policy.retention === "all" && entry.policy.ordering === "ordered") {
                break;
            }
        }
        return false;
    }

    drain() {
        while (this.queue.length) {
            const entry = this.queue[0];
            if (!this.can_dispatch(entry)) {
                return;
            }
            this.queue.shift();
            this.dispatch(entry);
        }
    }

    can_dispatch(entry) {
        if (entry.policy.completion !== null) {
            const in_flight = this.in_flight.get(entry.type);
            if (in_flight && in_flight.size >= entry.policy.max_in_flight) {
                return false;
            }
        }
        if (entry.policy.throttle_ms !== null && !entry.force) {
            const throttle = this.throttles.get(entry.type);
            if (throttle && throttle.timer !== null) {
                return false;
            }
        }
        return true;
    }

    dispatch(entry) {
        if (entry.policy.completion !== null) {
            const seq = this.next_seq;
            this.next_seq += 1;
            entry.payload.seq = seq;
            if (!this.in_flight.has(entry.type)) {
                this.in_flight.set(entry.type, new Set());
            }
            this.in_flight.get(entry.type).add(seq);
        }
        if (entry.policy.throttle_ms !== null) {
            this.start_throttle(entry.type, entry.policy.throttle_ms);
        }
        raw_send_message.call(this.fig, entry.type, entry.payload);
    }

    start_throttle(type, throttle_ms) {
        const current = this.throttles.get(type);
        if (current && current.timer !== null) {
            window.clearTimeout(current.timer);
        }
        const state = {timer: null};
        state.timer = window.setTimeout(() => {
            state.timer = null;
            this.drain();
        }, throttle_ms);
        this.throttles.set(type, state);
    }

    complete(type, seq) {
        if (this.closed) {
            return;
        }
        const in_flight = this.in_flight.get(type);
        if (!in_flight || !in_flight.delete(seq)) {
            return;
        }
        this.drain();
    }

    clear() {
        for (const state of this.throttles.values()) {
            if (state.timer !== null) {
                window.clearTimeout(state.timer);
            }
        }
        this.queue = [];
        this.in_flight.clear();
        this.throttles.clear();
        this.closed = true;
    }
}

mpl.figure.prototype.send_message = function(type, properties) {
    if (!this._request_scheduler) {
        this._request_scheduler = new RequestScheduler(this);
    }
    this._request_scheduler.send(type, properties);
};

mpl.figure.prototype.handle_resize_completion = function(fig, msg) {
    if (fig._request_scheduler) {
        fig._request_scheduler.complete("resize", msg.seq);
    }
};

function close_fig(fig) {
    fig.ws.close();
    delete fig;
}

mpl.figure.prototype.handle_newfig = function (fig, msg) {
    const template = document.createElement('template');
    template.innerHTML = msg.payload;
    const children = template.content.childNodes;
    Array.from(children).map(script => {
        if (script.tagName !== "SCRIPT") {
            return script;
        }
        const new_script = document.createElement("script");
        
        for (attr of script.attributes) {
            new_script.setAttribute(attr.name, attr.value) 
        }
        const script_text = document.createTextNode(script.innerHTML);
        new_script.appendChild(script_text);
        
        script.parentNode.replaceChild(new_script, script);
    });
    fig.root.append(...template.content.childNodes);
};

mpl.figure.prototype._root_extra_style = function (_canvas_div) {
    _canvas_div.classList.add("mpl-figure-root");
}

mpl.figure.prototype.handle_closed = function (fig, msg) {
    close_fig(fig);
}

function download_callback(template) {
    return function(fig, fmt) {
        var uri = template.replace("{fmt}", fmt);
        window.open(uri, '_blank');
    };
}

function new_fig(target, fig_id, ws_uri_str, download_fig_uri_str, on_close = "msg_discrete") {
    let websocket = new window._mpl_webagg_websocket_type(ws_uri_str);
    let fig = new mpl.figure(
        // A unique numeric identifier for the figure
        fig_id,
        // A websocket object (or something that behaves like one)
        websocket,
        // A function called when a file type is selected for download
        download_callback(download_fig_uri_str),
        // The HTML element in which to place the figure
        target
    );
    fig.focus_on_mouseover = true;
    let close_cb;
    if (on_close == "msg_discrete") {
        close_cb = function(event) {
            const template = document.createElement('template');
            template.innerHTML = (
                "<div style='color: red; font-size: smaller; cursor: pointer'>" +
                "Connection closed, this figure will no longer update. " +
                "Click to refresh the page." +
                "</div>"
            );
            let disconnected_msg = template.content.firstElementChild;
            disconnected_msg.addEventListener("click", function() {
                location.reload();
            });
            target.getElementsByClassName("mpl-toolbar")[0].prepend(disconnected_msg);
        };
    } else if (on_close == "msg_disable") {
        close_cb = function(event) {
            console.log("websocket close")
            const template = document.createElement('template');
            template.innerHTML = `
                <div style="
                    position: absolute;
                    top: 0;
                    left: 0;
                    height: 100%;
                    width: 100%;
                    text-align: center;
                    background: rgba(255, 255, 255, 0.5);
                    font-size: 24pt;
                    line-height: 2;
                    padding: 1em;
                    padding-top: 20%;
                    cursor: pointer;">
                    Connection closed, this figure will no longer update.<br>
                    Click to refresh the page.
                </div>`
            let disconnected_msg = template.content.firstElementChild;
            console.log("disconnected");
            console.log(disconnected_msg);
            disconnected_msg.addEventListener("click", function() {
                location.reload();
            });
            fig.canvas_div.append(disconnected_msg);
        };
    } else if (on_close == "remove") {
        close_cb = function(event) {
            fig.root.remove();
        };
    } else if (Array.isArray(on_close) && on_close[0] == "remove_parent") {
        let selector = on_close[1];
        close_cb = function(event) {
            fig.root.closest(selector).remove();
        };
    }
    websocket.addEventListener("close", close_cb);
    return fig;
}

function close_after_timeout(weakref, timeout) {
    window.setTimeout(function() {
        let fig = weakref.deref();
        if (!fig) {
            return;
        }
        close_fig(fig);
    }, timeout);
}

function mk_modal(modal, fig) {
    modal.showModal();
    let start = Date.now();
    let prevented = false;
    modal.addEventListener("cancel", (event) => {
        console.log("cancel event", event)
        let delay = Date.now() - start;
        // It's possible to for the mouseup event from the same click that opened the modal to close it without this delay
        // Question: Does this happen on Chrome as well as firefox?
        // Potential solution 1: Deal with different browsers with sniffing
        // Potential solution 2: Manually handle light dismissals
        // Potential solution 3: Track when there is a mouseup targeting the
        // modal matching a mousedown targetting another element, and use a shorter timer
        // to match that to the cancel event.
        if (delay < 1000 && !prevented) {
            prevented = true;
            event.preventDefault();
        }
    });
    modal.addEventListener("close", (e) => {
        if (!fig.ws) {
            return;
        }
        close_after_timeout(new WeakRef(fig), 10000);
        fig.send_message("close", {});
    });
}

window._mpl_webagg_websocket_type = mpl.get_websocket_type();
window._mpl_webaggext = {
    new_fig: new_fig,
    mk_modal: mk_modal
};

})();
