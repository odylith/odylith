from __future__ import annotations

from odylith.runtime.common import display_text


def test_strip_inline_markdown_emphasis_tree_cleans_nested_display_strings_without_rekeying() -> None:
    payload = {
        "version_state_global_name": "__ODYLITH_VERSION_STATE__",
        "title": "**Account owner**",
        "nested": [{"description": "The **actor** reviews evidence."}],
    }

    cleaned = display_text.strip_inline_markdown_emphasis_tree(payload)

    assert cleaned["version_state_global_name"] == "ODYLITH_VERSION_STATE"
    assert cleaned["title"] == "Account owner"
    assert cleaned["nested"][0]["description"] == "The actor reviews evidence."
