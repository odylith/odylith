from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_prompt_visible_assist_has_shared_host_owner() -> None:
    owner_path = ROOT / "src" / "odylith" / "runtime" / "surfaces" / "host_intervention_support.py"
    owner_text = owner_path.read_text(encoding="utf-8")
    assert "def ensure_prompt_visible_assist_bundle(" in owner_text
    assert "def compose_prompt_visible_markdown(" in owner_text
    assert "prompt_signal_runtime.prompt_assist_summary" in owner_text
    assert "visibility feedback noted; this line is deliberately shown in chat" not in owner_text
    assert "surfaced this visibility issue in normal chat where you can inspect it" not in owner_text
    assert "brand promise is something the user can see" not in owner_text

    for path in (
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "host_visible_intervention.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "codex_host_prompt_context.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "claude_host_prompt_context.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "claude_host_prompt_teaser.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert "brand promise is something the user can see" not in text
        assert "ensure_prompt_visible_assist_bundle(" in text


def test_assist_cadence_guidance_reaches_the_shipped_bundle() -> None:
    canonical = ROOT / "odylith" / "agents-guidelines"
    bundled = ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith"

    for path in (
        canonical / "GROUNDING_AND_NARROWING.md",
        canonical / "CODEX_HOST_CONTRACT.md",
        canonical / "VALIDATION_AND_TESTING.md",
        bundled / "AGENTS.md",
        bundled / "agents-guidelines" / "GROUNDING_AND_NARROWING.md",
        bundled / "agents-guidelines" / "CODEX_HOST_CONTRACT.md",
        bundled / "agents-guidelines" / "VALIDATION_AND_TESTING.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "explicit intervention feedback" in text
        assert "normal non-passthrough prompts do not get an Assist line by default" not in text
