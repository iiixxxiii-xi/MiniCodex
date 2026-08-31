from minicodex.core.messages import make_message
from minicodex.core.types import StepOutput
from minicodex.core.config import AgentConfig


def test_make_message_basic():
    m = make_message("user", "hello")
    assert m["role"] == "user"
    assert m["content"] == "hello"


def test_make_message_extra_keys_flattened():
    m = make_message("assistant", "hi", tool_call_id="c1", name="agent")
    assert m["tool_call_id"] == "c1"
    assert m["name"] == "agent"
    assert "extra" not in m


def test_step_output_defaults():
    s = StepOutput()
    assert s.done is False
    assert s.action is None
    assert s.observation is None
    assert s.exit_status == ""
    assert s.submission == ""


def test_agent_config_defaults():
    c = AgentConfig()
    assert c.step_limit == 50
    assert c.token_limit == 200_000
    assert c.cost_limit == 5.0
    assert c.wall_time_limit_seconds == 0
