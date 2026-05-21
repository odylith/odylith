from __future__ import annotations

import json
import os

from odylith.runtime.domain_intelligence import greenfield_proposals
from tests.unit.runtime.greenfield_proposal_fixtures import _confirmed_intent
from tests.unit.runtime.greenfield_proposal_fixtures import _host_reasoned_ecommerce_proposal
from tests.unit.runtime.greenfield_proposal_fixtures import _markdown_section
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import _write_confirmed_intent


def test_greenfield_text_starts_with_product_intent_confirmation(tmp_path, capsys) -> None:
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Design a mathematics research workspace for spectral graph theory",
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert "Product Intent Confirmation needed" in output
    assert "No files changed." in output
    assert "Host reasoning task" in output
    assert "Visible format contract" in output
    assert "Render the visible confirmation as sectioned Markdown" in output
    assert "Product story; State object; First complete path; Human actors" in output
    assert "Use bullets for Human actors, External systems, Internal product systems" in output
    assert "Render Next step as three separate bullet lines: Confirm, Edit, and Reject" in output
    assert "Write in chat" in output
    assert "Do not" in output
    assert "echo command instructions as the product name" in output
    assert "collapse the confirmation into a wall of prose without clear sections" in output
    assert "use Markdown emphasis or code formatting around normal domain words" in output
    assert "generate implementation records, architecture records, release waves, validation obligations, or proposal JSON before confirmation" in output
    assert "Original user intent" in output
    assert "Next step" in output
    assert "- Confirm: if the interpretation is right" in output
    assert "- Edit: if the product story, actors, systems, assumptions, first path, or proof boundary is wrong" in output
    assert "- Reject: if this is not the intended product" in output
    assert "No records were written. Confirm, edit, or reject this interpretation." not in output
    assert "greenfield create --repo-root ." in output
    assert "--confirm" in output
    assert "Confirmed CLI after confirmation" in output
    assert "--intent-file .odylith/runtime/greenfield/confirmed-intent.md" in output
    assert "дж" not in output
    assert "soн" not in output
    assert "..." not in output
    assert "Gate 1 - Interpretation" not in output
    assert "Product workstreams:" not in output
    assert "Candidate product boundaries:" not in output
    assert "Architecture review views:" not in output
    assert "Records after confirmation" not in output
    assert "A Mathematics Research Workspace For Spectral Graph Theory System Overview" not in output
    assert "A Mathematics Research Workspace For Spectral Graph Theory First Slice Flow" not in output
    assert "apply-ready JSON" not in output
    assert "provider_calls_by_odylith_cli" not in output
    assert "mode: host_reasoned_greenfield_proposal" not in output
    assert "shared artifact:" not in output
    assert "Project-first blueprint" not in output
    assert "Workstream domain intelligence" not in output
    assert len(output.splitlines()) <= 38
    assert len(output) <= 3200


def test_greenfield_confirm_intent_shows_direct_apply_handoff(tmp_path, capsys) -> None:
    _write_confirmed_intent(tmp_path)
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a municipal permit review workspace",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--confirm-intent",
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert "Odylith greenfield proposal: Municipal Permit Review Workspace" in output
    assert "No files changed" in output
    assert "- governed proposal: built from confirmed intent, normalized, validated" in output
    assert "- mode: host_reasoned_greenfield_proposal" in output
    assert "Project requirements" in output
    assert "Project-first blueprint" in output
    assert "Backlog proposal" in output
    assert "Planned components" in output
    assert "Draft architecture diagrams" in output
    assert "greenfield create --repo-root ." in output
    assert "--intent-file .odylith/runtime/greenfield/confirmed-intent.md" in output
    assert "internal apply payload" not in output
    assert "active-proposal.v1.json" not in output
    assert "host_instruction" not in output
    assert "reasoning_contract" not in output


def test_greenfield_confirm_intent_without_intent_file_fails_closed(tmp_path, capsys) -> None:
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a municipal permit review workspace",
            "--confirm-intent",
        ]
    )

    assert rc == 2
    output = capsys.readouterr().out
    assert "requires --intent-file" in output
    assert "will not write records from a thin prompt" in output


def test_greenfield_text_full_detail_keeps_apply_path_available_after_intent_confirmed(tmp_path, capsys) -> None:
    _write_confirmed_intent(tmp_path)
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a municipal permit review workspace",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--confirm-intent",
            "--detail",
            "full",
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert "Odylith greenfield proposal: Municipal Permit Review Workspace" in output
    assert "Gate 1 - Interpretation" not in output
    assert "Gate 2 - Clarify Before Apply" not in output
    assert "Gate 3 - Proposal Preview" not in output
    assert "Gate 4 - Choose Next Action" not in output
    assert "Backlog proposal" in output
    assert "Planned components" in output
    assert "Draft architecture diagrams" in output
    assert "odylith greenfield create --repo-root ." in output
    assert "--intent-file .odylith/runtime/greenfield/confirmed-intent.md" in output
    assert "--confirm" in output
    assert "internal apply payload" not in output
    assert ".odylith/runtime/greenfield/active-proposal.v1.json" not in output
    assert len(output.splitlines()) <= 270


