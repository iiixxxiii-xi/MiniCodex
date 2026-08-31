from minicodex.core.events import Event, ActionEvent, ObservationEvent, EventSource


def test_event_base_fields():
    e = Event(source=EventSource.MODEL, kind="action")
    assert e.id
    assert e.timestamp
    assert e.source == EventSource.MODEL


def test_action_observation_link():
    a = ActionEvent(source=EventSource.AGENT, tool_name="shell", tool_call_id="c1", action={"command": "ls"})
    o = ObservationEvent(source=EventSource.RUNTIME, tool_name="shell", tool_call_id="c1",
                         action_id=a.id, observation={"output": "x"})
    assert o.action_id == a.id
    assert o.tool_call_id == "c1"
