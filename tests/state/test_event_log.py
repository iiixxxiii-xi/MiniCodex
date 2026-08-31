import json

from minicodex.core.events import ActionEvent, Event, EventSource, ObservationEvent
from minicodex.state.event_log import EventLog, deserialize_event


def test_append_and_replay_roundtrip(tmp_path):
    log = EventLog(tmp_path / "traj.jsonl")
    a = ActionEvent(source=EventSource.AGENT, tool_name="shell", tool_call_id="c1", action={"command": "ls"})
    o = ObservationEvent(
        source=EventSource.RUNTIME,
        tool_name="shell",
        tool_call_id="c1",
        action_id=a.id,
        observation={"output": "x"},
    )
    log.append(a)
    log.append(o)
    log.close()

    events = log.replay()
    assert len(events) == 2
    assert isinstance(events[0], ActionEvent)
    assert isinstance(events[1], ObservationEvent)
    assert events[0].tool_call_id == "c1"
    assert events[1].action_id == a.id
    assert events[1].observation == {"output": "x"}


def test_replay_preserves_order(tmp_path):
    log = EventLog(tmp_path / "t.jsonl")
    for i in range(5):
        log.append(Event(source=EventSource.CONTROLLER, kind=f"step-{i}"))
    log.close()
    events = log.replay()
    assert [e.kind for e in events] == [f"step-{i}" for i in range(5)]


def test_replay_missing_file_returns_empty(tmp_path):
    log = EventLog(tmp_path / "nope.jsonl")
    assert log.replay() == []


def test_replay_skips_malformed_lines(tmp_path):
    path = tmp_path / "t.jsonl"
    good = Event(source=EventSource.CONTROLLER, kind="ok")
    path.write_text("not json\n" + json.dumps(good.model_dump(mode="json")) + "\n", encoding="utf-8")
    events = EventLog(path).replay()
    assert len(events) == 1
    assert events[0].kind == "ok"


def test_append_creates_parent_dirs(tmp_path):
    path = tmp_path / "a" / "b" / "t.jsonl"
    log = EventLog(path)
    log.append(Event(source=EventSource.CONTROLLER, kind="x"))
    log.close()
    assert path.exists()


def test_context_manager_flushes_on_exit(tmp_path):
    path = tmp_path / "t.jsonl"
    with EventLog(path) as log:
        log.append(Event(source=EventSource.CONTROLLER, kind="x"))
    events = EventLog(path).replay()
    assert len(events) == 1
    assert events[0].kind == "x"


def test_deserialize_event_dispatches_by_kind():
    action_data = {
        "id": "1",
        "timestamp": 0.0,
        "source": "agent",
        "kind": "action",
        "tool_name": "shell",
        "tool_call_id": "c",
        "action": {},
    }
    assert isinstance(deserialize_event(action_data), ActionEvent)

    obs_data = {
        "id": "2",
        "timestamp": 0.0,
        "source": "runtime",
        "kind": "observation",
        "tool_name": "shell",
        "tool_call_id": "c",
        "action_id": "1",
        "observation": {},
    }
    assert isinstance(deserialize_event(obs_data), ObservationEvent)

    base_data = {"id": "3", "timestamp": 0.0, "source": "user", "kind": "custom"}
    ev = deserialize_event(base_data)
    assert isinstance(ev, Event)
    assert not isinstance(ev, ActionEvent)
