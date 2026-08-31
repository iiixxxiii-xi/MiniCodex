from minicodex.model.mock import MockModel


def test_mock_returns_scripted_response():
    m = MockModel(script=[{"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "ls"}}]}])
    r = m.query([], [])
    assert r.tool_calls[0].name == "shell"
    assert r.tool_calls[0].arguments == {"command": "ls"}


def test_mock_increments_usage():
    m = MockModel()
    m.query([], [])
    assert m.total_input_tokens > 0


def test_mock_repeats_last_script_entry_when_exhausted():
    m = MockModel(script=[
        {"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "ls"}}]},
        {"tool_calls": []},
    ])
    assert m.query([], []).tool_calls[0].name == "shell"
    assert m.query([], []).tool_calls == []
    assert m.query([], []).tool_calls == []
