"""Progressive skill loading: bundle tools into named skills and load only the
relevant ones for a task.

Mirrors Claude Code's progressive-disclosure model: instead of injecting every
tool schema into the prompt, the agent starts from a lightweight *skill index*
(name + description + trigger keywords) and expands only the skills a task is
about to touch. This keeps the tool surface small on focused tasks (fewer
schemas, fewer tokens) while still exposing the full set when a task is broad.

A skill whose ``keywords`` is empty is a *core* skill: it is always loaded.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Skill(BaseModel):
    """A named bundle of tools with a human description and trigger keywords.

    ``tools`` holds the tool names this skill exposes. ``keywords`` are
    lowercased substrings that, when present in a task, mark the skill as
    relevant; an empty list means "always relevant".
    """

    name: str
    description: str
    tools: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


def select_skills(task: str, skills: list[Skill]) -> list[Skill]:
    """Return the skills relevant to ``task``.

    A skill is selected when it has no keywords (core) or any keyword is a
    substring of the lowercased task. When nothing matches (e.g. a broad or
    empty task), all skills are returned as a safe fallback.
    """
    lowered = (task or "").lower()
    selected = [
        skill
        for skill in skills
        if not skill.keywords or any(kw.lower() in lowered for kw in skill.keywords)
    ]
    return selected or list(skills)


def tool_names(skills: list[Skill]) -> list[str]:
    """Flatten a list of skills into their (deduplicated, order-preserving)
    tool names."""
    seen: list[str] = []
    for skill in skills:
        for name in skill.tools:
            if name not in seen:
                seen.append(name)
    return seen


def select_tool_schemas(task: str, schemas: list[dict], skills: list[Skill]) -> list[dict]:
    """Return the function-calling schemas for the skills relevant to ``task``.

    ``schemas`` is the full registry output (one OpenAI function schema per
    tool); ``skills`` is the skill decomposition. The result preserves the
    original schema order.
    """
    relevant = {name for name in tool_names(select_skills(task, skills))}
    return [schema for schema in schemas if schema.get("function", {}).get("name") in relevant]


#: The standard skill decomposition of minicodex's builtin tools. ``filesystem``
#: is core (always loaded); the rest load only when the task mentions them.
DEFAULT_SKILLS: list[Skill] = [
    Skill(
        name="filesystem",
        description="Read, write, and edit files in the workspace.",
        tools=["read_file", "write_file", "apply_patch"],
    ),
    Skill(
        name="shell",
        description="Run shell commands (install deps, run scripts, git).",
        tools=["shell", "git"],
        keywords=["shell", "command", "run", "install", "git", "commit", "build"],
    ),
    Skill(
        name="search",
        description="Search the codebase for symbols and patterns.",
        tools=["grep"],
        keywords=["search", "find", "grep", "locate", "where", "symbol"],
    ),
    Skill(
        name="test",
        description="Run the project test suite to verify a fix.",
        tools=["test_runner"],
        keywords=["test", "pytest", "verify", "pass", "fail", "assert"],
    ),
]
