"""Repo spec: an auth system with a cross-module session-token bug."""

REPO = "auth"

FILES = {
    "auth/__init__.py": "",
    "auth/password.py": '''"""Password: plaintext compare for this toy repo."""


def verify(password: str, stored: str) -> bool:
    return password == stored
''',
    "auth/session.py": '''"""Session: map tokens to usernames."""


class SessionStore:
    def __init__(self):
        self._tokens = {}

    def create(self, username: str) -> str:
        token = self._make_token(username)
        self._tokens[token] = username
        return token

    def _make_token(self, username: str) -> str:
        return "tok_" + username

    def resolve(self, token: str):
        return self._tokens.get(token)
''',
    "auth/auth.py": '''"""Auth: the login/authenticate API."""

from auth.password import verify
from auth.session import SessionStore


class AuthService:
    def __init__(self, users: dict, sessions: SessionStore):
        self.users = users
        self.sessions = sessions

    def login(self, username: str, password: str):
        if username not in self.users:
            return None
        if not verify(password, self.users[username]):
            return None
        return self.sessions.create(username)

    def authenticate(self, token: str):
        return self.sessions.resolve(token)
''',
}

TESTS = {
    "tests/test_auth.py": '''"""Tests for auth (session token bug surfaces via authenticate)."""

from auth.auth import AuthService
from auth.session import SessionStore


def test_login_success():
    svc = AuthService({"alice": "secret"}, SessionStore())
    assert svc.login("alice", "secret") is not None


def test_login_wrong_password():
    svc = AuthService({"alice": "secret"}, SessionStore())
    assert svc.login("alice", "wrong") is None


def test_tokens_are_distinct():
    # Two users must not share the same token (else one overwrites the other).
    store = SessionStore()
    svc = AuthService({"alice": "a", "bob": "b"}, store)
    t1 = svc.login("alice", "a")
    t2 = svc.login("bob", "b")
    assert t1 != t2
    assert store.resolve(t1) == "alice"
    assert store.resolve(t2) == "bob"
''',
}

TASKS = [
    {
        "id": "auth-distinct-tokens",
        "instruction": (
            "Fix the bug where two different users logging in get the same "
            "session token, so one user's session overwrites the other's. The "
            "test 'test_tokens_are_distinct' fails. Find the root cause."
        ),
        "difficulty": "hard",
        "category": "cross-module",
        "lines": 1,
        "bug": [
            ("auth/session.py",
             '        return "tok_" + username\n',
             '        return "same_token"\n'),
        ],
        "fail_to_pass": [
            "tests/test_auth.py::test_tokens_are_distinct",
        ],
        "pass_to_pass": [
            "tests/test_auth.py::test_login_success",
            "tests/test_auth.py::test_login_wrong_password",
        ],
    },
]
