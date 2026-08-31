import pytest

from minicodex.model.usage import compute_cost


def test_compute_cost_known_model():
    assert compute_cost("gpt-4o-mini", 1_000_000, 1_000_000) == pytest.approx(0.75)


def test_compute_cost_unknown_model_uses_default():
    assert compute_cost("mystery-model", 1_000_000, 0) == pytest.approx(3.0)


def test_compute_cost_zero_tokens_is_zero():
    assert compute_cost("gpt-4o", 0, 0) == 0.0
