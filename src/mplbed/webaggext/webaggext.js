(function() {

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

const navigation_keys = new Set([
    "ArrowUp",
    "ArrowDown",
    "ArrowLeft",
    "ArrowRight",
    "PageUp",
    "PageDown",
    "Home",
    "End",
    " ",
]);

function prevent_default_navigation(fig) {
    fig.canvas_div.addEventListener("wheel", function(event) {
        event.preventDefault();
    }, {passive: false});
    fig.canvas_div.addEventListener("keydown", function(event) {
        if (navigation_keys.has(event.key)) {
            event.preventDefault();
        }
    });
}

function new_fig(
    target,
    fig_id,
    ws_uri_str,
    download_fig_uri_str,
    on_close = "msg_discrete",
    should_prevent_default_navigation = false,
) {
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
    if (should_prevent_default_navigation) {
        prevent_default_navigation(fig);
    }
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
