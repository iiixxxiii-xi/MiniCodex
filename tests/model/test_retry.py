import pytest

from minicodex.model.retry import is_retryable, with_retry


class _StatusError(Exception):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class _TimeoutError(Exception):
    pass


def test_is_retryable_http_statuses():
    assert is_retryable(_StatusError(429)) is True
    assert is_retryable(_StatusError(500)) is True
    assert is_retryable(_StatusError(400)) is False
    assert is_retryable(_StatusError(404)) is False


def test_is_retryable_timeout_by_name():
    assert is_retryable(_TimeoutError()) is True


def test_with_retry_retries_then_succeeds():
    calls: list[int] = []

    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise _StatusError(500)
        return "ok"

    assert with_retry(fn, max_attempts=5, base_delay=0.0) == "ok"
    assert len(calls) == 3


def test_with_retry_non_retryable_fails_immediately():
    calls: list[int] = []

    def fn():
        calls.append(1)
        raise _StatusError(400)

    with pytest.raises(_StatusError):
        with_retry(fn, max_attempts=5, base_delay=0.0)
    assert len(calls) == 1


def test_with_retry_exhausts_and_reraises():
    calls: list[int] = []

    def fn():
        calls.append(1)
        raise _StatusError(500)

    with pytest.raises(_StatusError):
        with_retry(fn, max_attempts=3, base_delay=0.0)
    assert len(calls) == 3
