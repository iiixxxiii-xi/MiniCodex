from minicodex.permission.boundary import is_within_workspace


def test_relative_inside_is_allowed(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    assert is_within_workspace("./sub/file", root) is True


def test_parent_traversal_is_rejected(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    assert is_within_workspace("../etc/passwd", root) is False


def test_midpath_traversal_is_rejected(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    assert is_within_workspace("sub/../../etc", root) is False


def test_absolute_inside_is_allowed(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    sub = root / "sub"
    sub.mkdir()
    assert is_within_workspace(sub / "file", root) is True


def test_absolute_outside_is_rejected(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    outside = tmp_path / "other"
    assert is_within_workspace(outside / "file", root) is False


def test_root_itself_is_allowed(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    assert is_within_workspace(".", root) is True
