from minicodex.permission.masking import mask


def test_mask_replaces_secret_values():
    assert mask("api key: sk-abc123", ["sk-abc123"]) == "api key: ***"


def test_mask_replaces_multiple_secrets():
    text = "user=admin password=hunter2 token=sk-abc123"
    assert mask(text, ["hunter2", "sk-abc123"]) == "user=admin password=*** token=***"


def test_mask_longest_first_to_avoid_partial_matches():
    assert mask("sk-abc123", ["sk-abc", "sk-abc123"]) == "***"


def test_mask_ignores_empty_secrets():
    assert mask("hello", ["", "h"]) == "***ello"


def test_mask_no_secrets_returns_unchanged():
    assert mask("no secrets here", ["xyz"]) == "no secrets here"
