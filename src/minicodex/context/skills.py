"""On-demand SKILL.md loading.

Skills are loaded lazily only when requested. A skill is a directory (or a
single ``.md`` file) whose frontmatter declares ``name`` and ``description``,
followed by the instruction body.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class SkillNotFoundError(FileNotFoundError):
    """Raised when a requested skill file does not exist."""


@dataclass
class Skill:
    name: str
    description: str
    body: str
    path: Path


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split ``text`` into ``(metadata, body)``.

    Recognizes a YAML-style frontmatter block delimited by ``---`` lines at the
    very start of the text. Each ``key: value`` line inside becomes a metadata
    entry. Without a leading delimiter, metadata is empty and the whole text is
    treated as the body.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end: int | None = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break

    if end is None:
        return {}, text

    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" in line:
            key, _, value = line.partition(":")
            metadata[key.strip()] = value.strip()
    body = "\n".join(lines[end + 1 :])
    return metadata, body


def load_skill(path: str | Path) -> Skill:
    """Load a skill from a directory (``SKILL.md``) or a markdown file directly.

    The skill ``name`` comes from frontmatter, falling back to the directory
    name (or file stem). ``description`` defaults to the empty string.
    """
    path = Path(path)
    skill_file = path / "SKILL.md" if path.is_dir() else path
    if not skill_file.exists():
        raise SkillNotFoundError(f"skill file not found: {skill_file}")

    text = skill_file.read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(text)

    if path.is_dir():
        fallback_name = path.name
    else:
        fallback_name = path.stem

    name = metadata.get("name") or fallback_name
    description = metadata.get("description", "")
    return Skill(name=name, description=description, body=body.strip(), path=skill_file)
