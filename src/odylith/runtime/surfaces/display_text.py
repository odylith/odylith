"""Surface compatibility wrapper for shared display-text cleanup."""

from __future__ import annotations

from odylith.runtime.common.display_text import strip_inline_markdown_emphasis
from odylith.runtime.common.display_text import strip_inline_markdown_emphasis_tokens
from odylith.runtime.common.display_text import strip_inline_markdown_emphasis_tree


__all__ = [
    "strip_inline_markdown_emphasis",
    "strip_inline_markdown_emphasis_tokens",
    "strip_inline_markdown_emphasis_tree",
]
