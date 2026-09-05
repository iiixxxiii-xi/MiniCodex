"""Auth: the login/authenticate API."""

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
