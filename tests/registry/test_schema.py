from minicodex.registry.schema import Tool, to_function_schema


def test_tool_to_openai_schema():
    t = Tool(
        name="read_file",
        description="Read a file",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        annotations={"read_only": True},
    )
    s = to_function_schema(t)
    assert s["type"] == "function"
    assert s["function"]["name"] == "read_file"
    assert s["function"]["description"] == "Read a file"
    assert s["function"]["parameters"]["required"] == ["path"]


def test_tool_annotations_default_empty():
    t = Tool(name="shell", description="Run a command", parameters={"type": "object", "properties": {}})
    assert t.annotations == {}
