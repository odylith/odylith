from pathlib import Path

from odylith.install.agents import (
    SCOPE_END,
    SCOPE_START,
    inject_managed_block,
    managed_block,
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

    assert "Before any substantive repo scan or code change outside trivial fixes, the agent must start from the repo-local Odylith entrypoint" in block
    assert "keep the active workstream, component, or packet in scope" in block
    assert "Direct repo scan before that start step is a policy violation unless the task is trivial or Odylith is unavailable." in block
    assert "Start substantive turns with `./.odylith/bin/odylith start --repo-root .`" in block
    assert "`./.odylith/bin/odylith context --repo-root . <ref>` before raw repo search." in block
    assert "CLI-first is non-negotiable for both Codex and Claude Code." in block
    assert "Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting." in block
    assert "hard policy violation, not a stylistic preference" in block
    assert "odylith/agents-guidelines/CLI_FIRST_POLICY.md" in block
    assert "CB-104" in block
    assert "odylith bug capture" in block
    assert "odylith backlog create" in block
    assert "rerender only the owned surface" in block
    assert "odylith radar refresh" in block
    assert "odylith registry refresh" in block
    assert "odylith casebook refresh" in block
    assert "odylith atlas refresh" in block
    assert "odylith compass refresh" in block
    assert "odylith compass deep-refresh" in block
    assert "missing-shim, or fallback-path details implicit" in block
    assert "Keep the default operating lane shared across Codex and Claude Code" in block
    assert "keep startup, fallback, routing, and packet-selection internals implicit" in block
    assert "the exact file/workstream, the bug under test, or the validation in flight" in block
    assert "If an earlier repo-local start attempt degraded but work can continue safely, do not narrate that history." in block
    assert "Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates" in block
    assert "never prefix commentary with control-plane receipt labels" in block
    assert "Mention Odylith during the work only when the user explicitly asks for the command, a real blocker requires it, or a consumer-versus-maintainer lane distinction matters." in block
    assert "literal commands" not in block
    assert "Keep normal commentary task-first and human." in block
    assert "reserve explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels" in block
    assert "At closeout, you may add at most one short `Odylith Assist:` line" in block
    assert "Prefer `**Odylith Assist:**` when Markdown formatting is available" in block
    assert "Lead with the user win" in block
    assert "link updated governance ids inline when they were actually changed" in block
    assert "frame the edge against `odylith_off` or the broader unguided path" in block
    assert "Keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual." in block
    assert "Ground the line in concrete observed counts, measured deltas, or validation outcomes" in block
    assert "Use only concrete observed counts, measured deltas, or validation outcomes, and ground the line in concrete observed counts, measured deltas, or validation outcomes" not in block
    assert "Silence is better than filler." in block
    assert "At most one supplemental closeout line may appear" in block
    assert "never say `fixed`, `cleared`, or `resolved` without qualification" in block
    assert "same fingerprint as the last falsification or not" in block
    assert "follow this workflow check in order: read the nearest `AGENTS.md`; run the repo-local `odylith start`/`odylith context` step" in block
    assert "grounding Odylith is diagnosis authority, not blanket write authority" in block
    assert "stop at diagnosis and maintainer-ready feedback" in block
    assert "Treat `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh` as writes" in block
    assert "search existing workstream, plan, bug, component, diagram, and recent session/Compass context first" in block
    assert "Queued backlog items, case queues, and shell or Compass queue previews are not implicit implementation instructions." in block
    assert "If the slice expands beyond one truthful record, use child workstreams or execution waves" in block
    assert "`./.odylith/bin/odylith` chooses how Odylith runs; it does not decide which repo files the agent may edit" in block
    assert "run `./.odylith/bin/odylith version --repo-root .` when the launcher exists" in block
    assert "If the launcher is missing, confirm that from the filesystem first" in block
    assert "substantive grounded consumer-lane work" in block
    assert "validated Odylith delegation hosts under the same grounding and validation contract" in block
    assert "keep Odylith grounding mostly in the background. Do not require a fixed visible prefix" not in block
    assert "Odylith grounding:" not in block
    assert "Odylith didn't return immediately" not in block
    assert "In the Odylith product repo, maintainer-only release and benchmark publishing work follows `odylith/maintainer/AGENTS.md`." not in block
    assert "surface the earned Observation/Proposal beat visibly at the hook moment" in block
    assert "Stop is the fallback closeout lane, not the primary intervention moment." in block


def test_managed_block_adds_maintainer_overlay_for_product_repo() -> None:
    block = managed_block(repo_role="product_repo")

    assert "In the Odylith product repo, maintainer-only release and benchmark publishing work follows `odylith/maintainer/AGENTS.md`." in block
    assert "the consumer lane and the Odylith product repo's maintainer mode" in block
    assert "pinned dogfood and detached `source-local` maintainer-dev posture" in block
    assert "pinned dogfood is the default proof posture and detached `source-local` is the explicit dev posture" in block
    assert "Keep the default operating lane shared across Codex and Claude Code" in block
    assert "rerender only the owned surface" in block
    assert "surface the earned Observation/Proposal beat visibly at the hook moment" in block


def test_managed_block_matches_repo_root_product_scope_truth() -> None:
    expected = _extract_scope_block((REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"))

    assert managed_block(repo_role="product_repo") == expected
