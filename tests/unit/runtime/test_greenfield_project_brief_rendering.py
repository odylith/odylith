from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
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
        "  - Proof depth: Require a status timeline before coding. Choices: timeline, notification. "
        "Impact: Changes the first release gate."
    ) in lines
    assert (
        "  - Status evidence: Which status proves the request is reviewable? "
        "Done when: The first release names that status and its reviewer."
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
