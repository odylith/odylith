from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import stub_preconfirm_surface_refresh


def test_sparse_confirmed_intent_uses_grammatical_state_phrase_before_writes(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    stub_preconfirm_surface_refresh(monkeypatch)
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(
        greenfield_component_commit.component_authoring.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "skipped_in_sparse_semantic_unit"},
    )
    prompt = (
        "Create a greenfield proposal for a cross-organization disclosure council that receives reports, "
        "coordinates review, records evidence custody, decides embargo status, and publishes release readiness proof."
    )
    edit_evidence = """
EDIT

## State object
Report.

## Problem
Cross-organization disclosure council users need a dependable way to understand Report and decide the next step.

## Proof boundary
Trusted evidence custody and embargo decision.

## Internal product systems
- Intake desk records disclosure reports.
- Review log records cross-organization review decisions.
- Embargo registry tracks embargo status.
""".strip()
    transaction_file = ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    propose_rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--edit",
            edit_evidence,
            "--format",
            "json",
        ]
    )
    propose_output = capsys.readouterr().out
    assert propose_rc == 0, propose_output
    transaction_hash = str(json.loads(propose_output)["product_create_transaction"]["transaction_hash"])
    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            transaction_file,
            "--transaction-hash",
            transaction_hash,
            "--confirm",
            "--json",
        ]
    )

    output = capsys.readouterr().out
    assert rc == 0, output
    payload = json.loads(output)
    manifest = payload["post_confirm_quality_manifest"]
    assert manifest["status"] == "passed"
    assert manifest["write_transaction"]["status"] == "committed"
    structured_intent = json.loads(
        (tmp_path / ".odylith/runtime/greenfield/candidate-intent.json").read_text(encoding="utf-8")
    )
    assert "embargo" in structured_intent["proof_boundary"].casefold()
    assert "trusted" in structured_intent["proof_boundary"].casefold()
    assert not structured_intent["proof_boundary"].casefold().endswith(("result is.", "before."))
    assert len(structured_intent["internal_systems"]) >= 3
    assert any("embargo" in row.casefold() for row in structured_intent["internal_systems"])
    assert len(payload["components"]) >= 3
    assert any("embargo" in str(row.get("label", "")).casefold() for row in payload["components"])
    accepted = json.loads((tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8"))
    encoded = json.dumps(accepted)
    assert "understand Report" not in encoded
    assert "understand the report" in encoded
    review_specs = [
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md")
        if "review-log" in str(path)
    ]
    assert review_specs
    assert len(list((tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md"))) >= 3
    rendered_review_log = "\n".join(review_specs)
    assert "owns review log.." not in rendered_review_log
    assert "Relevant behavior." not in rendered_review_log
    assert generated_semantic_slop_issues(accepted, root="proposal") == []
