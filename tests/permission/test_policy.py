from minicodex.permission.policy import Decision, PermissionPolicy
from minicodex.registry.schema import Tool


def _tool(name, annotations=None):
    return Tool(name=name, description="", parameters={}, annotations=annotations or {})


def test_read_only_tool_is_allowed():
    policy = PermissionPolicy()
    tool = _tool("read_file", {"read_only": True})
    assert policy.decide(tool, {"name": "read_file", "arguments": {}}) is Decision.ALLOW


def test_destructive_tool_is_denied():
    policy = PermissionPolicy()
    tool = _tool("apply_patch", {"destructive": True})
    assert policy.decide(tool, {"name": "apply_patch", "arguments": {}}) is Decision.DENY


def test_destructive_annotation_wins_over_read_only():
    policy = PermissionPolicy()
    tool = _tool("weird", {"read_only": True, "destructive": True})
    assert policy.decide(tool, {}) is Decision.DENY


def test_shell_rm_rf_is_denied():
    policy = PermissionPolicy()
    tool = _tool("shell")
    action = {"name": "shell", "arguments": {"command": "rm -rf /tmp/x"}}
    assert policy.decide(tool, action) is Decision.DENY


def test_shell_read_only_command_is_allowed():
    policy = PermissionPolicy()
    tool = _tool("shell")
    action = {"name": "shell", "arguments": {"command": "ls -la"}}
    assert policy.decide(tool, action) is Decision.ALLOW


def test_shell_unknown_command_asks():
    policy = PermissionPolicy()
    tool = _tool("shell")
    action = {"name": "shell", "arguments": {"command": "python train.py"}}
    assert policy.decide(tool, action) is Decision.ASK


def test_non_command_tool_without_annotation_asks():
    policy = PermissionPolicy()
    tool = _tool("mystery_tool")
    assert policy.decide(tool, {"name": "mystery_tool", "arguments": {}}) is Decision.ASK
