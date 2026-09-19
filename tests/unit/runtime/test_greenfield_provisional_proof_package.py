"""A proposed checkpoint remains visibly provisional through a complete package."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_commit, greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import (
    authored_projection_parity_issues,
    build_authored_greenfield_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_candidate_intent_stage import render_candidate_intent_markdown
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import materialize_model_authored_intent
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import STANDARD_PROFILE_ID
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_preconfirm_semantic_alignment import semantic_model_shape_issues
from odylith.runtime.domain_intelligence.project_intelligence_binding import attach_project_intelligence_bindings
from tests.unit.runtime.greenfield_baseline_fixtures import activate_greenfield_baseline_fixture
from tests.unit.runtime.greenfield_model_authoring_fixtures import AdmittingReviewProvider, RemainingCandidateProvider
from tests.unit.runtime.greenfield_proposal_fixtures import seal_compiled_greenfield_transaction
from tests.unit.runtime.test_greenfield_provisional_proof_authoring import provisional_proof_response


def _proposal(root: Path) -> dict:
    source, response = provisional_proof_response()
    provider = RemainingCandidateProvider(response)
    receipt = {}
    candidate = materialize_model_authored_intent(
        prompt=source,
        repo_root=root,
        authoring_provider=provider,
        participant_provider_factory=provider.participant_provider,
        review_provider_factory=AdmittingReviewProvider,
        authoring_profile_id=STANDARD_PROFILE_ID,
        authoring_timeout_seconds=60,
        authoring_receipt=receipt,
    )
    proposal = build_authored_greenfield_proposal(
        observed_source={"source_posture": "operator prompt evidence"},
        release_selector="0.0.1",
        confirmed_intent=candidate,
    )
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = candidate[PRODUCT_INTENT_AUTHORITY_KEY]
    proposal = attach_project_intelligence_bindings(proposal)
    proposal["_test_model_authoring_receipt"] = receipt
    return proposal


def test_commit_only_version_admission_matches_preconfirm_custody() -> None:
    from odylith.runtime.domain_intelligence.greenfield_commit_transaction import _CURRENT_SEALED_INTENT_VERSIONS
    from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
        ATOMIC_FACT_LEDGER_VERSION,
        PRODUCT_INTENT_AUTHORITY_VERSION,
        PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION,
        PRODUCT_INTENT_LEDGER_VERSION,
    )

    assert _CURRENT_SEALED_INTENT_VERSIONS == {
        "version": PRODUCT_INTENT_AUTHORITY_VERSION,
        "envelope_schema_version": PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION,
        "ledger_version": PRODUCT_INTENT_LEDGER_VERSION,
        "atomic_ledger_version": ATOMIC_FACT_LEDGER_VERSION,
    }


def test_all_package_views_keep_checkpoint_out_of_source_truth(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    intent = proposal["intent"]
    assert not intent.get("proof_boundary")
    assert not any(row["visible_result_quote"] for row in intent["authored_semantics"]["first_path_relations"])
    assert authored_projection_parity_issues(proposal) == []
    preview = render_candidate_intent_markdown(intent)
    assert "## Proposed proof checkpoint\nAssumption — " in preview
    assert "## Proof boundary" not in preview
    for row in proposal["backlog"]:
        assert row["radar_sections"]["Proposed Proof Checkpoint"].startswith("Assumption — ")
        assert "Source Proof Boundary" not in row["radar_sections"]
    brief = proposal["project_brief"]
    assert "The accepted release proof boundary." not in str(brief)
    assert "Proposed proof checkpoint" in str(brief)
    assert proposal["semantic_model"]["domain_ontology"]["proof_boundary"] == ""
    assert all(row["authority_kind"] == "assumption" for row in proposal["semantic_model"]["proof_obligations"])
    support = next(row for row in proposal["diagrams"] if row["slug"].endswith("capability-support"))
    assert "Proposed proof checkpoint — assumption" in support["mermaid_source"]
    assert "Source-stated proof boundary:" not in str(support["diagram_boxes"])
    assert "Source-stated visible result:" not in str(support["diagram_boxes"])


@pytest.mark.parametrize("surface", ["backlog", "diagrams", "semantic_model"])
def test_relabeling_a_proposed_checkpoint_as_source_is_projection_drift(tmp_path: Path, surface: str) -> None:
    proposal = deepcopy(_proposal(tmp_path))
    if surface == "backlog":
        sections = proposal[surface][0]["radar_sections"]
        sections["Source Proof Boundary"] = sections.pop("Proposed Proof Checkpoint")
    elif surface == "diagrams":
        row = next(row for row in proposal[surface] if row["slug"].endswith("capability-support"))
        row["mermaid_source"] = row["mermaid_source"].replace("Proposed proof checkpoint — assumption", "Source-stated facts")
    else:
        proposal[surface]["proof_obligations"][0]["authority_kind"] = "source_grounded"
    assert authored_projection_parity_issues(proposal)


def test_semantic_shape_requires_the_exact_canonical_assumption(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    semantic, intent = proposal["semantic_model"], proposal["intent"]
    assert semantic_model_shape_issues(semantic, intent=intent) == []
    assert semantic_model_shape_issues(semantic)
    missing = deepcopy(intent)
    missing["assumptions"] = [row for row in missing["assumptions"] if row["applies_to"] != "proof_boundary"]
    assert semantic_model_shape_issues(semantic, intent=missing)
    changed = deepcopy(semantic)
    changed["proof_obligations"][0]["authority_kind"] = "source_grounded"
    assert semantic_model_shape_issues(changed, intent=intent)
    changed = deepcopy(semantic)
    changed["first_path_contract"]["visible_result"] = "A different proposed outcome."
    assert semantic_model_shape_issues(changed, intent=intent)


def test_proposed_checkpoint_compiles_and_commits_only_sealed_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    proposal = _proposal(tmp_path)
    activate_greenfield_baseline_fixture(tmp_path)
    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        model_authoring_receipt=proposal["_test_model_authoring_receipt"],
    )
    sealed = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("CONFIRM must not compile or reinterpret proposed proof")

    monkeypatch.setattr(greenfield_proposals, "compile_greenfield_create_transaction", forbidden)
    results = [greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=sealed.transaction_file,
        transaction_hash=sealed.transaction_hash,
        confirm=True,
    ) for _ in range(2)]
    assert all(result["commit_manifest"]["status"] == "passed" for result in results)
    assert (tmp_path / "odylith/index.html").exists()
