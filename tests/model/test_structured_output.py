"""Structured-output helpers: provider-side strict schemas and client-side
argument validation that reject tool calls whose arguments violate the schema."""

from minicodex.model.base import ModelResponse, ToolCall
from minicodex.model.schema import (
    drop_invalid_tool_calls,
    to_anthropic_tool,
    to_strict_tool_schema,
    validate_arguments,
)


def test_to_strict_tool_schema_forces_all_properties_required():
    tool = {
        "type": "function",
        "function": {
            "name": "shell",
            "description": "run a command",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "number"},
                },
                "required": ["command"],
            },
        },
    }
    out = to_strict_tool_schema(tool)
    fn = out["function"]
    assert fn["name"] == "shell"
    assert fn["strict"] is True
    assert fn["parameters"]["additionalProperties"] is False
    assert fn["parameters"]["required"] == ["command", "timeout"]


def test_to_anthropic_tool_maps_function_to_input_schema():
    tool = {
        "type": "function",
        "function": {
            "name": "shell",
            "description": "run a command",
            "parameters": {"type": "object", "properties": {}},
        },
    }
    out = to_anthropic_tool(tool)
    assert out == {
        "name": "shell",
        "description": "run a command",
        "input_schema": {"type": "object", "properties": {}},
    }


def test_validate_arguments_accepts_valid():
    params = {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }
    assert validate_arguments({"command": "ls"}, params) == []


def test_validate_arguments_rejects_missing_required():
    params = {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }
    assert validate_arguments({}, params) != []


def test_validate_arguments_rejects_wrong_type():
    params = {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }
    assert validate_arguments({"command": 123}, params) != []


def test_drop_invalid_tool_calls_removes_bad_arguments():
    tools = [
        {
            "type": "function",
            "function": {
                "name": "shell",
                "parameters": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
            },
        }
    ]
    response = ModelResponse(
        tool_calls=[
            ToolCall(id="1", name="shell", arguments={"command": "ls"}),
            ToolCall(id="2", name="shell", arguments={}),  # missing required command
        ]
    )
    out = drop_invalid_tool_calls(response, tools)
    assert [tc.id for tc in out.tool_calls] == ["1"]
