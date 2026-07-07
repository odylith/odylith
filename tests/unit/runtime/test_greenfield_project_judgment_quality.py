from __future__ import annotations

from odylith.runtime.artifact_quality.greenfield_project_judgment import greenfield_project_judgment_issues
from odylith.runtime.domain_intelligence.greenfield_first_path_common import inline_first_path_scope_fragment
from odylith.runtime.domain_intelligence.greenfield_semantic_model import build_greenfield_semantic_model
from odylith.runtime.domain_intelligence.greenfield_semantic_model import semantic_model_mapping
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage


def _proposal(*, state_object: str = "A review record with owner, status, final outcome, and audit history.") -> dict[str, object]:
    return {
        "intent": {
            "title": "ReviewLedger",
            "state_object": state_object,
        },
        "components": [
            {"component_id": "review-record", "label": "Review Record Service"},
            {"component_id": "final-outcome", "label": "Final Outcome Review Service"},
        ],
        "semantic_model": {
            "first_path_contract": {
                "visible_result": "a published final outcome and audit history",
                "events": [
                    {"action": "opens", "text": "A reviewer opens a packet"},
                    {"action": "records", "text": "A reviewer records evidence"},
                    {"action": "approves", "text": "A reviewer approves the final outcome"},
                    {"action": "publishes", "text": "The product publishes a final outcome and audit history"},
                ],
            }
        },
    }


def test_project_judgment_rejects_casing_state_component_and_tail_drift() -> None:
    package = GreenfieldCompletionPackage(
        proposal=_proposal(
            state_object="The product keeps a review record with owner, status, final outcome, and audit history."
        ),
        project_brief_preview={
            "coding_readiness_gates": [
                (
                    "The reviewLedger components come from product systems named in the accepted product "
                    "direction: Review Record Service, Final."
                ),
                "Keep 0.0.1 to the accepted first path and non-goals: Do not expand beyond opening a packet until the first outcome works.",
                "Confirm this as the versioned state object: the product keeps a review record with owner and status.",
            ]
        },
    )

    issues = greenfield_project_judgment_issues(package)

    assert "greenfield artifacts drift mixed-case source token `ReviewLedger` into `reviewLedger`" in issues
    assert (
        "greenfield artifacts should use state-object label `Review Record` instead of the raw tracking predicate"
        in issues
    )
    assert "greenfield project brief clips component label `Final Outcome Review Service` to `Final`" in issues
    assert "greenfield scope boundary truncates the accepted first-path tail" in issues


def test_project_judgment_rejects_managed_state_predicate_leak() -> None:
    package = GreenfieldCompletionPackage(
        proposal=_proposal(
            state_object=(
                "The product manages a cooking run, including selected recipe, staged ingredients, "
                "sensor readings, safety stops, and final serve readiness."
            )
        ),
        project_brief_preview={
            "coding_readiness_gates": [
                (
                    "Confirm this as the versioned state object: The product manages a cooking run, "
                    "including selected recipe, staged ingredients, sensor readings, safety stops, and final serve readiness."
                ),
            ]
        },
    )

    issues = greenfield_project_judgment_issues(package)

    assert "greenfield artifacts leak a product/system predicate instead of a state-object noun phrase" in issues
    assert "greenfield artifacts should use state-object label `Cooking Run` instead of the raw tracking predicate" in issues


def test_project_judgment_accepts_full_case_label_and_tail_coverage() -> None:
    package = GreenfieldCompletionPackage(
        proposal=_proposal(),
        project_brief_preview={
            "coding_readiness_gates": [
                (
                    "The ReviewLedger components come from product systems named in the accepted product "
                    "direction: Review Record Service, Final Outcome Review Service."
                ),
                (
                    "Keep 0.0.1 to the accepted first path and non-goals: Do not expand beyond opening a packet, "
                    "recording evidence, approving the final outcome, and publishing the final outcome and audit history "
                    "until the first outcome works."
                ),
                "Confirm this as the versioned state object: review record with owner and status.",
            ]
        },
    )

    assert greenfield_project_judgment_issues(package) == ()


def test_scope_fragment_preserves_long_confirmed_path_tail() -> None:
    path = (
        "A case board member opens one agenda item, reviews the parcel map and zoning overlays, "
        "reads the staff recommendation and impact summary, groups public comments by concern, "
        "saves questions for staff, compares the recommendation to concerns, records a vote rationale "
        "at the hearing, and sees claim-source traceability for the public record."
    )

    fragment = inline_first_path_scope_fragment(path)

    assert "record a vote rationale" in fragment
    assert "see claim-source traceability" in fragment
    assert "public record" in fragment


