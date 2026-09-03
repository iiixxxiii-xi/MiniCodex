"""JSON serialization helpers used across the datastore package."""

import json


def dump_json(obj, path: str) -> None:
    """Serialize ``obj`` to ``path`` as indented JSON (UTF-8, non-ASCII kept)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_json(path: str):
    """Deserialize the JSON document stored at ``path``."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
