"""Repo spec: a network client with a cross-module retry bug."""

REPO = "netclient"

FILES = {
    "netclient/__init__.py": "",
    "netclient/transport.py": '''"""Transport: a fake HTTP transport that fails the first N calls."""


class FlakyTransport:
    def __init__(self, fail_times: int = 0):
        self.fail_times = fail_times
        self.calls = 0

    def request(self, url: str) -> str:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise ConnectionError("flaky")
        return "ok"
''',
    "netclient/retry.py": '''"""Retry: retry a callable a few times."""


def retry(fn, attempts: int):
    for _ in range(attempts):
        try:
            return fn()
        except ConnectionError:
            continue
    raise ConnectionError("exhausted")
''',
    "netclient/client.py": '''"""Client: the public request API."""

from netclient.retry import retry


class Client:
    def __init__(self, transport, attempts: int):
        self.transport = transport
        self.attempts = attempts

    def get(self, url: str) -> str:
        return retry(lambda: self.transport.request(url), self.attempts)
''',
}

TESTS = {
    "tests/test_netclient.py": '''"""Tests for netclient (retry bug surfaces via flaky success)."""

from netclient.transport import FlakyTransport
from netclient.client import Client


def test_retries_flaky_transport():
    t = FlakyTransport(fail_times=2)
    c = Client(t, attempts=3)
    assert c.get("http://x") == "ok"


def test_exhausts_retries():
    t = FlakyTransport(fail_times=99)
    c = Client(t, attempts=3)
    try:
        c.get("http://x")
    except ConnectionError:
        return
    raise AssertionError("expected ConnectionError")
''',
}

TASKS = [
    {
        "id": "netclient-retry",
        "instruction": (
            "Fix the bug in the network client where it gives up after one "
            "failure instead of retrying. The test 'test_retries_flaky_transport' "
            "fails. Find the root cause."
        ),
        "difficulty": "hard",
        "category": "cross-module",
        "lines": 1,
        "bug": [
            ("netclient/retry.py",
             "    for _ in range(attempts):\n",
             "    for _ in range(1):\n"),
        ],
        "fail_to_pass": [
            "tests/test_netclient.py::test_retries_flaky_transport",
        ],
        "pass_to_pass": [
            "tests/test_netclient.py::test_exhausts_retries",
        ],
    },
]
