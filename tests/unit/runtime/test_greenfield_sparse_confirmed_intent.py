from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    load_compiled_product_create_transaction_file,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_FACTS_HASH_KEY
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import stub_preconfirm_surface_refresh


ROOT = Path(__file__).resolve().parents[3]
PORT_OPERATIONS_PROMPT = json.loads(
    (ROOT / "tests/fixtures/greenfield-volume/logistics-infrastructure.v1.json").read_text(encoding="utf-8")
)["cases"][0]["prompt"]


def _stub_commit_only_create_dependencies(monkeypatch) -> None:
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


def test_sparse_confirmed_intent_uses_grammatical_state_phrase_before_writes(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    _stub_commit_only_create_dependencies(monkeypatch)
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
    propose_payload = json.loads(propose_output)
    transaction_hash = str(propose_payload["product_create_transaction"]["transaction_hash"])
    transaction_file = str(propose_payload["transaction_file"])
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
    manifest = payload["commit_manifest"]
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


def test_port_prompt_compiles_visible_constraints_into_a_commit_only_transaction(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    _stub_commit_only_create_dependencies(monkeypatch)
    prompt = (
        "Build a berth turnaround control workspace where a terminal coordinator opens the morning vessel call "
        "at Pier 7, reconciles carrier manifests with berth assignments, records an exception, and sees a signed "
        "handoff receipt."
    )
    propose_rc = greenfield_proposals.main(
        ["propose", "--repo-root", str(tmp_path), "--prompt", prompt, "--format", "json"]
    )
    propose_output = capsys.readouterr().out

    assert propose_rc == 0, propose_output
    proposed = json.loads(propose_output)
    candidate = proposed["intent_hypothesis"]
    transaction_path = tmp_path / str(proposed["transaction_file"])
    transaction = load_compiled_product_create_transaction_file(transaction_path)
    proposal = transaction.proposal
    assert "Pier 7" in candidate["operational_constraints"]
    assert "Pier 7" in proposal["intent"]["operational_constraints"]
    assert "Pier 7" in proposal["semantic_model"]["domain_ontology"]["operational_constraints"]
    assert "Pier 7" in proposal["project_brief"]["operational_constraints"]
    assert candidate["product_intent_authority"][PRODUCT_FACTS_HASH_KEY] == transaction.intent_authority[
        PRODUCT_FACTS_HASH_KEY
    ]

    create_rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            str(transaction_path),
            "--transaction-hash",
            transaction.transaction_hash,
            "--confirm",
            "--json",
        ]
    )
    create_output = capsys.readouterr().out

    assert create_rc == 0, create_output
    manifest = json.loads(create_output)["commit_manifest"]
    assert manifest["status"] == "passed"
    assert manifest["write_transaction"]["status"] == "committed"


def test_logistics_fixture_compiles_a_clean_confirmation_transaction_and_commits(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    _stub_commit_only_create_dependencies(monkeypatch)
    propose_rc = greenfield_proposals.main(
        ["propose", "--repo-root", str(tmp_path), "--prompt", PORT_OPERATIONS_PROMPT, "--format", "json"]
    )
    propose_output = capsys.readouterr().out

    assert propose_rc == 0, propose_output
    proposed = json.loads(propose_output)
    candidate = proposed["intent_hypothesis"]
    transaction_path = tmp_path / str(proposed["transaction_file"])
    transaction = load_compiled_product_create_transaction_file(transaction_path)
    proposal = transaction.proposal
    assert "port operations director" not in candidate["title"].casefold()
    assert "berth planner" in candidate["first_path"].casefold()
    assert "quay crane availability" in candidate["first_path"].casefold()
    assert "carrier manifests" not in candidate["first_path"].casefold()
    assert "weather holds" not in candidate["first_path"].casefold()
    assert "customs clearance" not in candidate["first_path"].casefold()
    assert candidate["evidence_requirements"] == ["carrier manifests"]
    assert "Pier 7" in candidate["operational_constraints"]
    assert "Pier 7" in proposal["semantic_model"]["domain_ontology"]["operational_constraints"]
    assert proposal["intent"]["evidence_requirements"] == ["carrier manifests"]

    create_rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            str(transaction_path),
            "--transaction-hash",
            transaction.transaction_hash,
            "--confirm",
            "--json",
        ]
    )
    create_output = capsys.readouterr().out

    assert create_rc == 0, create_output
    manifest = json.loads(create_output)["commit_manifest"]
    assert manifest["status"] == "passed"
    assert manifest["write_transaction"]["status"] == "committed"


