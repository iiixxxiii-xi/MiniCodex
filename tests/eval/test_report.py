"""Report rendering: markdown + csv comparison tables and result persistence."""

import json

from minicodex.eval.ablation import AblationResult
from minicodex.eval.metrics import BatchMetrics
from minicodex.eval.report import (
    dump_ablation_results,
    load_ablation_results,
    render_csv,
    render_markdown,
    write_report,
)


def _results():
    minimal = BatchMetrics(
        n_tasks=2, success_rate=0.0, avg_tool_calls=1.0, avg_cost_usd=0.0,
        avg_latency_ms=5.0, avg_recovery_rate=1.0, avg_invalid_tool_call_rate=0.5,
    )
    full = BatchMetrics(
        n_tasks=2, success_rate=0.5, avg_tool_calls=3.0, avg_cost_usd=0.01,
        avg_latency_ms=20.0, avg_recovery_rate=0.8, avg_invalid_tool_call_rate=0.1,
    )
    return [
        AblationResult(preset="minimal", metrics=minimal),
        AblationResult(preset="full", metrics=full),
    ]


def test_render_markdown_has_table():
    md = render_markdown(_results(), title="Ablation Report")
    assert "# Ablation Report" in md
    assert "| Preset |" in md
    assert "Success Rate" in md
    assert "Avg Tool Calls" in md
    assert "Recovery Rate" in md
    assert "Invalid Tool Call Rate" in md
    assert "| minimal |" in md
    assert "| full |" in md


def test_render_csv_has_header_and_rows():
    csv = render_csv(_results())
    lines = csv.strip().splitlines()
    assert lines[0].startswith("Preset")
    assert "Success Rate" in lines[0]
    assert any(line.startswith("minimal") for line in lines)
    assert any(line.startswith("full") for line in lines)
    assert len(lines) == 3  # header + 2 rows


def test_write_report_creates_files(tmp_path):
    paths = write_report(_results(), tmp_path, formats=("md", "csv"))
    assert set(p.name for p in paths) == {"report.md", "report.csv"}
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "report.csv").exists()


def test_write_report_md_only(tmp_path):
    paths = write_report(_results(), tmp_path, formats=("md",))
    assert [p.name for p in paths] == ["report.md"]
    assert not (tmp_path / "report.csv").exists()


def test_dump_and_load_ablation_results_roundtrip(tmp_path):
    results = _results()
    dump_ablation_results(results, tmp_path)
    assert (tmp_path / "minimal.json").exists()
    assert (tmp_path / "full.json").exists()

    loaded = load_ablation_results(tmp_path)
    assert {r.preset for r in loaded} == {"minimal", "full"}
    assert loaded[0].metrics.n_tasks == 2


def test_load_ablation_results_skips_malformed(tmp_path):
    (tmp_path / "good.json").write_text(_results()[0].model_dump_json(), encoding="utf-8")
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    loaded = load_ablation_results(tmp_path)
    assert len(loaded) == 1
    assert loaded[0].preset == "minimal"


def test_load_ablation_results_missing_dir(tmp_path):
    assert load_ablation_results(tmp_path / "nope") == []
