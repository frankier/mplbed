import os
import signal
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"


@dataclass(frozen=True)
class ExampleSpec:
    id: str
    subdir: str
    file: str
    # "asgi" examples are run under `daphne` against `<module>:app`.
    # "script" examples are run directly with `python <file>` and must honour
    # a `PORT` environment variable.
    kind: str
    routes: tuple = ("/",)
    requires_mne_data: bool = False

    @property
    def path(self):
        return EXAMPLES_DIR / self.subdir / self.file

    @property
    def module_name(self):
        return Path(self.file).stem


EXAMPLES = [
    ExampleSpec(id="starlette-demo_popup", subdir="starlette", file="demo_popup.py", kind="asgi"),
    ExampleSpec(id="starlette-draw_idle", subdir="starlette", file="draw_idle.py", kind="asgi"),
    ExampleSpec(id="starlette-embed2_raw", subdir="starlette", file="embed2_raw.py", kind="asgi"),
    ExampleSpec(id="starlette-mount_app", subdir="starlette", file="mount_app.py", kind="asgi"),
    ExampleSpec(
        id="starlette-integrate_mne",
        subdir="starlette",
        file="integrate_mne.py",
        kind="asgi",
        requires_mne_data=True,
    ),
    ExampleSpec(id="quart-basic", subdir="quart", file="basic.py", kind="script", routes=("/", "/figure")),
]


def mne_sample_data_available():
    try:
        import mne
    except ImportError:
        return False
    try:
        path = mne.datasets.sample.data_path(download=False)
    except Exception:
        return False
    path = Path(path)
    return path.exists() and (path / "MEG" / "sample").exists()


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_port(host, port, timeout=20.0):
    deadline = time.monotonic() + timeout
    last_exc = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError as exc:
            last_exc = exc
            time.sleep(0.2)
    raise TimeoutError(f"Nothing listening on {host}:{port} after {timeout}s") from last_exc


def _terminate(proc, timeout=10.0):
    if proc.poll() is not None:
        return
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=timeout)


@contextmanager
def running_example(spec: ExampleSpec, port: int = None):
    """
    Launch `spec` as a subprocess bound to `port` (a free port is chosen if
    not given), block until it accepts connections, and yield
    `(base_url, proc)`. The process is always terminated on exit.
    """
    if port is None:
        port = free_port()
    cwd = EXAMPLES_DIR / spec.subdir
    env = {**os.environ, "PORT": str(port)}

    if spec.kind == "asgi":
        cmd = [sys.executable, "-m", "daphne", "-p", str(port), f"{spec.module_name}:app"]
    elif spec.kind == "script":
        cmd = [sys.executable, spec.file]
    else:
        raise ValueError(f"Unknown example kind: {spec.kind}")

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        try:
            wait_for_port("127.0.0.1", port)
        except TimeoutError:
            _terminate(proc)
            output = proc.stdout.read() if proc.stdout else ""
            raise AssertionError(
                f"{spec.id} never bound to port {port}.\n--- process output ---\n{output}"
            )
        yield f"http://127.0.0.1:{port}", proc
    finally:
        _terminate(proc)


@pytest.fixture(params=EXAMPLES, ids=lambda spec: spec.id)
def example_spec(request):
    spec = request.param
    if spec.requires_mne_data and not mne_sample_data_available():
        pytest.skip(
            "MNE sample dataset not available locally; set it up with "
            "`python -c \"import mne; mne.datasets.sample.data_path()\"` to include this example"
        )
    return spec
