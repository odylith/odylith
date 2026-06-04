from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_project_brief import render_project_brief_lines


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"


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
