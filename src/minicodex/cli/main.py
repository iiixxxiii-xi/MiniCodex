"""Typer CLI: ``minicodex run`` / ``eval`` / ``report``.

The default model is ``mock`` so the whole pipeline runs end-to-end without any
API key. Real models are selected with ``--model anthropic/<id>`` or
``--model openai/<id>`` and read their credentials from the environment.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

import typer
from dotenv import load_dotenv

from minicodex.chat.runner import ChatRunner, run_chat_session
from minicodex.eval.ablation import DEFAULT_PRESETS, run_ablation
from minicodex.eval.report import (
    dump_ablation_results,
    load_ablation_results,
    render_markdown,
    write_report,
)
from minicodex.eval.runner import Runner
from minicodex.eval.task import load_task, load_tasks
from minicodex.model.anthropic import AnthropicModel
from minicodex.model.mock import MockModel
from minicodex.model.openai import OpenAIModel
from minicodex.runtime.sandbox.docker import docker_available
from minicodex.toolsource.mcp import mcp_tool_source

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = typer.Typer(help="MiniCodex: a from-scratch coding-agent harness with evaluation.")


def resolve_model(model_id: str, mock: bool):
    """Map a ``--model`` string to a model instance.

    ``mock`` (or the ``--mock`` flag) yields a ``MockModel`` that needs no API
    key. ``anthropic/<id>`` and ``openai/<id>`` select the real SDK adapters.
    """
    if mock or model_id in ("mock", "MockModel"):
        return MockModel()
    if model_id.startswith("anthropic/"):
        return AnthropicModel(model=model_id.split("/", 1)[1])
    if model_id.startswith("openai/"):
        return OpenAIModel(model=model_id.split("/", 1)[1])
    if model_id.startswith("deepseek/"):
        name = model_id.split("/", 1)[1]
        # DeepSeek V4 models are reasoning models: their chain-of-thought shares
        # the output budget with tool calls. Coding tasks need that deep
        # reasoning, so keep the thinking head ENABLED and raise the token budget
        # so the reasoning tokens don't starve the tool calls.
        #
        # Note: unlike CUA (which terminates via a dedicated ``done`` action),
        # this harness's loop finishes when the model returns *no tool calls*, so
        # we deliberately do NOT set ``tool_choice="required"`` here — forcing a
        # tool call would make termination impossible.
        return OpenAIModel(
            model=name,
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            api_key=os.environ.get("DEEPSEEK_API_KEY"),
            max_tokens=8192 if "v4" in name else 4096,
            extra_body={"thinking": {"type": "enabled"}} if "v4" in name else None,
        )
    raise typer.BadParameter(
        f"unrecognized model '{model_id}'; use 'mock', 'anthropic/<id>', 'openai/<id>', or 'deepseek/<id>'"
    )


def _build_tool_sources(mcp: list[str] | None):
    """Turn ``--mcp`` specs into tool sources (None when no servers attached)."""
    if not mcp:
        return None
    return [mcp_tool_source(spec) for spec in mcp]


def _resolve_sandbox(sandbox: str) -> str:
    """Validate ``--sandbox`` and downgrade ``docker`` to ``local`` when the daemon
    is unreachable, printing a clear hint instead of crashing."""
    if sandbox not in ("local", "docker"):
        raise typer.BadParameter(f"unrecognized sandbox '{sandbox}'; use 'local' or 'docker'")
    if sandbox == "docker" and not docker_available():
        typer.echo(
            "warning: Docker daemon is unavailable; falling back to local sandbox "
            "(pass --sandbox local to silence this).",
            err=True,
        )
        return "local"
    return sandbox


@app.command("run")
def run_cmd(
    task: str = typer.Argument(..., help="Path to a task JSON file."),
    model: str = typer.Option("mock", "--model", help="Model: mock, anthropic/<id>, openai/<id>."),
    output_dir: str = typer.Option("results", "--output-dir", help="Where to write trajectory + result."),
    mock: bool = typer.Option(False, "--mock", help="Force MockModel (no API key)."),
    step_limit: int = typer.Option(0, "--step-limit", help="Max steps (0 = unlimited)."),
    max_requeries: int = typer.Option(3, "--max-requeries", help="Retry requeries on errors."),
    sandbox: str = typer.Option("local", "--sandbox", help="Sandbox: 'local' or 'docker'."),
    mcp: list[str] = typer.Option(
        None,
        "--mcp",
        help="Attach an MCP server (repeatable): a URL for HTTP, else a stdio command line.",
    ),
) -> None:
    """Run a single task and print its PASS/FAIL verdict + metrics."""
    try:
        task_obj = load_task(task)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    runner = Runner(
        resolve_model(model, mock),
        output_dir=output_dir,
        step_limit=step_limit,
        max_requeries=max_requeries,
        tool_sources=_build_tool_sources(mcp),
        sandbox=_resolve_sandbox(sandbox),
    )
    result = asyncio.run(runner.run(task_obj))
    verdict = "PASS" if result.passed else "FAIL"
    m = result.metrics
    typer.echo(
        f"{verdict} {result.task_id}  exit={result.exit_status}  "
        f"tool_calls={m.tool_calls}  cost={m.cost_usd:.4f}  latency={m.latency_ms:.1f}ms"
    )
    if result.error:
        typer.echo(f"error: {result.error}", err=True)


@app.command("chat")
def chat_cmd(
    repo: str = typer.Option(".", "--repo", help="Directory the agent reads and writes."),
    model: str = typer.Option("deepseek/v4-pro", "--model", help="Model: deepseek/v4-pro (default), anthropic/<id>, openai/<id>, mock."),
    mock: bool = typer.Option(False, "--mock", help="Force MockModel (no API key)."),
    step_limit: int = typer.Option(0, "--step-limit", help="Max steps per turn (0 = unlimited)."),
    max_requeries: int = typer.Option(3, "--max-requeries", help="Retry requeries on model/format errors."),
    mcp: list[str] = typer.Option(
        None,
        "--mcp",
        help="Attach an MCP server (repeatable): a URL for HTTP, else a stdio command line.",
    ),
) -> None:
    """Interactive chat: type natural-language instructions; the agent edits the repo."""
    model_obj = resolve_model(model, mock)
    try:
        runner = ChatRunner(
            model_obj,
            repo,
            step_limit=step_limit,
            max_requeries=max_requeries,
            tool_sources=_build_tool_sources(mcp),
        )
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    def _readline() -> str:
        sys.stdout.write("> ")
        sys.stdout.flush()
        return input()

    code = asyncio.run(run_chat_session(runner, readline=_readline, write=typer.echo))
    raise typer.Exit(code=code)


@app.command("eval")
def eval_cmd(
    tasks: str = typer.Argument(..., help="Directory of task JSON files, or a .jsonl/.json path."),
    model: str = typer.Option("mock", "--model", help="Model: mock, anthropic/<id>, openai/<id>."),
    policies: str = typer.Option("minimal,full", "--policies", help="Comma-separated ablation presets."),
    output_dir: str = typer.Option("results", "--output-dir", help="Where to write results + report."),
    mock: bool = typer.Option(False, "--mock", help="Force MockModel (no API key)."),
    concurrency: int = typer.Option(4, "--concurrency", help="Max tasks to run concurrently."),
    sandbox: str = typer.Option("local", "--sandbox", help="Sandbox: 'local' or 'docker'."),
) -> None:
    """Run a task set under every policy preset (ablation) and write a report."""
    try:
        task_list = load_tasks(tasks)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if not task_list:
        typer.echo(f"error: no tasks found in {tasks}", err=True)
        raise typer.Exit(code=1)

    preset_names = [name.strip() for name in policies.split(",") if name.strip()]
    unknown = [name for name in preset_names if name not in DEFAULT_PRESETS]
    if unknown:
        typer.echo(f"error: unknown policy preset(s): {', '.join(unknown)}", err=True)
        raise typer.Exit(code=1)
    presets = [DEFAULT_PRESETS[name] for name in preset_names]

    model_obj = resolve_model(model, mock)
    results = asyncio.run(
        run_ablation(
            task_list,
            model_obj,
            presets=presets,
            output_dir=output_dir,
            concurrency=concurrency,
            sandbox=_resolve_sandbox(sandbox),
        )
    )
    dump_ablation_results(results, output_dir)
    write_report(results, output_dir)
    for result in results:
        m = result.metrics
        typer.echo(
            f"{result.preset}: success={m.success_rate:.2f}  "
            f"tool_calls={m.avg_tool_calls:.2f}  cost={m.avg_cost_usd:.4f}  "
            f"latency={m.avg_latency_ms:.1f}ms  recovery={m.avg_recovery_rate:.2f}  "
            f"invalid={m.avg_invalid_tool_call_rate:.2f}"
        )
    typer.echo(f"report written to {Path(output_dir).resolve()}")


@app.command("report")
def report_cmd(
    results: str = typer.Argument("results", help="Directory of AblationResult JSON files."),
    formats: str = typer.Option("md,csv", "--formats", help="Comma-separated: md, csv."),
    output_dir: str = typer.Option("", "--output-dir", help="Where to write report (default: results dir)."),
) -> None:
    """Render the ablation comparison table from persisted results."""
    loaded = load_ablation_results(results)
    if not loaded:
        typer.echo(f"error: no results found in {results}", err=True)
        raise typer.Exit(code=1)
    out = output_dir or results
    fmt = tuple(f.strip() for f in formats.split(",") if f.strip())
    write_report(loaded, out, formats=fmt)
    typer.echo(render_markdown(loaded))


def main() -> None:
    # Bare ``minicodex`` (no subcommand) drops straight into an interactive chat
    # session — the ``claude``-style experience: type instructions, the agent
    # edits the repo. (Equivalent to ``minicodex chat``.)
    if len(sys.argv) <= 1:
        sys.argv.append("chat")
    app()


if __name__ == "__main__":
    main()
