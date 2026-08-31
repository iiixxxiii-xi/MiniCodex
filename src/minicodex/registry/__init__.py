"""Tool registry: declarative tools and function-schema generation."""

from minicodex.registry.registry import DuplicateToolError, RegistryError, ToolRegistry
from minicodex.registry.schema import Tool, to_function_schema

__all__ = [
    "Tool",
    "ToolRegistry",
    "RegistryError",
    "DuplicateToolError",
    "to_function_schema",
]
