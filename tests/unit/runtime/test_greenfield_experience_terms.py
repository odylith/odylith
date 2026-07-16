from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_experience import (
    _trim_preview_terminal_fragment,
    _workstream_title_matches_component,
    build_next_steps,
)


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"
EXPERIENCE_PATH = DOMAIN_INTELLIGENCE / "greenfield_experience.py"

HANDOFF_MATCH_STOPWORDS = {
    "adapter",
    "build",
    "component",
    "first",
    "handoffs",
    "implement",
    "path",
    "proof",
    "review",
    "service",
    "state",
    "surface",
    "system",
}


def test_experience_handoff_terms_use_shared_domain_index() -> None:
    source = EXPERIENCE_PATH.read_text(encoding="utf-8")

    assert "greenfield_domain_term_index import ordered_terms" in source
    assert "def _meaningful_terms" not in source
    assert "re.findall" not in source

    assert ordered_terms(
        "Status dashboards, status windows, and review services.",
        minimum=4,
        stopwords=HANDOFF_MATCH_STOPWORDS,
    ) == ["status", "dashboard", "window"]
    assert _workstream_title_matches_component(
        "Build status dashboards proof",
        {"label": "Status Dashboard Surface"},
    )
    assert not _workstream_title_matches_component(
        "Build dashboard targets",
        {"label": "Status Dashboard Surface"},
    )
    assert not _workstream_title_matches_component(
        "Build reviews service handoffs",
        {"label": "Review Service"},
    )


def test_experience_preview_trims_incomplete_subordinate_tail() -> None:
    assert _trim_preview_terminal_fragment(  # noqa: SLF001
        "Give clear correction guidance when required information"
    ) == "Give clear correction guidance"
    assert _trim_preview_terminal_fragment(  # noqa: SLF001
        "Give clear correction guidance when required information is missing"
    ) == "Give clear correction guidance when required information is missing"


def test_implementation_handoff_preserves_explicit_first_release_requirements() -> None:
    next_steps = build_next_steps(
        proposal={
            "intent": {
                "title": "Release Notes Workspace",
                "first_path": "Extension publishers assemble release notes and see a reviewable release brief.",
            },
            "apply_semantic_input": {
                "first_path": "Extension publishers assemble release notes and see a reviewable release brief.",
            },
            "semantic_model": {
                "domain_ontology": {
                    "proof_boundary": (
                        "Release succeeds when the release brief is reviewable. The first release includes one "
                        "workspace per extension, a review queue, and an exportable release brief."
                    )
                }
            },
            "backlog": [
                {"title": "Prove One Complete Release Notes Path"},
                {"title": "Let Extension Publishers Assemble Release Notes", "recommended_first_slice": "Assemble one release brief."},
            ],
            "project_brief": {"coding_readiness_gates": ["The first implementation lane is ready."]},
        },
        backlog_result={
            "created": [
                {"idea_id": "B-001", "title": "Prove One Complete Release Notes Path"},
                {"idea_id": "B-002", "title": "Let Extension Publishers Assemble Release Notes"},
            ]
        },
        first_release_workstreams=["B-001", "B-002"],
        program_result={"umbrella_id": "B-001", "waves": [{"status": "active", "primary_workstreams": ["B-002"]}]},
        release_selector="0.0.1",
    )

    prompt = next_steps["implementation_prompt"].casefold()

    assert "one workspace per extension, a review queue, and an exportable release brief" in prompt
    assert "marketplace publishing" not in prompt
    assert "telemetry" not in prompt
    assert "code scanning" not in prompt
