"""Transport: a fake HTTP transport that fails the first N calls."""


class FlakyTransport:
    def __init__(self, fail_times: int = 0):
        self.fail_times = fail_times
        self.calls = 0

    def request(self, url: str) -> str:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise ConnectionError("flaky")
        return "ok"
