"""Structured-output helpers for tool arguments.

Two layers work together to keep tool arguments valid:

* **Provider-side** — :func:`to_strict_tool_schema` rewrites OpenAI function
  tools into ``strict: true`` schemas (all properties required,
  ``additionalProperties: false``) so the API refuses non-conforming arguments;
  :func:`to_anthropic_tool` maps the OpenAI ``{"function": {...}}`` shape into
  Anthropic's ``{"name", "description", "input_schema"}`` shape.
* **Client-side** — :func:`validate_arguments` checks parsed arguments against
  the declared JSON Schema, and :func:`drop_invalid_tool_calls` rejects tool
  calls whose arguments violate it, so garbage never reaches the runtime.
"""

from __future__ import annotations

import logging

import jsonschema

from minicodex.model.base import ModelResponse, ToolCall

logger = logging.getLogger(__name__)


def _make_strict(schema):
    """Recursively make an object schema OpenAI-``strict``-compatible.

    Every object level (a subschema carrying ``properties``) gets
    ``additionalProperties: false`` and a ``required`` list naming all of its
    properties. Leaf schemas (``{"type": "string"}``) are left untouched.
    """
    if not isinstance(schema, dict):
        return schema
    out = dict(schema)
    properties = out.get("properties")
    if isinstance(properties, dict):
        out["properties"] = {key: _make_strict(value) for key, value in properties.items()}
        out["type"] = "object"
        out["additionalProperties"] = False
        out["required"] = sorted(properties.keys())
    return out


def to_strict_tool_schema(tool: dict) -> dict:
    """Convert an OpenAI function tool into a ``strict: true`` schema the API
    can enforce, so returned arguments always conform to the declared shape."""
    function = dict(tool.get("function") or {})
    return {
        "type": "function",
        "function": {
            "name": function.get("name", ""),
            "description": function.get("description", ""),
            "parameters": _make_strict(function.get("parameters") or {}),
            "strict": True,
        },
    }


def to_anthropic_tool(tool: dict) -> dict:
    """Map an OpenAI ``{"type": "function", "function": {...}}`` tool into the
    Anthropic ``{"name", "description", "input_schema"}`` shape."""
    function = dict(tool.get("function") or {})
    return {
        "name": function.get("name", ""),
        "description": function.get("description", ""),
        "input_schema": function.get("parameters") or {},
    }


def validate_arguments(arguments: dict, parameters: dict) -> list[str]:
    """Validate ``arguments`` against a JSON Schema, returning error strings.

    Returns an empty list when valid. A malformed or empty schema never raises:
    it degrades to "no validation" so a bad schema cannot reject every call.
    """
    if not isinstance(parameters, dict) or not parameters:
        return []
    try:
        cls = jsonschema.validators.validator_for(parameters)
        errors = list(cls(parameters).iter_errors(arguments))
    except (jsonschema.SchemaError, Exception):  # noqa: BLE001 - never reject on schema problems
        return []
    return [
        f"{'.'.join(str(p) for p in err.path) or '<root>'}: {err.message}"
        for err in sorted(errors, key=lambda e: list(e.path))
    ]


def _tool_schema(tool: dict) -> tuple[str, dict | None]:
    """Extract ``(name, parameters)`` from a tool dict in either provider shape."""
    if not isinstance(tool, dict):
        return "", None
    function = tool.get("function")
    if isinstance(function, dict):
        return function.get("name", ""), function.get("parameters")
    return tool.get("name", ""), tool.get("input_schema")


def parameters_for(tools: list[dict], name: str) -> dict | None:
    """Return the JSON Schema ``parameters`` for the tool named ``name``."""
    for tool in tools or []:
        tool_name, parameters = _tool_schema(tool)
        if tool_name == name and isinstance(parameters, dict) and parameters:
            return parameters
    return None


def drop_invalid_tool_calls(response: ModelResponse, tools: list[dict]) -> ModelResponse:
    """Return ``response`` with tool calls whose arguments violate their schema
    removed (degraded), logging each rejection.

    This is the client-side half of structured output: provider-side constraints
    reduce invalid arguments, and this guard catches whatever slips through.
    """
    if not response.tool_calls:
        return response
    kept: list[ToolCall] = []
    for tool_call in response.tool_calls:
        parameters = parameters_for(tools, tool_call.name)
        errors = validate_arguments(tool_call.arguments, parameters) if parameters else []
        if errors:
            logger.warning(
                "rejecting tool call '%s' (%s) with invalid arguments: %s",
                tool_call.name,
                tool_call.id,
                "; ".join(errors),
            )
            continue
        kept.append(tool_call)
    if len(kept) == len(response.tool_calls):
        return response
    return response.model_copy(update={"tool_calls": kept})