def test_semantic_model_preserves_terminal_handoff_visible_result() -> None:
    semantic = semantic_model_mapping(
        build_greenfield_semantic_model(
            title="Field Operations Evidence Console",
            state_object=(
                "An operations evidence record tracks site identity, observation source, captured readings, "
                "supporting files, readiness status, blocker reason, reviewer decision, and handoff evidence."
            ),
            first_path=(
                "An operator opens one site record, adds a source-backed observation, attaches supporting evidence, "
                "marks missing readings as blockers when needed, reviews readiness, and hands the reviewed decision "
                "to the next action queue."
            ),
            proof_boundary=(
                "Release 0.0.1 succeeds when one site record can be opened, linked to source evidence, reviewed "
                "for missing readings, marked ready or blocked with a reason, and handed to the next action queue "
                "with the evidence and reviewer decision still traceable."
            ),
            components=[],
            human_actors=["Field operator", "Operations reviewer"],
        )
    )

    contract = semantic["first_path_contract"]
    events = contract["events"]
    joined_events = " ".join(str(row["text"]) for row in events)

    assert contract["visible_result"] == "the decision to the next action queue"
    assert events[-1]["visible_result"] is True
    assert "accepted result for review" not in joined_events


def test_semantic_model_preserves_reviewed_handoff_object_without_fixed_noun_whitelist() -> None:
    semantic = semantic_model_mapping(
        build_greenfield_semantic_model(
            title="Inspection Scorecard Console",
            state_object="An inspection scorecard tracks site identity, readiness notes, and queue handoff status.",
            first_path=(
                "An operator opens one site record, reviews readiness, and hands the reviewed scorecard "
                "to the next action queue."
            ),
            proof_boundary=(
                "Release succeeds when one site record can be opened, reviewed, and handed to the next action queue."
            ),
            components=[],
            human_actors=["Field operator"],
        )
    )

    contract = semantic["first_path_contract"]

    assert contract["visible_result"] == "the scorecard to the next action queue"
    assert "one site record can be opened" not in contract["visible_result"]


def test_project_judgment_does_not_cross_into_unrelated_scope_prose() -> None:
    package = GreenfieldCompletionPackage(
        proposal=_proposal(),
        project_brief_preview={
            "coding_readiness_gates": [
                (
                    "Keep this slice narrow: Do not expand beyond opening a packet, recording evidence, and "
                    "approving the final outcome; deferred scope: Do not expand into adjacent workflows until "
                    "their own path is accepted."
                )
            ]
        },
    )

    assert "greenfield scope boundary truncates the accepted first-path tail" not in greenfield_project_judgment_issues(package)


def test_project_judgment_accepts_visible_result_inflection_in_scope_tail() -> None:
    package = GreenfieldCompletionPackage(
        proposal={
            **_proposal(),
            "semantic_model": {
                "first_path_contract": {
                    "visible_result": "exported provenance proof",
                    "events": [
                        {"action": "creates", "text": "A museum registrar creates one provenance review case"},
                        {"action": "attaches", "text": "A museum registrar attaches source documents"},
                        {"action": "routes", "text": "A museum registrar routes expert review"},
                        {"action": "marks", "text": "A museum registrar marks accession-ready or blocked"},
                        {"action": "exports", "text": "A museum registrar exports provenance proof"},
                    ],
                }
            },
        },
        project_brief_preview={
            "customization_options": [
                {
                    "recommended": (
                        "Keep 0.0.1 to the accepted first path and non-goals: Do not expand beyond a museum "
                        "registrar creates one provenance review case, attaches source documents, routes expert "
                        "review, marks accession-ready or blocked, and exports provenance proof until the first "
                        "outcome works."
                    )
                }
            ]
        },
    )

    assert greenfield_project_judgment_issues(package) == ()


def test_project_judgment_accepts_past_tense_visible_result_in_scope_tail() -> None:
    package = GreenfieldCompletionPackage(
        proposal={
            **_proposal(),
            "semantic_model": {
                "first_path_contract": {
                    "visible_result": "saved reproducible run record",
                    "events": [
                        {"action": "provides", "text": "A researcher provides source data"},
                        {"action": "defines", "text": "A researcher defines the evaluation context and target"},
                        {"action": "runs", "text": "A researcher runs the model or simulation"},
                        {
                            "action": "reviews",
                            "text": (
                                "A researcher reviews the prediction result with uncertainty and comparison evidence"
                            ),
                        },
                        {"action": "saves", "text": "A researcher saves a reproducible run record"},
                    ],
                }
            },
        },
        project_brief_preview={
            "customization_options": [
                {
                    "recommended": (
                        "Keep 0.0.1 to the accepted first path and non-goals: Do not expand beyond provide "
                        "source data; define the evaluation context and target; run the model or simulation; "
                        "review the prediction result with uncertainty and comparison evidence; save a reproducible "
                        "run record until the first outcome works."
                    )
                }
            ]
        },
    )

    assert greenfield_project_judgment_issues(package) == ()


