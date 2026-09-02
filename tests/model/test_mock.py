from minicodex.model.mock import MockModel


async def test_mock_returns_scripted_response():
    m = MockModel(script=[{"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "ls"}}]}])
    r = await m.query([], [])
    assert r.tool_calls[0].name == "shell"
    assert r.tool_calls[0].arguments == {"command": "ls"}


async def test_mock_increments_usage():
    m = MockModel()
    await m.query([], [])
    assert m.total_input_tokens > 0


async def test_mock_repeats_last_script_entry_when_exhausted():
    m = MockModel(script=[
        {"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "ls"}}]},
        {"tool_calls": []},
    ])
    assert (await m.query([], [])).tool_calls[0].name == "shell"
    assert (await m.query([], [])).tool_calls == []
    assert (await m.query([], [])).tool_calls == []
