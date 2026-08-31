import json

from minicodex.context.compaction import compact, load_offloaded


def _summarizer(messages):
    return f"Summary of {len(messages)} messages"


def test_compact_shortens_messages_but_preserves_raw(tmp_path):
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "q2"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "q3"},
    ]
    result = compact(messages, _summarizer, tmp_path, keep_recent=2)
    assert len(result.messages) < len(messages)
    assert result.messages[0] == messages[0]  # system preserved
    assert result.summary == "Summary of 3 messages"
    assert result.messages[-2:] == [messages[-2], messages[-1]]  # recent kept
    assert result.offload_path is not None
    raw = load_offloaded(result.offload_path)
    assert raw == messages[1:4]  # the compacted raw messages are complete


def test_compact_noop_when_within_keep_recent(tmp_path):
    messages = [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]
    result = compact(messages, _summarizer, tmp_path, keep_recent=10)
    assert result.messages == messages
    assert result.offload_path is None
    assert result.summary == ""


def test_compact_never_compacts_system_messages(tmp_path):
    messages = [
        {"role": "system", "content": "s1"},
        {"role": "system", "content": "s2"},
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "q2"},
    ]
    result = compact(messages, _summarizer, tmp_path, keep_recent=1)
    assert result.messages[:2] == messages[:2]  # both system messages retained
    assert result.messages[-1] == messages[-1]


def test_compact_creates_offload_dir(tmp_path):
    offload = tmp_path / "nested" / "offload"
    messages = [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "q2"},
    ]
    result = compact(messages, _summarizer, offload, keep_recent=1)
    assert result.offload_path.parent == offload
    assert result.offload_path.exists()


def test_load_offloaded_skips_malformed_lines(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text(
        '{"role": "user", "content": "ok"}\nnot-json\n{"role": "assistant", "content": "x"}\n',
        encoding="utf-8",
    )
    msgs = load_offloaded(bad)
    assert len(msgs) == 2


def test_load_offloaded_missing_file_returns_empty(tmp_path):
    assert load_offloaded(tmp_path / "nope.jsonl") == []
