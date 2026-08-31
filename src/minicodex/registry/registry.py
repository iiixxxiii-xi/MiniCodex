"""``ToolRegistry``: name-keyed store of declarative tools with schema output."""

from __future__ import annotations

from minicodex.registry.schema import Tool, to_function_schema


class RegistryError(Exception):
    """Base error for tool-registry failures."""


class DuplicateToolError(RegistryError):
    """A tool was registered under a name that already exists."""


class ToolRegistry:
    """Ordered, name-keyed registry of ``Tool`` definitions.

    Produces the full list of function-calling schemas to hand to a model, and
    looks up per-tool annotations for the permission/risk layer.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise DuplicateToolError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def resolve(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def schemas(self) -> list[dict]:
        return [to_function_schema(tool) for tool in self._tools.values()]

    def annotations_for(self, name: str) -> dict:
        tool = self._tools.get(name)
        return tool.annotations if tool is not None else {}

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
