"""Report rendering: markdown + csv comparison tables, plus result persistence.

``write_report`` renders an ablation comparison from in-memory results;
``dump_ablation_results`` / ``load_ablation_results`` persist and restore the
results for the CLI's separate ``eval`` and ``report`` commands.
"""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path

from pydantic import ValidationError

from minicodex.eval.ablation import AblationResult

logger = logging.getLogger(__name__)

_COLUMNS = [
    ("Preset", "preset"),
    ("Success Rate", "success_rate"),
    ("Avg Tool Calls", "avg_tool_calls"),
    ("Avg Cost USD", "avg_cost_usd"),
    ("Avg Latency ms", "avg_latency_ms"),
    ("Recovery Rate", "avg_recovery_rate"),
    ("Invalid Tool Call Rate", "avg_invalid_tool_call_rate"),
    ("Tasks", "n_tasks"),
]

_HEADER = [label for label, _ in _COLUMNS]


def _fmt(value, digits: int = 4) -> str:
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _rows(results: list[AblationResult]) -> list[list[str]]:
    return [
        [_fmt(getattr(r.metrics, attr)) for _, attr in _COLUMNS[1:]]
        for r in results
    ]


def render_markdown(results: list[AblationResult], *, title: str = "Ablation Report") -> str:
    """Render a markdown comparison table for the ablation results."""
    lines = [f"# {title}", ""]
    lines.append("| " + " | ".join(_HEADER) + " |")
    lines.append("|" + "|".join([" --- "] * len(_HEADER)) + "|")
    for result in results:
        values = [result.preset] + [
            _fmt(getattr(result.metrics, attr)) for _, attr in _COLUMNS[1:]
        ]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def render_csv(results: list[AblationResult]) -> str:
    """Render a CSV comparison table for the ablation results."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_HEADER)
    for result in results:
        writer.writerow([result.preset] + _rows([result])[0])
    return buffer.getvalue()


def write_report(
    results: list[AblationResult],
    output_dir: str | Path,
    *,
    formats: tuple[str, ...] = ("md", "csv"),
) -> list[Path]:
    """Write the comparison report to ``output_dir`` and return the written paths."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    if "md" in formats:
        path = output_dir / "report.md"
        path.write_text(render_markdown(results), encoding="utf-8")
        written.append(path)
    if "csv" in formats:
        path = output_dir / "report.csv"
        path.write_text(render_csv(results), encoding="utf-8")
        written.append(path)
    return written


def dump_ablation_results(results: list[AblationResult], output_dir: str | Path) -> list[Path]:
    """Persist each :class:`AblationResult` as ``<preset>.json`` under ``output_dir``."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for result in results:
        path = output_dir / f"{result.preset}.json"
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        written.append(path)
    return written


def load_ablation_results(results_dir: str | Path) -> list[AblationResult]:
    """Load :class:`AblationResult` files (``*.json``) from ``results_dir``.

    Malformed files are skipped with a warning; a missing directory yields an
    empty list (so ``report`` never crashes on an absent results dir).
    """
    results_dir = Path(results_dir)
    if not results_dir.exists():
        return []
    loaded: list[AblationResult] = []
    for path in sorted(results_dir.glob("*.json")):
        try:
            loaded.append(AblationResult.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValidationError, ValueError) as exc:
            logger.warning("skipping malformed result file %s: %s", path, exc)
    return loaded
