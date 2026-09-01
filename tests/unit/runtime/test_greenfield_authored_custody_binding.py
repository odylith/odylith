from __future__ import annotations

import copy
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
    AUTHORED_SEMANTICS_KEY,
    GreenfieldAuthoredSemanticsError,
    authored_component_relation_facts,
    authored_relation_set_sha256,
    authored_source_custody,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    materialize_model_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    RESCUE_PROFILE_ID,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from odylith.runtime.governance import artifact_tribunal
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
)


def _materialized_authored_intent(tmp_path: Path) -> dict[str, Any]:
    intent: dict[str, Any] = {
        "title": "Harbor Desk",
        "product_story": "Dock attendants need clear berth placement",
        "state_object": "berth occupancy",
        "first_path": (
            "Dock attendant Ivo enters a vessel tag, the berth recorder records berth occupancy, "
            "and the berth map shows the placement"
        ),
        "proof_boundary": "Verify the placement and retention receipt",
        "problem": "Berth placement is hard to track",
        "customer": "Dock attendants",
        "opportunity": "One reviewable berth workflow",
        "product_view": "Harbor Desk gives dock attendants a berth workflow",
        "success_metrics": ["The berth map shows the placement"],
        "evidence_requirements": ["Source evidence preserves berth history"],
        "operational_constraints": ["Retain source notes for seven years"],
        "component_responsibilities": ["Record berth occupancy", "Show berth placement"],
        "human_actors": ["Dock attendant Ivo"],
        "external_systems": ["Harbor Ledger"],
        "internal_systems": ["Berth recorder", "Berth map"],
        "assumptions": [],
        "ambiguities": [],
        "non_goals": ["Do not manage vessel scheduling"],
    }
    relations = [
        {
            "actor_kind": "human",
            "actor_quote": "Dock attendant Ivo",
            "event_quote": "Dock attendant Ivo enters a vessel tag",
            "action_verb_quote": "enters",
            "target_quote": "a vessel tag",
            "visible_result_quote": "",
            "recovery_path": False,
        },
        {
            "actor_kind": "product",
            "actor_quote": "the berth recorder",
            "owner_system_quote": "Berth recorder",
            "event_quote": "the berth recorder records berth occupancy",
            "action_verb_quote": "records",
            "target_quote": "berth occupancy",
            "visible_result_quote": "",
            "recovery_path": False,
        },
        {
            "actor_kind": "product",
            "actor_quote": "the berth map",
            "owner_system_quote": "Berth map",
            "event_quote": "the berth map shows the placement",
            "action_verb_quote": "shows",
            "target_quote": "the placement",
            "visible_result_quote": "the berth map shows the placement",
            "recovery_path": False,
        },
    ]
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    ) + "."
    return materialize_model_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        authoring_provider=StructuredAuthoringProvider(
            authored_response(
                intent,
                evidence_text=source,
                first_path_relations=relations,
                component_responsibility_owners=["Berth recorder", "Berth map"],
            )
        ),
        authoring_timeout_seconds=84,
        authoring_profile_id=RESCUE_PROFILE_ID,
    )


