from __future__ import annotations

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_apply_semantic import ensure_apply_semantic_model

from tests.unit.runtime.greenfield_proposal_fixtures import HIIT_CONFIRMED_INTENT_TEXT


def test_hiit_compact_path_semantics_expand_without_manual_rewrite() -> None:
    intent = complete_confirmed_intent(
        parse_confirmed_intent_text(
            HIIT_CONFIRMED_INTENT_TEXT,
            prompt="Draft a greenfield proposal for a guided HIIT interval training app",
        )
    )
    proposal = ensure_apply_semantic_model(
        build_confirmed_greenfield_proposal(
            prompt="Draft a greenfield proposal for a guided HIIT interval training app",
            title=intent["title"],
            observed_source={},
            release_selector="0.0.1",
            confirmed_intent=intent,
        ),
        refresh=True,
    )

    first_path = proposal["semantic_model"]["first_path_contract"]

    assert intent["external_systems"] == ["device wake-lock so the screen stays on mid-workout"]
    assert first_path["actor"] == "Trainee"
    assert [event["action"] for event in first_path["events"]] == [
        "chooses",
        "starts",
        "drives",
        "keeps",
        "marks",
        "saves",
    ]
    assert first_path["visible_result"] == "Saved session in history with date, workout, and total time"
    assert next(row for row in proposal["components"] if row["label"] == "Workout Builder Service")["release_scope"] == "deferred"
    assert "Trainee Following" not in "\n".join(proposal["intent"]["human_actors"])


def test_generated_copy_quality_blocks_hiit_regression_shapes() -> None:
    bad_copy = {
        "bad_result": "The user sees the session to history with date, workout, and total time.",
        "bad_possessive": "The product shows history with its date, workout, and total time.",
        "bad_actions": "The first path must prove choose a workout, starts it, and saves a result.",
        "bad_label": 'external1["Optional"] --> P',
    }

    issues = generated_public_copy_issues("sample", bad_copy)

    assert any("saved-destination result prose" in issue for issue in issues)
    assert any("possessive result-list prose" in issue for issue in issues)
    assert any("compact path mixed action prose" in issue for issue in issues)
    assert any("scope prefix as a system label" in issue for issue in issues)
