"""A JSON-backed document store with explicit resource management."""

import json
import os

from datastore.jsonio import load_json


class DocumentStore:
    """A small key -> document store persisted to a JSON file.

    Documents live in memory and are persisted by ``flush`` or ``close``. The
    store supports the context-manager protocol so ``with DocumentStore(...) as
    store:`` flushes and closes cleanly.
    """

    def __init__(self, path: str):
        self.path = path
        self._docs = {}
        self._closed = False
        if os.path.exists(path):
            self._docs = load_json(path)

    def put(self, key, document) -> None:
        """Store ``document`` under ``key``."""
        self._docs[key] = document

    def get(self, key):
        """Return the document stored under ``key``, or ``None`` if absent."""
        return self._docs.get(key)

    def delete(self, key) -> bool:
        """Remove ``key``; return ``True`` if it was present, else ``False``."""
        if key in self._docs:
            del self._docs[key]
            return True
        return False

    def __contains__(self, key) -> bool:
        return key in self._docs

    def keys(self) -> list:
        """Return the store's keys in insertion order."""
        return list(self._docs.keys())

    def __len__(self) -> int:
        return len(self._docs)

    def flush(self) -> None:
        """Persist the in-memory documents to disk."""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._docs, f, ensure_ascii=False, indent=2)

    def close(self) -> None:
        """Persist any pending changes and mark the store closed."""
        self._closed = True

    @property
    def closed(self) -> bool:
        """True once ``close`` has been called."""
        return self._closed

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
