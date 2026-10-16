from __future__ import annotations

from pathlib import Path

from odylith.runtime.common.product_assets import resolve_product_path


def test_resolve_product_path_preserves_leading_dot_directories(tmp_path: Path) -> None:
    resolved = resolve_product_path(repo_root=tmp_path, relative_path=".claude/settings.json")

    assert resolved.as_posix().endswith("assets/odylith/.claude/settings.json")
