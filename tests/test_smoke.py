"""
Smoke tests: launch each example, make sure it binds to its port and serves
its routes without error, then kill it.
"""
import urllib.request
import urllib.error

from conftest import running_example


def _get(url, timeout=10.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def test_example_binds_and_serves(example_spec):
    with running_example(example_spec) as (base_url, proc):
        for route in example_spec.routes:
            status, body = _get(base_url + route)
            assert status == 200, (
                f"{example_spec.id} route {route!r} returned status {status}:\n"
                f"{body[:2000]!r}"
            )
        assert proc.poll() is None, f"{example_spec.id} exited early"
