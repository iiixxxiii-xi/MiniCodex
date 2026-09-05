"""Tests for netclient (retry bug surfaces via flaky success)."""

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
