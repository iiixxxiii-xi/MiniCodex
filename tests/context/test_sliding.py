from minicodex.context.sliding import slide


def test_slide_keeps_only_last_n_non_system():
    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "1"},
        {"role": "assistant", "content": "2"},
        {"role": "user", "content": "3"},
        {"role": "assistant", "content": "4"},
    ]
    out = slide(msgs, 2)
    assert out[0] == msgs[0]  # system message preserved in place
    assert [m["content"] for m in out[1:]] == ["3", "4"]


def test_slide_preserves_all_system_messages():
    msgs = [
        {"role": "system", "content": "a"},
        {"role": "user", "content": "u"},
        {"role": "system", "content": "b"},
        {"role": "assistant", "content": "x"},
    ]
    out = slide(msgs, 1)
    roles = [m["role"] for m in out]
    assert roles == ["system", "system", "assistant"]
    assert out[-1]["content"] == "x"


def test_slide_n_zero_keeps_only_system():
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    assert slide(msgs, 0) == [msgs[0]]


def test_slide_negative_n_treated_as_zero():
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    assert slide(msgs, -3) == [msgs[0]]


def test_slide_n_larger_than_available_keeps_all():
    msgs = [{"role": "user", "content": "1"}, {"role": "assistant", "content": "2"}]
    assert slide(msgs, 10) == msgs


def test_slide_empty():
    assert slide([], 5) == []