def test_project_judgment_rejects_component_summary_missing_long_label_tails() -> None:
    long_label = (
        "Annealing Result Review Console for QUBO models, Ising models, "
        "baseline comparisons, and reproducibility evidence"
    )
    package = GreenfieldCompletionPackage(
        proposal={
            **_proposal(),
            "components": [
                {"component_id": "annealing-review", "label": long_label},
                {
                    "component_id": "solver-access",
                    "label": (
                        "Solver Access Control Plane for D-Wave Leap credentials, simulator fallback, "
                        "queue visibility, and run imports"
                    ),
                },
            ],
        },
        project_brief_preview={
            "coding_readiness_gates": [
                (
                    "The ReviewLedger components come from product systems named in the accepted product "
                    "direction: Annealing Result Review Console, Solver Access Control Plane."
                )
            ]
        },
    )

    issues = greenfield_project_judgment_issues(package)

    assert f"greenfield project brief component summary omits `{long_label}`" in issues


def test_project_judgment_treats_repeated_short_actions_as_tail_coverage() -> None:
    proposal = _proposal()
    proposal["semantic_model"] = {
        "first_path_contract": {
            "visible_result": "a simple trend over time",
            "events": [
                {"action": "records", "text": "A user records a first entry"},
                {"action": "logs", "text": "A user logs one action"},
                {"action": "log", "text": "The next day they log again"},
                {"action": "shows", "text": "The product shows a simple trend over time"},
            ],
        }
    }
    package = GreenfieldCompletionPackage(
        proposal=proposal,
        project_brief_preview={
            "coding_readiness_gates": [
                (
                    "The ReviewLedger components come from product systems named in the accepted product "
                    "direction: Review Record Service, Final Outcome Review Service."
                ),
                (
                    "Keep 0.0.1 to the accepted first path and non-goals: Do not expand beyond recording "
                    "a first entry, logging one action, logging again, and reviewing a simple trend over time "
                    "until the first outcome works."
                ),
            ]
        },
    )

    assert greenfield_project_judgment_issues(package) == ()


def test_project_judgment_requires_high_risk_assumptions_in_rendered_artifacts() -> None:
    proposal = _proposal()
    proposal["assumptions"] = [
        {
            "id": "ASM-001",
            "tier": "user_intent",
            "statement": "Reviewers are authorized staff only, not general public users.",
        }
    ]
    package = GreenfieldCompletionPackage(
        proposal=proposal,
        project_brief_preview={
            "coding_readiness_gates": [
                (
                    "The ReviewLedger components come from product systems named in the accepted product "
                    "direction: Review Record Service, Final Outcome Review Service."
                ),
                (
                    "Keep 0.0.1 to the accepted first path and non-goals: Do not expand beyond opening a packet, "
                    "recording evidence, approving the final outcome, and publishing the final outcome and audit history "
                    "until the first outcome works."
                ),
            ]
        },
        backlog_result={"idea_files": {"IDEA.md": "Reviewers can publish a final outcome and audit history."}},
    )

    assert (
        "greenfield domain-expert lens omits accepted assumption `ASM-001` from generated artifacts"
        in greenfield_project_judgment_issues(package)
    )

    covered = GreenfieldCompletionPackage(
        proposal=proposal,
        project_brief_preview=package.project_brief_preview,
        backlog_result={
            "idea_files": {
                "IDEA.md": "Authorized staff reviewers only can publish a final outcome; the general public is not a user."
            }
        },
    )

    assert greenfield_project_judgment_issues(covered) == ()


def test_project_judgment_allows_single_concept_component_label_without_service_suffix() -> None:
    proposal = _proposal()
    proposal["components"] = [
        {"component_id": "observability", "label": "Observability Service"},
        {"component_id": "pipeline", "label": "Pipeline Control Service"},
    ]
    package = GreenfieldCompletionPackage(
        proposal=proposal,
        project_brief_preview={
            "coding_readiness_gates": [
                (
                    "The ReviewLedger components come from product systems named in the accepted product "
                    "direction: Observability, Pipeline Control."
                ),
                (
                    "Keep 0.0.1 to the accepted first path and non-goals: Do not expand beyond opening a packet, "
                    "recording evidence, approving the final outcome, and publishing the final outcome and audit history "
                    "until the first outcome works."
                ),
            ]
        },
    )

    assert greenfield_project_judgment_issues(package) == ()
