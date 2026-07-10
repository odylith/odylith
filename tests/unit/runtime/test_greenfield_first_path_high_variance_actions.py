from __future__ import annotations

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.domain_intelligence import greenfield_confirmed_backlog_actions as backlog_actions
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import metric_capability_summary
from odylith.runtime.domain_intelligence.greenfield_proposals import build_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import readable_action_chain_sentence
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_steps
from odylith.runtime.project_intelligence.intent_confirmation import build_product_intent_confirmation
from odylith.runtime.project_intelligence.intent_confirmation import format_product_intent_confirmation_text
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_mapping_with_authority


_QUANTUM_DOT_DISPLAY_PROMPT = (
    "Create a greenfield proposal for a quantum dot display aging simulation review board that helps a display "
    "reliability engineer submit a scenario, inspect controls and assumptions, execute the simulation, review "
    "confidence and residuals, route exceptions, and publish readiness proof. The first release must preserve "
    "display aging, quantum dot film, luminance decay, thermal soak, color shift, and lifetime model evidence. "
    "Distinctive project vocabulary includes quantum dot display aging color shift evidence and quantum dot display "
    "aging lifetime model review. It must capture scenario version, control variable, error bound, decision ledger, "
    "avoid unsupported operational claims, show uncertainty or confidence limits, and make the saved result "
    "reproducible for product, architecture, engineering, and domain-expert review."
)


def test_first_path_action_chain_keeps_workflow_verbs_from_becoming_actors() -> None:
    first_path = (
        "Restoration hydrologist can open the wetland restoration reach, record stage, vegetation, "
        "and flow evidence, escalate watershed review, resolve exceptions, and publish the restoration "
        "readiness report without automating expert judgment."
    )

    steps = first_path_steps(first_path)

    assert "Restoration hydrologist escalates watershed review" in steps
    assert "Restoration hydrologist resolves exceptions" in steps
    assert all("escalate watershed resolves" not in step.casefold() for step in steps)


def test_metric_capability_summary_does_not_splice_long_paths_through_promised_result() -> None:
    first_path = (
        "Restoration hydrologist can open the wetland restoration reach, record stage, vegetation, "
        "and flow evidence, escalate watershed review, resolve exceptions, and publish the restoration "
        "readiness report without automating expert judgment."
    )

    readable = readable_action_chain_sentence(
        first_path,
        fallback="complete the accepted product path",
        limit=220,
        max_steps=5,
        include_visible_results=True,
    )
    summary = metric_capability_summary(readable)

    assert summary == "the complete first-path run"
    assert "through the promised result" not in summary
    assert generated_public_copy_issues(
        "accepted-project final memory",
        {
            "success_metric": f"Success proof includes the first path actions: {summary}.",
            "operator_metric": f"The first interaction proves this path: {summary}.",
        },
    ) == ()


def test_domain_terms_do_not_make_synthetic_product_role_appear_in_first_path() -> None:
    first_path = (
        "Display reliability engineer can submit a scenario, inspect controls and assumptions, execute the simulation, "
        "review confidence and residuals, route exceptions, and publish readiness proof."
    )

    assert backlog_actions.actor_appears_in_path(first_path, "Display Reliability Engineer")
    assert not backlog_actions.actor_appears_in_path(first_path, "Quantum Dot Display Aging operator")


def test_final_memory_pressure_does_not_use_title_homonym_as_reviewer(tmp_path) -> None:
    confirmation = build_product_intent_confirmation(
        prompt=_QUANTUM_DOT_DISPLAY_PROMPT,
        title="quantum dot display aging simulation review board",
        repo_name=tmp_path.name,
        observed_source={},
    )
    intent = parse_confirmed_intent_text(format_product_intent_confirmation_text(confirmation), prompt=_QUANTUM_DOT_DISPLAY_PROMPT)
    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=_QUANTUM_DOT_DISPLAY_PROMPT,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
        require_completion_ready=False,
    )
    rendered = str(proposal)

    assert "letting the quantum dot display review" not in rendered.casefold()
    assert "let the quantum dot display review" not in rendered.casefold()
    assert generated_public_copy_issues("accepted-project final memory", proposal) == ()
