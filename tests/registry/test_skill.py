"""Progressive skill loading: skill selection + schema filtering."""

from minicodex.registry.skill import (
    DEFAULT_SKILLS,
    Skill,
    select_skills,
    select_tool_schemas,
    tool_names,
)


def _schema(name: str) -> dict:
    return {"type": "function", "function": {"name": name}}


def test_core_skills_are_always_loaded():
    # filesystem has no keywords -> core, always selected.
    selected = select_skills("any task whatsoever", DEFAULT_SKILLS)
    names = {s.name for s in selected}
    assert "filesystem" in names


def test_keyword_match_loads_skill():
    selected = select_skills("run the test suite and verify", DEFAULT_SKILLS)
    names = {s.name for s in selected}
    assert "test" in names
    assert "shell" in names  # "run" matches the shell keyword


def test_irrelevant_skill_not_loaded():
    # A pure search task should not pull in the shell or test skills.
    selected = select_skills("search for the symbol foo", DEFAULT_SKILLS)
    names = {s.name for s in selected}
    assert "search" in names
    assert "shell" not in names
    assert "test" not in names


def test_empty_task_loads_only_core_skills():
    # Progressive disclosure: an empty/broad task starts minimal (core only).
    selected = select_skills("", DEFAULT_SKILLS)
    names = {s.name for s in selected}
    assert names == {"filesystem"}


def test_falls_back_to_all_when_no_core_and_no_match():
    # No core skill + no keyword hit -> safe fallback to the whole set.
    skills = [Skill(name="shell", description="", tools=["shell"], keywords=["run"])]
    assert len(select_skills("a totally unrelated task", skills)) == len(skills)


def test_select_tool_schemas_filters():
    schemas = [_schema(n) for n in ["read_file", "shell", "grep", "test_runner", "git"]]
    out = select_tool_schemas("run the tests", schemas, DEFAULT_SKILLS)
    names = {s["function"]["name"] for s in out}
    # core filesystem + test (keyword "test") + shell ("run") are loaded; grep is not.
    assert "read_file" in names
    assert "test_runner" in names
    assert "shell" in names
    assert "grep" not in names


def test_tool_names_dedupes():
    skills = [
        Skill(name="a", description="", tools=["x", "y"]),
        Skill(name="b", description="", tools=["y", "z"]),
    ]
    assert tool_names(skills) == ["x", "y", "z"]
