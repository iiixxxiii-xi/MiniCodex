"""Session: map tokens to usernames."""


class SessionStore:
    def __init__(self):
        self._tokens = {}

    def create(self, username: str) -> str:
        token = self._make_token(username)
        self._tokens[token] = username
        return token

    def _make_token(self, username: str) -> str:
        return "same_token"

    def resolve(self, token: str):
        return self._tokens.get(token)
