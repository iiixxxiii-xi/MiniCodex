"""ContextPolicy turns a named policy into real message/observation transforms."""

import pytest

from minicodex.controller.policies.context import ContextPolicy


def test_none_policy_is_identity():
    policy = ContextPolicy(name="none")
    messages = [{"role": "user", "content": "hi"}]
    assert policy.process_messages(messages) is messages
    assert policy.process_observation("hello world") == "hello world"


def test_sliding_keeps_last_n_non_system():
    policy = ContextPolicy(name="sliding", window=2)
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
    ]
    out = policy.process_messages(messages)
    assert [m["content"] for m in out] == ["sys", "a1", "u2"]


def test_truncation_cuts_and_annotates():
    policy = ContextPolicy(name="truncation", max_len=10)
    out = policy.process_observation("x" * 100)
    assert out.startswith("x" * 10)
    assert "omitted" in out
    assert "90" in out


def test_truncation_leaves_short_text_untouched():
    policy = ContextPolicy(name="truncation", max_len=100)
    assert policy.process_observation("short") == "short"


def test_compaction_summarizes_old_messages(tmp_path):
    policy = ContextPolicy(name="compaction", keep_recent=2, offload_dir=str(tmp_path))
    messages = [
        {"role": "user", "content": "m1"},
        {"role": "assistant", "content": "m2"},
        {"role": "user", "content": "m3"},
        {"role": "assistant", "content": "m4"},
        {"role": "user", "content": "m5"},
    ]
    out = policy.process_messages(messages)
    assert len(out) < len(messages)
    assert any("summary" in m.get("content", "") for m in out)
    assert out[-1]["content"] == "m5"
    assert out[-2]["content"] == "m4"
    # raw compacted messages are offloaded to disk for replay
    assert list(tmp_path.glob("compaction-*.jsonl"))


def test_unknown_policy_name_raises():
    with pytest.raises(ValueError):
        ContextPolicy(name="bogus")
