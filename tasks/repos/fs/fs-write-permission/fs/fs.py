"""FS: the public read/write API."""

from fs.permissions import can_read, can_write


class FileSystem:
    def __init__(self):
        self._files = {}

    def read(self, user: str, path: str, mode: str):
        if not can_read(user, mode):
            return None
        return self._files.get(path)

    def write(self, user: str, path: str, content: str, mode: str):
        if not can_write(user, mode):
            return False
        self._files[path] = content
        return True
