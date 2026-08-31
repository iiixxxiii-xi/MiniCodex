import pytest

from minicodex.context.truncation import truncate_observation


def test_short_text_unchanged():
    text = "hello"
    assert truncate_observation(text, max_len=100) == text


def test_exact_boundary_unchanged():
    text = "abcdef"
    assert truncate_observation(text, max_len=6) == text


def test_over_limit_truncates_and_appends_notice():
    text = "x" * 100
    out = truncate_observation(text, max_len=10)
    assert out.startswith("x" * 10)
    assert "truncated" in out
    assert "90" in out  # omitted character count


def test_notice_reports_omitted_count():
    text = "abcdefghij"
    out = truncate_observation(text, max_len=4)
    assert "6" in out


def test_negative_max_len_raises():
    with pytest.raises(ValueError):
        truncate_observation("abc", max_len=-1)


def test_zero_max_len_still_appends_notice():
    text = "abc"
    out = truncate_observation(text, max_len=0)
    assert "truncated" in out
    assert "3" in out
