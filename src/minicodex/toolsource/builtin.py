"""``BuiltinToolSource``: the in-process tool set, exposed as a ``ToolSource``.

Wraps the existing :class:`~minicodex.registry.registry.ToolRegistry` (for
schemas) and a runtime (for execution) so the built-in tools participate in the
same pluggable tool-source list as external sources. Behaviour is identical to
the pre-abstraction loop: schemas are handed to the model verbatim and
``call`` forwards to ``runtime.execute``.
"""

from __future__ import annotations

from minicodex.registry.registry import ToolRegistry


class BuiltinToolSource:
    """Expose a runtime (+ registry / explicit schemas) as a :class:`ToolSource`.

    Schema resolution order:

    1. explicit ``schemas`` (the loop passes the possibly policy-filtered list),
    2. ``registry.schemas()`` when a registry is supplied,
    3. ``runtime.schemas()`` when the runtime exposes one.

    ``call`` always delegates to ``runtime.execute`` with the canonical
    ``{"name": ..., "arguments": ...}`` action shape.
    """

    def __init__(self, runtime, *, registry: ToolRegistry | None = None, schemas: list[dict] | None = None):
        self.runtime = runtime
        self.registry = registry
        self._schemas = list(schemas) if schemas is not None else None

    def schemas(self) -> list[dict]:
        if self._schemas is not None:
            return list(self._schemas)
        if self.registry is not None:
            return self.registry.schemas()
        schemas_fn = getattr(self.runtime, "schemas", None)
        if callable(schemas_fn):
            return schemas_fn()
        return []

    async def call(self, name: str, arguments: dict) -> dict:
        return await self.runtime.execute({"name": name, "arguments": arguments})
