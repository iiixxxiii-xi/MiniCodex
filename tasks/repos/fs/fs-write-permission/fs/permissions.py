"""Permissions: check whether a user may access a path."""


def can_read(user: str, mode: str) -> bool:
    return mode in ("r", "rw")


def can_write(user: str, mode: str) -> bool:
    return mode in ("r", "rw")
