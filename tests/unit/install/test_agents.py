from pathlib import Path

from odylith.install.agents import (
    SCOPE_END,
    SCOPE_START,
    inject_managed_block,
    managed_block,
    managed_claude_bridge_block,
    remove_managed_block,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _extract_scope_block(text: str) -> str:
    start = text.index(SCOPE_START)
    end = text.index(SCOPE_END) + len(SCOPE_END)
    return text[start:end].strip() + "\n"


def test_inject_managed_block_is_idempotent() -> None:
    original = "# Root\n\nBody\n"
    once = inject_managed_block(original)
    twice = inject_managed_block(once)
    assert once == twice
    assert "<!-- odylith-scope:start -->" in once


def test_remove_managed_block_restores_original_body() -> None:
    original = "# Root\n\nBody\n"
    injected = inject_managed_block(original)
    restored = remove_managed_block(injected)
    assert restored == original


def test_remove_managed_block_also_removes_legacy_marker_block() -> None:
    original = "# Root\n\nBody\n"
    legacy = "\n".join(
        [
            "# Root",
            "",
            "<!-- odylith-managed:start -->",
            "## Installed Odylith Guidance",
            "",
            "When `odylith/AGENTS.md` exists, installed Odylith surfaces and installed Odylith paths follow the guidance under `odylith/`.",
            "",
            "- Odylith-related work under `odylith/` should follow `odylith/AGENTS.md` first.",
            "- The repo-root guidance in this file remains authoritative for repo-owned paths outside `odylith/`.",
            "",
            "<!-- odylith-managed:end -->",
            "",
            "Body",
            "",
        ]
    )
    assert remove_managed_block(legacy) == original


def test_managed_block_defaults_consumers_to_odylith_guidance_and_skills() -> None:
    block = managed_block()

    expected = (
        "run `./.odylith/bin/odylith start --repo-root .` first",
        "Do not run `odylith context`, `odylith query`, `git status`, broad repo search",
        "CLI-first is non-negotiable for both Codex and Claude Code",
        "odylith/agents-guidelines/CLI_FIRST_POLICY.md",
        "CB-104",
        "odylith bug capture",
        "odylith backlog create",
        "odylith radar refresh",
        "odylith compass deep-refresh",
        "Keep startup, Context Engine, Execution Engine, memory substrate, Tribunal, Intervention Engine, observers",
        "Optimize by routing, caching, batching, and shortening prompt surface, not by disabling engines.",
        "Treat AI slop as a regression",
        "Generated human-visible content has a non-negotiable clarity floor across all lanes",
        "odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md",
        "odylith/skills/odylith-code-hygiene-guard/SKILL.md",
        "Discipline hot paths must not call host models",
        "project-first Product Intent Confirmation",
        "sectioned Markdown",
        "`## Choose one command`",
        "Start your reply with one clear command: **CONFIRM**, **EDIT**, or **REJECT**",
        "Command: `CONFIRM`",
        "Command: `EDIT`",
        "Command: `REJECT`",
        "same visible Product Intent Confirmation",
        ".odylith/runtime/greenfield/confirmed-intent.json",
        "greenfield compile-transaction",
        "ProductCreateTransaction",
        "--transaction-file",
        "--transaction-hash",
        "writes atomically",
        "Odylith capabilities",
        "host model capability surface",
        "never prefix commentary with control-plane receipt labels",
        "`**Odylith Observation**`",
        "`Odylith Assist:`",
        "Claude direct-edit and Bash PostToolUse hooks stay silent on success",
        "Claude Stop is memory/logging only",
        "`odylith codex intervention-status` or `odylith claude",
        "low-latency delivery record for Teaser, Ambient Highlight, Observation, Proposal, and Assist readiness",
        "`Activation: ready` plus chat visibility",
        "normal non-passthrough prompts do not get an Assist line by default",
        "Do not add Assist just because Odylith ran",
        "concrete observed counts, measured deltas, or validation outcomes",
        "Generic activity receipts are not premium interventions",
        "never say `fixed`, `cleared`, or `resolved` without qualification",
        "same fingerprint as the last falsification or not",
        "grounding Odylith is diagnosis authority, not blanket write authority",
        "Treat `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh` as writes",
        "Queued backlog items, case queues, and shell or Compass queue previews are not implicit implementation instructions.",
        "validated Odylith delegation hosts under the same grounding and validation contract",
    )
    for snippet in expected:
        assert snippet in block

    forbidden = (
        "run the repo-local `odylith start`/`odylith context` step",
        "keep Odylith grounding mostly in the background. Do not require a fixed visible prefix",
        "Odylith grounding:",
        "Odylith didn't return immediately",
        "literal commands",
        "supplies one shared prompt-visible Assist line",
        "Product repo release/benchmark publishing uses `odylith/maintainer/AGENTS.md`.",
    )
    for snippet in forbidden:
        assert snippet not in block

    assert len(block.encode("utf-8")) < 11600


def test_managed_block_adds_maintainer_overlay_for_product_repo() -> None:
    block = managed_block(repo_role="product_repo")

    assert "Product repo release/benchmark publishing uses `odylith/maintainer/AGENTS.md`." in block
    assert "the consumer lane and the Odylith product repo's maintainer mode" in block
    assert "pinned dogfood and detached `source-local` maintainer-dev posture" in block
    assert "pinned dogfood is default proof; detached `source-local` is explicit dev" in block
    assert "Codex and Claude Code are both validated Odylith delegation hosts under the same grounding, routing, and validation contract" in block
    assert "rerender only the owned surface" in block
    assert "Claude direct-edit and Bash PostToolUse hooks stay silent on success" in block
    assert "Claude Stop is memory/logging only" in block
    assert "Do not inspect Odylith source" in block
    assert "hand-author/repair proposal JSON" in block
    assert "parser/schema retries" in block
    assert "Do not ask operator to inspect proposal JSON or add a second confirmation" in block
    assert "Surface only final summary or blockers" in block
    assert "Confirm/Edit/Reject" not in block
    assert "confirm to expand" not in block
    assert len(block.encode("utf-8")) < 11600


def test_managed_block_matches_repo_root_product_scope_truth() -> None:
    expected = _extract_scope_block((REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"))

    assert managed_block(repo_role="product_repo") == expected


def test_managed_claude_bridge_stays_lean_and_imports_agents() -> None:
    original = "# CLAUDE.md\n\n@AGENTS.md\n\nBody\n"
    rendered = inject_managed_block(
        original,
        repo_role="product_repo",
        path=Path("CLAUDE.md"),
    )
    scope_block = _extract_scope_block(rendered)

    assert scope_block == managed_claude_bridge_block(repo_role="product_repo")
    assert "@AGENTS.md" in rendered
    assert "Treat AI slop as a regression." not in scope_block
    assert len(scope_block.encode("utf-8")) < 2200


def test_managed_claude_bridge_consumer_does_not_pin_maintainer_identity() -> None:
    scope_block = managed_claude_bridge_block()

    assert "Use the consumer repo's Git identity and commit policy" in scope_block
    assert "freedom-research" not in scope_block
    assert "sole canonical contributor identity" not in scope_block
    assert "Commit messages must use only" not in scope_block
    assert "coding-assistant trailers" not in scope_block


def test_managed_claude_bridge_matches_repo_root_scope_truth() -> None:
    expected = _extract_scope_block((REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8"))

    assert managed_claude_bridge_block(repo_role="product_repo") == expected