def test_greenfield_title_preserves_meaningful_trailing_domain_terms(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="field inspection evidence workspace for municipal building permits",
        confirmed_intent=_confirmed_intent(),
    )

    assert proposal["intent"]["title"] == "Municipal Permit Review Workspace"
    assert not proposal["intent"]["title"].endswith(" To")


def test_greenfield_cli_json_defaults_to_intent_confirmation(tmp_path, capsys) -> None:
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Build a statistics notebook repo",
            "--format",
            "json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "product_intent_reasoning_request"
    assert payload["provider_calls"] == 0
    assert payload["write_policy"] == "host_reason_product_intent_before_confirmed_greenfield_create"
    assert payload["host_reasoning_task"]["must_include"]
    assert payload["host_reasoning_task"]["must_not"]
    assert payload["host_reasoning_task"]["format_contract"]
    assert "sectioned Markdown" in " ".join(payload["host_reasoning_task"]["format_contract"])
    assert "Product story; State object; First complete path; Human actors" in " ".join(payload["host_reasoning_task"]["format_contract"])
    assert "three separate bullet lines: Confirm, Edit, and Reject" in " ".join(payload["host_reasoning_task"]["format_contract"])
    assert "three separate bullet lines for Confirm, Edit, and Reject" in " ".join(payload["host_reasoning_task"]["must_include"])
    assert "dump a generic template or domain catalog" in payload["host_reasoning_task"]["must_not"]
    assert "collapse the confirmation into a wall of prose without clear sections" in payload["host_reasoning_task"]["must_not"]
    assert "use Markdown emphasis or code formatting around normal domain words" in payload["host_reasoning_task"]["must_not"]
    assert "backlog" not in payload
    assert "components" not in payload
    assert "diagrams" not in payload


def test_greenfield_cli_json_is_governed_audit_after_intent_confirmation(tmp_path, capsys) -> None:
    _write_confirmed_intent(tmp_path)
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a municipal permit review workspace",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--confirm-intent",
            "--format",
            "json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "host_reasoned_greenfield_proposal"
    assert payload["provider_calls"] == 0
    assert payload["intent"]["reasoning_mode"] == "odylith_confirmed_governed_proposal"
    encoded = json.dumps(payload)
    assert "Permit File Registry" in encoded
    assert "Zoning Check Ledger" in encoded
    assert "Municipal Permit Review Workspace Workflow Service" not in encoded
    assert "reasoning_contract" not in payload
    assert "host_instruction" not in payload
    assert "canonical_proposal" not in payload
    assert "proposal_template" not in payload
    assert len(payload["backlog"]) >= 4
    assert len(payload["components"]) >= 3
    assert len(payload["diagrams"]) >= 6


def test_greenfield_apply_cli_prints_operator_handoff(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps(_host_reasoned_ecommerce_proposal()), encoding="utf-8")

    rc = greenfield_proposals.main(
        ["apply", "--repo-root", str(tmp_path), "--proposal-file", str(proposal_path), "--confirm", "--release", "0.0.1"]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "- project-first workstream: B-001 Govern Commerce Launch System" in out
    assert "- project story: odylith/index.html?tab=project" in out
    assert "- workstream detail: odylith/radar/radar.html?view=plan&workstream=B-001" in out
    assert "- project gate: review direction choices and readiness gates before opening a technical plan; do not edit source from this closeout" in out
    assert "- current project lane: wave Checkout spine | release 0.0.1" in out
    assert "- choose before coding:" in out
    assert "- coding readiness gates:" in out
    assert "- future first implementation lane after gates: B-002 Define Storefront boundary" in out
    assert "- operator handoff:" in out
    assert "./.odylith/bin/odylith validate plan-workstream-binding --repo-root ." in out


def test_greenfield_prompt_paths_do_not_expose_legacy_apply_ready_scaffold(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a home automation product with a physical device and a care outcome.",
        ]
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert "Product Intent Confirmation needed" in out
    assert "Host reasoning task" in out
    assert "raw greenfield intent" not in out

    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a home automation product with a physical device and a care outcome.",
            "--confirm-intent",
        ]
    )
    out = capsys.readouterr().out

    assert rc == 2
    assert "requires --intent-file" in out
    assert "will not write records from a thin prompt" in out
    assert "internal apply payload" not in out
    assert "active-proposal.v1.json" not in out
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []


