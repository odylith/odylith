from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_apply_prewrite import (
    preview_project_dashboard_payload,
)
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import (
    build_authored_greenfield_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    GreenfieldAuthoredSemanticsError,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_handoff_quality import (
    project_dashboard_preview_issues,
)
from odylith.runtime.project_intelligence.authored_fact_presenter import (
    authored_fact_view,
)
from tests.unit.runtime.test_greenfield_authored_project_dashboard import (
    PRODUCT_STORY,
    PROOF_BOUNDARY,
    PROPOSED_FIRST_RUN,
    _accepted_preview,
    _completion_package,
    _proposal,
    _source_launch_context,
)


PROPOSED_CHECKPOINT = (
    "A reviewer uses visit evidence as the initial release checkpoint."
)
PROPOSED_CHECKPOINT_COPY = f"Assumption — {PROPOSED_CHECKPOINT}"


def _provisional_proof_proposal() -> dict[str, object]:
    source_proposal = _proposal()
    intent = deepcopy(source_proposal["intent"])
    intent["proof_boundary"] = ""
    intent["assumptions"] = [
        {"applies_to": "proof_boundary", "statement": PROPOSED_CHECKPOINT}
    ]
    for relation in intent["authored_semantics"]["first_path_relations"]:
        relation["visible_result_quote"] = ""
    return build_authored_greenfield_proposal(
        observed_source={"source_posture": "operator prompt evidence"},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )


def _dashboard(proposal: dict[str, object], *, root: Path) -> dict[str, object]:
    return preview_project_dashboard_payload(
        root=root,
        proposal=proposal,
        accepted_project_preview=_accepted_preview(proposal=proposal, root=root),
        source_launch_context=_source_launch_context(proposal=proposal, root=root),
    )


def test_provisional_proof_is_visible_without_becoming_an_authored_fact(
    tmp_path: Path,
) -> None:
    proposal = _provisional_proof_proposal()
    payload = _dashboard(proposal, root=tmp_path)

    assert payload["intro"] == f"Source excerpt: “{PRODUCT_STORY}”"
    assert payload["desired"] == PROPOSED_CHECKPOINT_COPY
    assert payload["open_label"] == "Assumptions"
    assert payload["open"] == [PROPOSED_CHECKPOINT]
    assert payload["known"].count(PROPOSED_CHECKPOINT_COPY) == 1
    assert payload["scenario_details"] == [
        ("Proposed first run", PROPOSED_FIRST_RUN),
        ("Proposed proof checkpoint", PROPOSED_CHECKPOINT_COPY),
    ]

    proof_card = next(
        row
        for row in payload["product_story"]["release_contract"]
        if row["semantic_slot"] == "proof"
    )
    assert proof_card == {
        "label": "Proposed proof checkpoint",
        "semantic_slot": "proof",
        "body": PROPOSED_CHECKPOINT_COPY,
    }
    proof_claims = [
        row
        for row in payload["claim_evidence"]
        if row["claim"] == "Proposed proof checkpoint"
    ]
    assert proof_claims == [
        {
            "claim": "Proposed proof checkpoint",
            "value": PROPOSED_CHECKPOINT_COPY,
            "evidence": "explicit typed assumption",
            "freshness": "proposal",
            "owner": "Product decision owner",
            "source": "typed provisional assumption",
        }
    ]

    facts = payload["authored_facts"]
    assert facts["proof_boundary"] == ""
    assert facts["visible_result"] == ""
    assert facts["assumptions"] == [
        {"applies_to": "proof_boundary", "statement": PROPOSED_CHECKPOINT}
    ]
    assert all(
        relation["visible_result_quote"] == ""
        for relation in facts["first_path_relations"]
    )
    assert authored_fact_view(payload) is not None

    for handoff in payload["host_handoff_prompts"]:
        bindings = handoff["contract"]["fact_bindings"]
        assert bindings["proof_boundary"] == PROPOSED_CHECKPOINT_COPY
        assert bindings["visible_result"] == PROPOSED_CHECKPOINT_COPY
        assert handoff["prompt"].count(PROPOSED_CHECKPOINT_COPY) == 1
        assert handoff["prompt"].count("Proposed proof checkpoint:") == 1
        assert "Release proof boundary:" not in handoff["prompt"]
        assert "Release visible result:" not in handoff["prompt"]

    package = _completion_package(
        proposal=proposal,
        dashboard=payload,
        root=tmp_path,
    )
    assert project_dashboard_preview_issues(
        package,
        payload,
        model_authored=True,
    ) == []


def test_source_proof_dashboard_and_handoff_copy_remain_unchanged(
    tmp_path: Path,
) -> None:
    proposal = _proposal()
    payload = _dashboard(proposal, root=tmp_path)

    assert payload["desired"] == "Ω-Receipt"
    assert payload["scenario_details"] == [
        ("Proposed first run", PROPOSED_FIRST_RUN),
        ("Visible result", "Ω-Receipt"),
        ("Proof boundary", PROOF_BOUNDARY),
    ]
    assert payload["authored_facts"]["proof_boundary"] == PROOF_BOUNDARY
    assert payload["authored_facts"]["visible_result"] == "Ω-Receipt"
    assert payload["authored_facts"]["assumptions"] == []
    for handoff in payload["host_handoff_prompts"]:
        bindings = handoff["contract"]["fact_bindings"]
        assert bindings["proof_boundary"] == PROOF_BOUNDARY
        assert bindings["visible_result"] == "Ω-Receipt"
        if handoff["step_id"] == "refresh_governance":
            assert f"Release proof boundary:\n{PROOF_BOUNDARY}" not in handoff["prompt"]
            assert "Release visible result:\nΩ-Receipt" not in handoff["prompt"]
        else:
            assert f"Release proof boundary:\n{PROOF_BOUNDARY}" in handoff["prompt"]
            assert "Release visible result:\nΩ-Receipt" in handoff["prompt"]
    assert project_dashboard_preview_issues(
        _completion_package(proposal=proposal, dashboard=payload, root=tmp_path),
        payload,
        model_authored=True,
    ) == []


def test_absent_proof_fact_projects_as_empty_without_absorbing_assumption_copy(
    tmp_path: Path,
) -> None:
    proposal = _provisional_proof_proposal()
    proposal["intent"].pop("proof_boundary")

    payload = _dashboard(proposal, root=tmp_path)

    assert payload["authored_facts"]["proof_boundary"] == ""
    assert payload["authored_facts"]["visible_result"] == ""
    assert payload["desired"] == PROPOSED_CHECKPOINT_COPY
    assert project_dashboard_preview_issues(
        _completion_package(proposal=proposal, dashboard=payload, root=tmp_path),
        payload,
        model_authored=True,
    ) == []


@pytest.mark.parametrize("mutation", ["missing", "competing", "source_and_assumption"])
def test_invalid_proof_authority_fails_before_dashboard_projection(
    tmp_path: Path,
    mutation: str,
) -> None:
    proposal = _provisional_proof_proposal()
    intent = proposal["intent"]
    if mutation == "missing":
        intent["assumptions"] = []
    elif mutation == "competing":
        intent["assumptions"].append(
            {"applies_to": "proof_boundary", "statement": "A competing checkpoint."}
        )
    else:
        intent["proof_boundary"] = "A source proof must not coexist with an assumption."

    with pytest.raises((GreenfieldAuthoredSemanticsError, ValueError)):
        _dashboard(proposal, root=tmp_path)


def test_tampered_result_relation_and_handoff_binding_fail_closed(
    tmp_path: Path,
) -> None:
    proposal = _provisional_proof_proposal()
    payload = _dashboard(proposal, root=tmp_path)
    package = _completion_package(proposal=proposal, dashboard=payload, root=tmp_path)

    payload["authored_facts"]["first_path_relations"][0][
        "visible_result_quote"
    ] = PROPOSED_CHECKPOINT
    with pytest.raises(GreenfieldAuthoredSemanticsError):
        authored_fact_view(payload)
    issues = project_dashboard_preview_issues(package, payload, model_authored=True)
    assert "model-authored Project dashboard drifted from typed first-path relations" in issues

    payload = _dashboard(proposal, root=tmp_path)
    package = _completion_package(proposal=proposal, dashboard=payload, root=tmp_path)
    payload["host_handoff_prompts"][2]["contract"]["fact_bindings"][
        "proof_boundary"
    ] = PROPOSED_CHECKPOINT
    issues = project_dashboard_preview_issues(package, payload, model_authored=True)
    assert (
        "model-authored Project handoff step 3 drifted from the source-or-assumption proof"
        in issues
    )