@pytest.mark.parametrize(
    ("prompt", "edit", "expected_constraints"),
    (
        (
            (
                "Build a berth turnaround control workspace where a terminal coordinator opens one vessel call at "
                "Pier 7, reconciles carrier manifests with berth assignments, records an exception, and sees a "
                "signed handoff receipt."
            ),
            (
                "## First complete path\n"
                "A terminal coordinator opens one vessel call at Pier 9, reconciles carrier manifests with berth "
                "assignments, records an exception, and sees a signed handoff receipt."
            ),
            ("Pier 9",),
        ),
        (
            (
                "Build a berth turnaround control workspace where a terminal coordinator opens one vessel call, "
                "reconciles carrier manifests with berth assignments, records an exception, and sees a signed "
                "handoff receipt."
            ),
            (
                "## First complete path\n"
                "A terminal coordinator opens one vessel call at Pier 7, reconciles carrier manifests with berth "
                "assignments, records an exception, and sees a signed handoff receipt."
            ),
            ("Pier 7",),
        ),
        (
            (
                "Build a berth turnaround control workspace where a terminal coordinator opens one vessel call at "
                "Pier 7, reconciles carrier manifests with berth assignments, records an exception, and sees a "
                "signed handoff receipt."
            ),
            (
                "## First complete path\n"
                "A terminal coordinator opens one vessel call at Pier 9, reconciles carrier manifests with berth "
                "assignments, records an exception, and sees a signed handoff receipt.\n\n"
                "## Operational constraints\n"
                "- Pier 7"
            ),
            ("Pier 7",),
        ),
        (
            (
                "Build a berth turnaround control workspace where a terminal coordinator opens one vessel call at "
                "Pier 7, reconciles carrier manifests with berth assignments, records an exception, and sees a "
                "signed handoff receipt."
            ),
            (
                "## First complete path\n"
                "A terminal coordinator opens one vessel call, reconciles carrier manifests with berth assignments, "
                "records an exception, and sees a signed handoff receipt."
            ),
            ("Pier 7",),
        ),
        (
            (
                "Build a berth turnaround control workspace where a terminal coordinator opens one vessel call at "
                "Pier 7 during the morning shift before noon, reconciles carrier manifests with berth assignments, "
                "records an exception, and sees a signed handoff receipt."
            ),
            (
                "## First complete path\n"
                "A terminal coordinator opens one vessel call at Pier 9, reconciles carrier manifests with berth "
                "assignments, records an exception, and sees a signed handoff receipt."
            ),
            ("Pier 9", "morning shift", "before noon"),
        ),
        (
            (
                "Build a berth turnaround control workspace where a terminal coordinator opens one vessel call at "
                "Pier 7, reconciles carrier manifests with berth assignments, records an exception, and sees a "
                "signed handoff receipt."
            ),
            (
                "## First complete path\n"
                "A terminal coordinator opens one vessel call, reconciles carrier manifests with berth assignments, "
                "records an exception, and sees a signed handoff receipt.\n\n"
                "## Operational constraints\n"
                "- None"
            ),
            (),
        ),
        (
            (
                "Build a berth turnaround control workspace for Pier 7 where a terminal coordinator opens one "
                "vessel call, reconciles carrier manifests with berth assignments, records an exception, and sees "
                "a signed handoff receipt."
            ),
            (
                "## First complete path\n"
                "A terminal coordinator opens one vessel call at Pier 9, reconciles carrier manifests with berth "
                "assignments, records an exception, and sees a signed handoff receipt."
            ),
            ("Pier 9",),
        ),
    ),
)
def test_edit_rebuilds_operational_constraints_before_commit_only_create(
    tmp_path: Path,
    monkeypatch,
    capsys,
    prompt: str,
    edit: str,
    expected_constraints: tuple[str, ...],
) -> None:
    _seed_empty_governance_repo(tmp_path)
    _stub_commit_only_create_dependencies(monkeypatch)
    propose_rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--edit",
            edit,
            "--format",
            "json",
        ]
    )
    propose_output = capsys.readouterr().out

    assert propose_rc == 0, propose_output
    proposed = json.loads(propose_output)
    candidate = proposed["intent_hypothesis"]
    transaction_path = tmp_path / str(proposed["transaction_file"])
    transaction = load_compiled_product_create_transaction_file(transaction_path)
    expected = list(expected_constraints)
    assert candidate["operational_constraints"] == expected
    assert transaction.proposal["intent"]["operational_constraints"] == expected
    assert transaction.proposal["semantic_model"]["domain_ontology"]["operational_constraints"] == expected
    assert transaction.proposal["project_brief"]["operational_constraints"] == expected

    create_rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            str(transaction_path),
            "--transaction-hash",
            transaction.transaction_hash,
            "--confirm",
            "--json",
        ]
    )
    create_output = capsys.readouterr().out

    assert create_rc == 0, create_output
    assert json.loads(create_output)["commit_manifest"]["write_transaction"]["status"] == "committed"
