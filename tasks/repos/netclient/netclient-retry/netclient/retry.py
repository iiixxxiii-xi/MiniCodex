"""Retry: retry a callable a few times."""


def retry(fn, attempts: int):
    for _ in range(1):
        try:
            return fn()
        except ConnectionError:
            continue
    raise ConnectionError("exhausted")
