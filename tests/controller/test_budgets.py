import pytest

from minicodex.controller.budgets import BudgetTracker


def test_step_limit_exceeded():
    b = BudgetTracker(step_limit=3, token_limit=999, cost_limit=999)
    for _ in range(3):
        b.register_step()
    assert b.exceeded
    assert b.reason == "step_limit"


def test_cost_limit():
    b = BudgetTracker(step_limit=99, token_limit=999, cost_limit=1.0)
    b.add_cost(1.5)
    assert b.exceeded
    assert b.reason == "cost_limit"


def test_token_limit():
    b = BudgetTracker(step_limit=99, token_limit=100, cost_limit=999)
    b.add_tokens(60, 40)
    assert b.exceeded
    assert b.reason == "token_limit"


def test_not_exceeded_when_under_limits():
    b = BudgetTracker(step_limit=5, token_limit=1000, cost_limit=10.0)
    b.register_step()
    b.add_tokens(10, 10)
    b.add_cost(0.5)
    assert not b.exceeded
    assert b.reason == ""


def test_check_raises_limits_exceeded():
    from minicodex.controller.exceptions import LimitsExceeded

    b = BudgetTracker(step_limit=1, token_limit=999, cost_limit=999)
    b.register_step()
    with pytest.raises(LimitsExceeded):
        b.check()
