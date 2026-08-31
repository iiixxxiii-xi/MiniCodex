"""Declarative tool schema: a ``Tool`` and its function-calling schema form."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Tool(BaseModel):
    """A declarative tool: name, human description, JSON-Schema parameters, and
    optional annotations (e.g. ``read_only``) consumed by the permission layer.
    """

    name: str
    description: str
    parameters: dict
    annotations: dict = Field(default_factory=dict)


def to_function_schema(tool: Tool) -> dict:
    """Convert a ``Tool`` into an OpenAI-style function-calling schema dict.

    The ``parameters`` field is a JSON Schema object describing the arguments
    the tool accepts; it is passed through unchanged to the model.
    """
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }
