from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_prompt_visible_assist_has_shared_host_owner() -> None:
    owner_path = ROOT / "src" / "odylith" / "runtime" / "surfaces" / "host_intervention_support.py"
    owner_text = owner_path.read_text(encoding="utf-8")
    assert "def ensure_prompt_visible_assist_bundle(" in owner_text
    assert "def compose_prompt_visible_markdown(" in owner_text
    assert "brand promise is something the user can see" in owner_text

    for path in (
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "host_visible_intervention.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "codex_host_prompt_context.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "claude_host_prompt_context.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "claude_host_prompt_teaser.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert "brand promise is something the user can see" not in text
        assert "ensure_prompt_visible_assist_bundle(" in text