def test_greenfield_create_cli_applies_confirmed_prompt(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    _write_confirmed_intent(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a municipal permit review workspace",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--release",
            "0.0.1",
            "--confirm",
        ]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "greenfield create wrote confirmed proposal" in out
    assert "- validation gate: passed" in out
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert (tmp_path / "odylith/runtime/source/accepted-project.v1.json").is_file()
    accepted = (tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8")
    assert "Permit File Registry" in accepted
    assert "Municipal Permit Review Workspace Workflow Service" not in accepted
    assert (tmp_path / "odylith/registry/source/component_registry.v1.json").is_file()
    assert list((tmp_path / "odylith/atlas/source").glob("*.mmd"))
    spec_root = tmp_path / "odylith/registry/source/components"
    specs = {path.parent.name: path.read_text(encoding="utf-8") for path in spec_root.glob("*/CURRENT_SPEC.md")}
    permit_spec = specs["permit-file-registry"]
    zoning_spec = specs["zoning-check-ledger"]
    revision_spec = next(text for slug, text in specs.items() if slug.endswith("revision-tracker"))
    decision_spec = specs["decision-package-review"]
    assert "permit identity attachment" in permit_spec
    assert "required document completeness" in permit_spec
    assert "missing document blockers" in permit_spec
    assert "handoff into Zoning Check Ledger" in permit_spec
    assert "zoning checks, reviewer comments, rule references, and pass or block outcomes" in zoning_spec
    assert "applicant revisions to the documents and checks they are meant to address" in revision_spec
    assert "evidence, reviewer notes, unresolved blockers, and final approval state" in decision_spec
    role_sections = [
        _markdown_section(permit_spec, "## Component Role"),
        _markdown_section(zoning_spec, "## Component Role"),
        _markdown_section(revision_spec, "## Component Role"),
        _markdown_section(decision_spec, "## Component Role"),
    ]
    assert len(set(role_sections)) == 4
    for text in (permit_spec, zoning_spec, revision_spec, decision_spec):
        assert "Product context:" not in text
        assert "Project outcome:" not in text
        assert "Release 0.0.1 contribution:" not in text
        assert "accepted first release path" not in text
        assert "Contract proof covers" not in text
        assert "Contract focus:" not in text
        assert "Primary interface:" not in text
        assert "Proof obligation:" not in text
        assert ". and" not in text
        assert ". or" not in text
        assert "zoning, check" not in text
        assert "revision, tracker" not in text
        assert "decision, package" not in text
        assert "Failure Modes" in text
        assert "Domain risk:" in text
        assert "Security and policy posture:" in text
        assert "**" not in text
        assert "…" not in text
    catalog = json.loads((tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json").read_text(encoding="utf-8"))
    for diagram in catalog["diagrams"]:
        assert diagram["change_watch_paths"]
        assert "odylith/atlas/source" not in diagram["change_watch_paths"]


def test_greenfield_create_cli_requires_confirmation_before_writes(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "warehouse dispatch planning app",
            "--release",
            "0.0.1",
        ]
    )

    out = capsys.readouterr().out
    assert rc == 2
    assert "greenfield create requires --confirm" in out
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_create_cli_requires_confirmed_intent_file_before_writes(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a municipal permit review workspace",
            "--release",
            "0.0.1",
            "--confirm",
        ]
    )

    out = capsys.readouterr().out
    assert rc == 2
    assert "requires --intent-file" in out
    assert "will not write records from a thin prompt" in out
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_apply_json_output_is_machine_clean(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    def noisy_refresh(**_kwargs: object) -> None:
        print("refresh progress that must not contaminate JSON stdout", flush=True)
        os.write(1, b"fd-level refresh progress must not contaminate JSON stdout\n")

    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", noisy_refresh)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps(_host_reasoned_ecommerce_proposal()), encoding="utf-8")

    rc = greenfield_proposals.main(
        [
            "apply",
            "--repo-root",
            str(tmp_path),
            "--proposal-file",
            str(proposal_path),
            "--confirm",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["mode"] == "applied"
    assert payload["atlas_scaffold_logs"]
    assert payload["memory"]["recorded"] is True
    assert payload["memory"]["event"]["source"] == "domain-intelligence"
    assert payload["validation_gate"]["status"] == "passed"
    assert "tribunal" not in payload
    assert all("tribunal" not in line.casefold() for line in payload["atlas_scaffold_logs"])
    assert all("validation_gate" in row and "tribunal" not in row for row in payload["components"])
    assert payload["dashboard_refresh"]["surfaces"] == ["radar", "registry", "atlas", "compass", "tooling_shell"]
    assert payload["dashboard_refresh"]["view"] == "odylith/index.html?tab=project"
    assert payload["release_target"]["release_id"] == "release-commerce-launch-first"
    assert payload["operator_output"] == [
        "refresh progress that must not contaminate JSON stdout",
        "fd-level refresh progress must not contaminate JSON stdout",
    ]


def test_greenfield_apply_json_error_is_machine_clean(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    rc = greenfield_proposals.main(
        [
            "apply",
            "--repo-root",
            str(tmp_path),
            "--proposal-json",
            "{not-json",
            "--confirm",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 2
    assert payload["mode"] == "error"
    assert "Expecting property name enclosed in double quotes" in payload["error"]
