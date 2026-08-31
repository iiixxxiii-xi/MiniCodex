import pytest

from minicodex.context.skills import SkillNotFoundError, load_skill, parse_frontmatter


def _write_skill(dirpath, content, name="SKILL.md"):
    skill_file = dirpath / name
    skill_file.write_text(content, encoding="utf-8")
    return skill_file


def test_parse_frontmatter_extracts_metadata_and_body():
    text = "---\nname: my-skill\ndescription: does things\n---\nBody here\nmore body\n"
    metadata, body = parse_frontmatter(text)
    assert metadata == {"name": "my-skill", "description": "does things"}
    assert body == "Body here\nmore body"


def test_parse_frontmatter_without_frontmatter_returns_empty_metadata():
    text = "just a body\nline two\n"
    metadata, body = parse_frontmatter(text)
    assert metadata == {}
    assert body == text


def test_load_skill_from_directory(tmp_path):
    _write_skill(tmp_path, "---\nname: greet\ndescription: says hi\n---\nHello body\n")
    skill = load_skill(tmp_path)
    assert skill.name == "greet"
    assert skill.description == "says hi"
    assert skill.body == "Hello body"


def test_load_skill_from_file_directly(tmp_path):
    file = _write_skill(tmp_path, "---\nname: direct\n---\ncontent\n", name="custom.md")
    skill = load_skill(file)
    assert skill.name == "direct"
    assert skill.body == "content"


def test_load_skill_missing_name_falls_back_to_dirname(tmp_path):
    _write_skill(tmp_path, "---\ndescription: unnamed\n---\nbody\n")
    skill = load_skill(tmp_path)
    assert skill.name == tmp_path.name


def test_load_skill_missing_file_raises(tmp_path):
    with pytest.raises(SkillNotFoundError):
        load_skill(tmp_path / "does-not-exist")
