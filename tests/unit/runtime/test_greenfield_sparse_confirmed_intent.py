from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo


def test_sparse_confirmed_intent_uses_grammatical_state_phrase_before_writes(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(
        greenfield_apply_write.component_authoring.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_apply_write.scaffold_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_apply_write,
        "_raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "skipped_in_sparse_semantic_unit"},
    )
    prompt = (
        "Create a greenfield proposal for a cross-organization disclosure council that receives reports, "
        "coordinates review, records evidence custody, decides embargo status, and publishes release readiness proof."
    )
    intent_path = tmp_path / ".odylith/runtime/greenfield/confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(
        """
# Product Intent Confirmation

## Title
Disclosure council

## Product story
External researchers and internal owners coordinate a disclosure review.

## State object
Report.

## First complete path
Reporter submits a report; owner reviews it; council publishes proof.

## Actors
Reporter, owner, council.

## Systems
Intake desk, review log.

## Assumptions
The first release records evidence only.

## Ambiguities
Notification delivery is not included.

## Proof boundary
Evidence custody and embargo decision.
""".strip()
        + "\n",
        encoding="utf-8",
    )

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--release",
            "0.0.1",
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
        (tmp_path / ".odylith/runtime/greenfield/confirmed-intent.json").read_text(encoding="utf-8")
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