def _mutated_relations(candidate: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    mutated = copy.deepcopy(dict(candidate))
    semantics = mutated["authored_semantics"]
    relations = semantics["first_path_relations"]
    return mutated, relations


def _relation_free_intent(tmp_path: Path) -> dict[str, Any]:
    intent = copy.deepcopy(_materialized_authored_intent(tmp_path))
    intent.pop(AUTHORED_SEMANTICS_KEY)
    return intent


def test_product_intent_authority_binds_complete_ordered_authored_relation_set(tmp_path: Path) -> None:
    candidate = _materialized_authored_intent(tmp_path)
    authority = candidate[PRODUCT_INTENT_AUTHORITY_KEY]
    relations = candidate["authored_semantics"]["first_path_relations"]
    component_relations = candidate["authored_semantics"][
        "component_responsibility_relations"
    ]
    context_relations = candidate["authored_semantics"][
        "first_path_context_relations"
    ]

    assert authority["authored_relation_set_sha256"] == authored_relation_set_sha256(
        relations,
        component_relations,
        first_path_context_relations=context_relations,
    )


def test_confirmed_proposal_dispatch_rejects_relation_free_authority(tmp_path: Path) -> None:
    intent = _relation_free_intent(tmp_path)

    with pytest.raises(
        ValueError,
        match="authoredness does not match sealed Product Intent relation authority",
    ):
        greenfield_proposals.build_confirmed_greenfield_proposal(
            prompt="Build Harbor Desk",
            title="Harbor Desk",
            observed_source={"source_posture": "confirmed_intent_only"},
            confirmed_intent=intent,
        )


def test_proposal_construction_rejects_relation_free_authority(tmp_path: Path) -> None:
    intent = _relation_free_intent(tmp_path)

    with pytest.raises(
        ValueError,
        match="authoredness does not match sealed Product Intent relation authority",
    ):
        greenfield_proposals.build_greenfield_proposal(
            repo_root=tmp_path,
            prompt="Build Harbor Desk",
            confirmed_intent=intent,
            require_completion_ready=False,
        )


def test_transaction_compilation_rejects_relation_free_authority(tmp_path: Path) -> None:
    intent = _relation_free_intent(tmp_path)
    authority = intent.pop(PRODUCT_INTENT_AUTHORITY_KEY)

    with pytest.raises(
        ValueError,
        match="authoredness does not match sealed Product Intent relation authority",
    ):
        greenfield_proposals.compile_greenfield_create_transaction(
            repo_root=tmp_path,
            proposal={
                "intent": intent,
                PRODUCT_INTENT_AUTHORITY_KEY: authority,
            },
            release_selector="0.0.1",
        )


def test_proposal_construction_rejects_mutated_product_event_owner(tmp_path: Path) -> None:
    candidate = _materialized_authored_intent(tmp_path)
    mutated, relations = _mutated_relations(candidate)
    relations[1]["owner_system_quote"] = "Berth map"

    with pytest.raises(GreenfieldAuthoredSemanticsError, match="product event owner"):
        greenfield_proposals.build_greenfield_proposal(
            repo_root=tmp_path,
            prompt="Build Harbor Desk",
            confirmed_intent=mutated,
            require_completion_ready=False,
        )


def test_proposal_construction_rejects_rebound_component_responsibility_owner(
    tmp_path: Path,
) -> None:
    candidate = _materialized_authored_intent(tmp_path)
    mutated = copy.deepcopy(candidate)
    relation = mutated[AUTHORED_SEMANTICS_KEY]["component_responsibility_relations"][0]
    relation["owner_system_path"] = "/internal_systems/1"
    relation["owner_system_quote"] = "Berth map"

    with pytest.raises(
        GreenfieldAuthoredSemanticsError,
        match="do not match sealed Product Intent authority",
    ):
        greenfield_proposals.build_greenfield_proposal(
            repo_root=tmp_path,
            prompt="Build Harbor Desk",
            confirmed_intent=mutated,
            require_completion_ready=False,
        )


def test_proposal_construction_rejects_a_noncanonical_component_owner_path(
    tmp_path: Path,
) -> None:
    candidate = _materialized_authored_intent(tmp_path)
    mutated = copy.deepcopy(candidate)
    relation = mutated[AUTHORED_SEMANTICS_KEY]["component_responsibility_relations"][0]
    relation["owner_system_path"] = "/internal_systems/01"
    relation["owner_system_quote"] = "Berth map"

    with pytest.raises(GreenfieldAuthoredSemanticsError, match="invalid system owner"):
        greenfield_proposals.build_greenfield_proposal(
            repo_root=tmp_path,
            prompt="Build Harbor Desk",
            confirmed_intent=mutated,
            require_completion_ready=False,
        )


def test_transaction_compilation_rejects_missing_component_responsibility_binding(
    tmp_path: Path,
) -> None:
    candidate = _materialized_authored_intent(tmp_path)
    mutated = copy.deepcopy(candidate)
    del mutated[AUTHORED_SEMANTICS_KEY]["component_responsibility_relations"][0]
    proposal = {
        "projection_origin": AUTHORED_PROJECTION_ORIGIN,
        "intent": mutated,
        PRODUCT_INTENT_AUTHORITY_KEY: candidate[PRODUCT_INTENT_AUTHORITY_KEY],
    }

    with pytest.raises(GreenfieldAuthoredSemanticsError, match="without typed owners"):
        greenfield_proposals.compile_greenfield_create_transaction(
            repo_root=tmp_path,
            proposal=proposal,
            release_selector="0.0.1",
        )


def test_proposal_construction_rejects_authored_relation_downgrade(tmp_path: Path) -> None:
    candidate = _materialized_authored_intent(tmp_path)
    candidate.pop(AUTHORED_SEMANTICS_KEY)

    with pytest.raises(GreenfieldAuthoredSemanticsError, match="authoredness does not match"):
        greenfield_proposals.build_greenfield_proposal(
            repo_root=tmp_path,
            prompt="Build Harbor Desk",
            confirmed_intent=candidate,
            require_completion_ready=False,
        )


def test_proposal_construction_rejects_older_authored_semantics_without_inference(
    tmp_path: Path,
) -> None:
    candidate = _materialized_authored_intent(tmp_path)
    candidate[AUTHORED_SEMANTICS_KEY]["version"] = (
        "odylith.greenfield.authored-semantics.v2"
    )

    with pytest.raises(GreenfieldAuthoredSemanticsError, match="authored semantics are malformed"):
        greenfield_proposals.build_greenfield_proposal(
            repo_root=tmp_path,
            prompt="Build Harbor Desk",
            confirmed_intent=candidate,
            require_completion_ready=False,
        )


@pytest.mark.parametrize("mutation", ("recovery", "omission"))
def test_transaction_compilation_rejects_mutated_relation_set(
    tmp_path: Path,
    mutation: str,
) -> None:
    candidate = _materialized_authored_intent(tmp_path)
    mutated, relations = _mutated_relations(candidate)
    if mutation == "recovery":
        relations[0]["recovery_path"] = True
    else:
        del relations[1]
        relations[1]["order"] = 2
    proposal = {
        "projection_origin": AUTHORED_PROJECTION_ORIGIN,
        "intent": mutated,
        PRODUCT_INTENT_AUTHORITY_KEY: candidate[PRODUCT_INTENT_AUTHORITY_KEY],
    }

    expected_error = "do not match sealed Product Intent authority"
    with pytest.raises(GreenfieldAuthoredSemanticsError, match=expected_error):
        greenfield_proposals.compile_greenfield_create_transaction(
            repo_root=tmp_path,
            proposal=proposal,
            release_selector="0.0.1",
        )


def test_verified_relation_authority_issues_structural_tribunal_context(tmp_path: Path) -> None:
    candidate = _materialized_authored_intent(tmp_path)
    contracts = authored_component_relation_facts(
        title=candidate["title"],
        internal_systems=candidate["internal_systems"],
        relations=candidate[AUTHORED_SEMANTICS_KEY]["first_path_relations"],
        component_responsibility_relations=candidate[AUTHORED_SEMANTICS_KEY][
            "component_responsibility_relations"
        ],
    )
    contract = contracts[0]
    assert contracts[0]["responsibility_facts"] == ["Record berth occupancy"]
    assert contracts[1]["responsibility_facts"] == ["Show berth placement"]
    custody = authored_source_custody(
        intent=candidate,
        authority=candidate[PRODUCT_INTENT_AUTHORITY_KEY],
    )

    assert artifact_tribunal.source_custody_valid(custody)
    decision = artifact_tribunal.run_governed_artifact_tribunal(
        artifact_kind="component",
        payload={
            "component_id": "berth-recorder",
            "label": contract["owner_system"],
            "kind": "component",
            "path": "src/harbor-desk/berth-recorder",
            "responsibility": "; ".join(contract["responsibility_facts"]),
            "boundary": "",
            "interfaces": [],
            "dependencies": [],
            "validation": [],
            "risks": [],
        },
        source_custody=custody,
    )

    assert decision.passed, decision.issues
    assert decision.dimensions["typed_authority"].endswith(
        "artifact fidelity remains owned by the authored projection gate"
    )
    assert decision.dimensions["registry"] == (
        "source-custodied identity and owner-bound responsibility adjudicated"
    )


def test_verified_relation_authority_does_not_waive_authored_component_identity(tmp_path: Path) -> None:
    candidate = _materialized_authored_intent(tmp_path)
    custody = authored_source_custody(
        intent=candidate,
        authority=candidate[PRODUCT_INTENT_AUTHORITY_KEY],
    )

    decision = artifact_tribunal.run_governed_artifact_tribunal(
        artifact_kind="component",
        payload={
            "component_id": "berth-recorder",
            "label": "Berth recorder",
            "kind": "component",
            "path": "src/harbor-desk/berth-recorder",
            "responsibility": "",
            "boundary": "",
            "interfaces": [],
            "dependencies": [],
            "validation": [],
            "risks": [],
        },
        source_custody=custody,
    )

    assert not decision.passed
    assert "registry component must include `responsibility`" in decision.issues


def test_verified_relation_authority_allows_atlas_draft_without_invented_watch_paths(
    tmp_path: Path,
) -> None:
    candidate = _materialized_authored_intent(tmp_path)
    custody = authored_source_custody(
        intent=candidate,
        authority=candidate[PRODUCT_INTENT_AUTHORITY_KEY],
    )

    decision = artifact_tribunal.run_governed_artifact_tribunal(
        artifact_kind="atlas_diagram",
        payload={
            "diagram_id": "DRAFT-001",
            "slug": "harbor-desk-context",
            "title": "System Context View",
            "kind": "flowchart",
            "owner": "repo",
            "summary": "Accepted actors and candidate product-owned boundaries.",
            "components": ["berth-recorder", "berth-map"],
            "watch_paths": [],
            "related_backlog": [],
            "related_plans": [],
            "related_docs": [],
            "related_code": [],
        },
        source_custody=custody,
    )

    assert decision.passed, decision.issues
    assert decision.dimensions["atlas"] == (
        "source-custodied diagram identity, components, and draft posture adjudicated"
    )
