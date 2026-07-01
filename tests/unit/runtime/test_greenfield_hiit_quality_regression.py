from __future__ import annotations

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import ArtifactQualityUnit
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
        "bad_quote": 'The product shows clear "what',
        "bad_punctuation": "A user can collect input,. show a result.",
    }

    issues = generated_public_copy_issues("sample", bad_copy)

    assert any("saved-destination result prose" in issue for issue in issues)
    assert any("possessive result-list prose" in issue for issue in issues)
    assert any("compact path mixed action prose" in issue for issue in issues)
    assert any("scope prefix as a system label" in issue for issue in issues)
    assert any("unbalanced quoted text" in issue for issue in issues)
    assert any("malformed punctuation" in issue for issue in issues)


def test_generated_copy_quality_treats_shell_commands_as_atomic_quote_units() -> None:
    command = (
        "odylith greenfield create --repo-root . --prompt 'Service Goal Planning Workspace: "
        "A user completes onboarding. A user enters baseline capacity through the accepted first path' "
        "--intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1"
    )

    assert generated_public_copy_issues("command", command) == ()
    assert any(
        "unbalanced quoted text" in issue
        for issue in generated_public_copy_issues("bad command", "odylith greenfield create --prompt 'unfinished")
    )


def test_generated_copy_quality_does_not_splice_mermaid_label_headers_into_payload_text() -> None:
    mermaid = """
flowchart LR
  action["First action<br/>Curators: need the product to<br/>coordinate tactile object<br/>labels"] --> owner["Museum Accessibility Exhibit<br/>Planning Workspace Intake<br/>Register Service"]
  proof["Proof result<br/>Audio-description reviews<br/>visitor safety constraints and<br/>installation signoff"]
  outcome["Visible result<br/>Audio-description reviews<br/>visitor safety constraints and<br/>installation signoff"]
"""

    assert generated_public_copy_issues("mermaid", mermaid) == ()


def test_generated_copy_quality_blocks_mixed_action_coordination_in_visible_labels() -> None:
    assert generated_public_copy_issues("good label", 'S1["Upload or select a small dataset"]') == ()
    assert generated_public_copy_issues("action label", 'S1["Check and control for drift"]') == ()
    assert generated_public_copy_issues("ordinary prose", "The researcher uploads or selects a small dataset.") == ()
    assert generated_public_copy_issues("methods label", 'S1["Choose methods and controls for comparison"]') == ()
    assert generated_public_copy_issues("records label", 'S1["Upload controls and records for later review"]') == ()
    assert generated_public_copy_issues("bad control label", 'S1["Checks and control for drift"]') == (
        "bad control label leaked mixed finite/base action in visible label",
    )
    assert generated_public_copy_issues("bad label", 'S1["Uploads or select a small dataset"]') == (
        "bad label leaked mixed finite/base action in visible label",
    )
    assert generated_public_copy_issues("bad action label", 'S1["Upload controls and records results"]') == (
        "bad action label leaked mixed finite/base action in visible label",
    )


def test_generated_copy_quality_allows_structured_memory_context_delimiters() -> None:
    context = (
        "reasoning_mode=odylith_confirmed_governed_proposal; source_posture=confirmed_intent_only; "
        "assumptions=Release 0.0.1 proves one path. | Sensitive context stays auditable.; "
        "open_questions=Which policy applies?"
    )

    assert generated_public_copy_issues("memory context", context) == ()


def test_generated_copy_quality_uses_typed_units_to_skip_metadata_not_free_prose() -> None:
    metadata = ArtifactQualityUnit(
        projection_id="test",
        surface="Project dashboard",
        source_path="project.metadata.status",
        surface_role="status",
        text_kind="metadata",
        text="ready., malformed but not public prose",
    )
    prose = ArtifactQualityUnit(
        projection_id="test",
        surface="Project dashboard",
        source_path="project.summary",
        surface_role="summary",
        text_kind="free_prose",
        text="The accepted path is ready., but punctuation is malformed.",
    )

    assert generated_public_copy_issues("metadata unit", metadata) == ()
    assert generated_public_copy_issues("free prose unit", prose) == (
        "free prose unit leaked malformed punctuation",
    )
