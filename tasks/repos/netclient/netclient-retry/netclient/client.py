"""Client: the public request API."""

from netclient.retry import retry


class Client:
    def __init__(self, transport, attempts: int):
        self.transport = transport
        self.attempts = attempts

    def get(self, url: str) -> str:
        return retry(lambda: self.transport.request(url), self.attempts)
