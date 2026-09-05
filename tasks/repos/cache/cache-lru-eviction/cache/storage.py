"""Storage: an in-memory key-value store."""


class Storage:
    def __init__(self):
        self._data = {}

    def get(self, key):
        return self._data.get(key)

    def put(self, key, value):
        self._data[key] = value

    def remove(self, key):
        self._data.pop(key, None)

    def __len__(self):
        return len(self._data)
