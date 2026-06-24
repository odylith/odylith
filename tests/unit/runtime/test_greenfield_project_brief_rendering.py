from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_project_brief import normalize_project_brief
from odylith.runtime.domain_intelligence.greenfield_project_brief import project_brief_issues
from odylith.runtime.domain_intelligence.greenfield_project_brief import render_project_brief_lines


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"


def _proposal_from_guidance_prompt(prompt: str) -> dict[str, object]:
    intent_text = f"""Product Intent Confirmation needed
No files changed. Source posture: empty_or_no_app_source.

Visible format contract
- Render the visible confirmation as sectioned Markdown.

Original user intent
{prompt}
Next step
- Confirm.
"""
    intent = parse_confirmed_intent_text(intent_text, prompt=prompt)
    return build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=str(intent["title"]),
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )


def test_project_brief_rendering_stays_in_project_brief_owner() -> None:
    proposal_source = (DOMAIN_INTELLIGENCE / "proposal_rendering.py").read_text(encoding="utf-8")
    owner_source = (DOMAIN_INTELLIGENCE / "greenfield_project_brief.py").read_text(encoding="utf-8")

    assert (
        "from odylith.runtime.domain_intelligence.greenfield_project_brief import render_project_brief_lines"
        in proposal_source
    )
    assert "def render_project_brief_lines(" in owner_source
    assert "def _project_brief_lines(" not in proposal_source
    for moved in (
        "def _blueprint_section_lines(",
        "def _project_option_lines(",
        "def _project_checkpoint_lines(",
        "def _project_path_lines(",
    ):
        assert moved not in proposal_source
        assert moved in owner_source
    assert "from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows" in owner_source


def test_project_brief_rendering_uses_shared_row_coercion_and_keeps_plain_lines() -> None:
    brief = {
        "project_outcome": "Residents can submit repair requests and see a reviewable status trail.",
        "operating_principle": "Write only the first path that proves the accepted product promise.",
        "review_posture": "Review the product direction before implementation starts.",
        "blueprint_sections": [
            {
                "section": "First repair path",
                "must_capture": "Resident request, staff triage, status update, and review result.",
                "why_it_matters": "It proves the workflow without wider property-management scope.",
            },
            "not a row",
        ],
        "customization_options": [
            {
                "decision": "Proof depth",
                "recommended": "Require a status timeline before coding.",
                "choices": ["timeline", "notification", ""],
                "impact": "Changes the first release gate.",
            }
        ],
        "customization_prompts": ["Focus the first release on blocked-input recovery."],
        "pre_coding_checkpoints": [
            {
                "checkpoint": "Status evidence",
                "operator_question": "Which status proves the request is reviewable?",
                "done_when": "The first release names that status and its reviewer.",
            }
        ],
        "coding_readiness_gates": ["The first path has a blocked-input and recovery proof."],
        "host_independent_paths": [
            {
                "path": "Confirmed create",
                "command": "odylith greenfield create --confirm",
                "works_in": "Codex and Claude Code",
            }
        ],
    }

    lines = render_project_brief_lines(brief)

    assert "- project design board:" in lines
    assert (
        "  - First repair path: Resident request, staff triage, status update, and review result. "
        "Why: It proves the workflow without wider property-management scope."
    ) in lines
    assert (
        "  - Proof depth: Require a status timeline before coding. Options for Proof depth: timeline, notification. "
        "Impact: Changes the first release gate."
    ) in lines
    assert (
        "  - Status evidence: Which status proves the request is reviewable; "
        "done when The first release names that status and its reviewer."
    ) in lines
    assert "  - Confirmed create: `odylith greenfield create --confirm` (Codex and Claude Code)" in lines
    assert all("not a row" not in line for line in lines)


def test_confirmed_project_brief_does_not_clip_article_modifier_tail_from_broad_prompt() -> None:
    proposal = _proposal_from_guidance_prompt("Draft a greenfield proposal for a training roster readiness hub")
    brief = proposal["project_brief"]
    readiness_copy = json.dumps(brief["coding_readiness_gates"], sort_keys=True)

    assert "a reviewable." not in readiness_copy
    assert "product shows." not in readiness_copy
    assert "the product shows a result" not in readiness_copy
    assert generated_public_copy_issues("training roster project brief", brief) == ()


def test_confirmed_project_brief_skips_short_scope_preface_for_project_outcome() -> None:
    intent = {
        "title": "Project Coordination Workspace",
        "product_story": (
            "This workspace helps operators turn a broad objective into a coordinated project path with "
            "visible state, validation, review, and handoff evidence."
        ),
        "state_object": (
            "A project execution record that tracks the objective, task assignments, validation results, "
            "review decisions, blockers, and final handoff."
        ),
        "first_path": (
            "An operator submits an objective, the workspace creates a bounded plan, assigned roles complete "
            "tasks, validation checks the result, and a reviewer approves the final handoff."
        ),
        "proof_boundary": (
            "The proof should not claim production readiness yet. The first credible proof is one complete "
            "workflow where an operator submits an objective, the system records state, validation catches "
            "or confirms outcomes, and a reviewer can approve the result."
        ),
        "human_actors": [
            "Operator: submits the objective and watches progress",
            "Reviewer: approves or rejects the final handoff",
        ],
        "internal_systems": [
            "Planning Workspace",
            "Task Assignment Register",
            "Validation Evidence Ledger",
        ],
    }

    proposal = build_confirmed_greenfield_proposal(
        prompt="a workspace for coordinated project execution",
        title="Project Coordination Workspace",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    brief = proposal["project_brief"]

    assert "one complete workflow" in brief["project_outcome"]
    assert word_count(brief["project_outcome"]) >= 10
    assert project_brief_issues(brief) == []


def test_project_brief_normalization_repairs_shallow_outcome_from_accepted_intent() -> None:
    normalized = normalize_project_brief(
        {"project_outcome": "The proof should not claim production readiness yet."},
        intent={
            "title": "Project Coordination Workspace",
            "first_path": "An operator submits an objective and reviews a validated handoff.",
            "proof_boundary": (
                "The proof should not claim production readiness yet. The first credible proof is a complete "
                "reviewable path with accepted input, visible state, validation evidence, and an approved result."
            ),
            "state_object": "Project execution record",
        },
        release_selector="0.0.1",
    )

    assert "complete reviewable path" in normalized["project_outcome"]
    assert word_count(normalized["project_outcome"]) >= 10
