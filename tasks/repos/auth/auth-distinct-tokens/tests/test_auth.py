"""Tests for auth (session token bug surfaces via authenticate)."""

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
