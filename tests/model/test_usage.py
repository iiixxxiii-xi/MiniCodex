import pytest

from minicodex.model.usage import compute_cost


def test_compute_cost_known_model():
    assert compute_cost("gpt-4o-mini", 1_000_000, 1_000_000) == pytest.approx(0.75)


def test_compute_cost_unknown_model_uses_default():
    assert compute_cost("mystery-model", 1_000_000, 0) == pytest.approx(3.0)


def test_compute_cost_zero_tokens_is_zero():
    assert compute_cost("gpt-4o", 0, 0) == 0.0


def test_compute_cost_deepseek_v4_flash():
    assert compute_cost("deepseek-v4-flash", 1_000_000, 0) == pytest.approx(0.28)
    assert compute_cost("deepseek-v4-flash", 0, 1_000_000) == pytest.approx(0.42)


def test_compute_cost_deepseek_chat():
    assert compute_cost("deepseek-chat", 1_000_000, 0) == pytest.approx(0.28)
    assert compute_cost("deepseek-chat", 0, 1_000_000) == pytest.approx(0.42)


def test_compute_cost_deepseek_v4_pro():
    assert compute_cost("deepseek-v4-pro", 1_000_000, 0) == pytest.approx(1.10)
    assert compute_cost("deepseek-v4-pro", 0, 1_000_000) == pytest.approx(1.68)
