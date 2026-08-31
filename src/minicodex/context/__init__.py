"""Context management strategies: sliding window, truncation, compaction,
file-reference offload, and on-demand skill loading."""

from minicodex.context.sliding import slide

__all__ = ["slide"]
