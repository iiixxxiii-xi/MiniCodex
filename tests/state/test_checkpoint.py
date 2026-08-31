from minicodex.state.checkpoint import CheckpointData, CheckpointManager


def _state(step, n_msgs=2):
    return CheckpointData(
        step=step,
        messages=[{"role": "user", "content": f"m{i}"} for i in range(n_msgs)],
        counters={"steps": step, "input_tokens": 100 * step, "cost_usd": 0.5 * step},
        executed_actions=[{"name": "shell", "arguments": {"command": "ls"}}] * step,
    )


def test_save_then_load_roundtrip(tmp_path):
    mgr = CheckpointManager(tmp_path)
    state = _state(3)
    path = mgr.save(state)
    assert path.exists()
    loaded = mgr.load()
    assert loaded is not None
    assert loaded.step == 3
    assert loaded.messages == state.messages
    assert loaded.counters == state.counters
    assert loaded.executed_actions == state.executed_actions


def test_load_empty_dir_returns_none(tmp_path):
    mgr = CheckpointManager(tmp_path)
    assert mgr.load() is None


def test_load_recovers_latest_step(tmp_path):
    mgr = CheckpointManager(tmp_path)
    for step in (1, 2, 3):
        mgr.save(_state(step))
    loaded = mgr.load()
    assert loaded is not None
    assert loaded.step == 3


def test_load_skips_corrupt_latest_and_falls_back(tmp_path):
    mgr = CheckpointManager(tmp_path)
    mgr.save(_state(1))
    mgr.save(_state(2))
    mgr.save(_state(3))
    # Corrupt the latest checkpoint to simulate a torn write.
    (tmp_path / "checkpoint-000003.json").write_text("{not valid json", encoding="utf-8")
    loaded = mgr.load()
    assert loaded is not None
    assert loaded.step == 2


def test_load_all_corrupt_returns_none(tmp_path):
    mgr = CheckpointManager(tmp_path)
    (tmp_path / "checkpoint-000001.json").write_text("garbage", encoding="utf-8")
    (tmp_path / "checkpoint-000002.json").write_text("{also garbage", encoding="utf-8")
    assert mgr.load() is None


def test_crash_recovery_with_fresh_manager(tmp_path):
    mgr1 = CheckpointManager(tmp_path)
    mgr1.save(_state(1))
    mgr1.save(_state(2))
    # Simulate a crash: a brand-new manager must recover the latest state.
    mgr2 = CheckpointManager(tmp_path)
    recovered = mgr2.load()
    assert recovered is not None
    assert recovered.step == 2
    assert recovered.messages == _state(2).messages
