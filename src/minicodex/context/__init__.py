"""Context management strategies: sliding window, truncation, compaction,
file-reference offload, and on-demand skill loading."""

from minicodex.context.compaction import CompactionResult, compact, load_offloaded
from minicodex.context.file_reference import offload, replace_if_large
from minicodex.context.skills import Skill, SkillNotFoundError, load_skill, parse_frontmatter
from minicodex.context.sliding import slide
from minicodex.context.truncation import truncate_observation

__all__ = [
    "slide",
    "truncate_observation",
    "compact",
    "CompactionResult",
    "load_offloaded",
    "offload",
    "replace_if_large",
    "Skill",
    "SkillNotFoundError",
    "load_skill",
    "parse_frontmatter",
]
