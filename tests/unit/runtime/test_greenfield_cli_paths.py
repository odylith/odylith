from __future__ import annotations

import json
import os
import re
from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_text import normalize_domain_token
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_proposals
from tests.unit.runtime.greenfield_proposal_fixtures import _confirmed_intent
from tests.unit.runtime.greenfield_proposal_fixtures import _host_reasoned_ecommerce_proposal
from tests.unit.runtime.greenfield_proposal_fixtures import _markdown_section
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import _write_confirmed_intent


def _write_stubbed_atlas_render_outputs(repo_root: Path) -> None:
    for relative_path in (
        "odylith/atlas/atlas.html",
        "odylith/atlas/mermaid-payload.v1.js",
        "odylith/atlas/mermaid-app.v1.js",
    ):
        path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stubbed official Atlas render\n", encoding="utf-8")
    catalog_path = repo_root / "odylith/atlas/source/catalog/diagrams.v1.json"
    if not catalog_path.is_file():
        return
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    for diagram in catalog.get("diagrams", []):
        svg_path = repo_root / str(diagram.get("source_svg", ""))
        png_path = repo_root / str(diagram.get("source_png", ""))
        if svg_path.name:
            svg_path.parent.mkdir(parents=True, exist_ok=True)
            svg_path.write_text("<svg viewBox='0 0 1200 800'><title>Mermaid</title></svg>\n", encoding="utf-8")
        if png_path.name:
            png_path.parent.mkdir(parents=True, exist_ok=True)
            png_path.write_bytes(b"\x89PNG\r\n\x1a\n")
        watched = [str(path) for path in diagram.get("change_watch_paths", []) if str(path).strip()]
        diagram["reviewed_watch_fingerprints"] = {path: "stubbed-official-refresh" for path in watched}
        diagram["render_source_fingerprint"] = "stubbed-official-refresh"
    catalog_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _stub_dashboard_refresh(monkeypatch, calls: list[dict[str, object]] | None = None) -> None:
    def refresh(**kwargs: object) -> None:
        if calls is not None:
            calls.append(dict(kwargs))
        _write_stubbed_atlas_render_outputs(Path(str(kwargs["repo_root"])))

    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", refresh)


def test_greenfield_domain_token_normalizer_keeps_common_words_legible() -> None:
    assert normalize_domain_token("attaches") == "attach"
    assert normalize_domain_token("matches") == "match"
    assert normalize_domain_token("processes") == "process"
    assert normalize_domain_token("statuses") == "status"
    assert normalize_domain_token("readings") == "reading"


def test_greenfield_text_renders_confirmable_product_intent(tmp_path, capsys) -> None:
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
    assert "Product Intent Confirmation" in output
    assert "Product story" in output
    assert "State object" in output
    assert "First complete path" in output
    assert "Human actors" in output
    assert "External systems" in output
    assert "Internal product systems" in output
    assert "Critical assumptions" in output
    assert "Ambiguities" in output
    assert "Proof boundary" in output
    assert "Next step" in output
    assert "- `Confirm`: if this interpretation is right" in output
    assert "- `Edit`: if the product story, actors, systems, assumptions, first path, or proof boundary is wrong" in output
    assert "- `Reject`: if this is not the intended product" in output
    assert "Host reasoning task" not in output
    assert "Visible format contract" not in output
    assert "Original user intent" not in output
    assert "No files changed." not in output
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
    assert len(output.splitlines()) <= 72
    assert len(output) <= 6400


def test_greenfield_propose_stdout_can_be_confirmed_and_created(tmp_path, capsys) -> None:
    prompt = (
        "Create a greenfield proposal for a flood shelter intake system that helps city staff register displaced "
        "residents, match household needs to shelter capacity, track medical and accessibility constraints, "
        "preserve consent evidence, and produce a daily placement readiness report."
    )
    rc = greenfield_proposals.main(["propose", "--repo-root", str(tmp_path), "--prompt", prompt])
    confirmation = capsys.readouterr().out
    assert rc == 0
    assert "Host reasoning task" not in confirmation
    assert "Original user intent" not in confirmation
    intent_path = tmp_path / ".odylith/runtime/greenfield/confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(confirmation, encoding="utf-8")

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--confirm",
            "--release",
            "0.0.1",
            "--json",
        ]
    )
    output = capsys.readouterr().out

    assert rc == 0, output
    assert "No governed records were written" not in output
    assert "post-confirm completion failed" not in output
    assert (tmp_path / "odylith/radar/source").is_dir()
    assert (tmp_path / "odylith/registry/source/components").is_dir()
    assert (tmp_path / "odylith/atlas/source").is_dir()
    assert (tmp_path / ".odylith/runtime/greenfield/confirmed-intent.json").is_file()


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
    _stub_dashboard_refresh(monkeypatch)
    monkeypatch.setattr(greenfield_apply_write.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
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
    assert "Product Intent Confirmation" in out
    assert "Product story" in out
    assert "First complete path" in out
    assert "Host reasoning task" not in out
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
    dashboard_calls: list[dict[str, object]] = []
    _stub_dashboard_refresh(monkeypatch, dashboard_calls)
    monkeypatch.setattr(greenfield_apply_write.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(
        greenfield_proposals,
        "assert_greenfield_completion_ready",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("builder must not own final create readiness")),
    )
    apply_ready_flags: list[bool] = []
    original_apply = greenfield_proposals.apply_greenfield_proposal

    def wrapped_apply(**kwargs):
        apply_ready_flags.append(bool(kwargs.get("proposal_ready")))
        return original_apply(**kwargs)

    monkeypatch.setattr(greenfield_proposals, "apply_greenfield_proposal", wrapped_apply)

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
    assert apply_ready_flags == [True]
    assert dashboard_calls
    assert dashboard_calls[-1]["surfaces"] == ("radar", "registry", "atlas", "compass", "tooling_shell")
    assert dashboard_calls[-1]["operation_label"] == "Greenfield apply dashboard visibility"
    assert "atlas_sync" not in dashboard_calls[-1]
    assert "greenfield create wrote confirmed proposal" in out
    assert "- validation gate: passed" in out
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert (tmp_path / "odylith/runtime/source/accepted-project.v1.json").is_file()
    accepted = (tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8")
    assert "Permit File Registry" in accepted
    assert "Municipal Permit Review Workspace Workflow Service" not in accepted
    assert (tmp_path / "odylith/registry/source/component_registry.v1.json").is_file()
    mmd_files = list((tmp_path / "odylith/atlas/source").glob("*.mmd"))
    svg_files = list((tmp_path / "odylith/atlas/source").glob("*.svg"))
    png_files = list((tmp_path / "odylith/atlas/source").glob("*.png"))
    assert mmd_files
    assert len(svg_files) == len(mmd_files)
    assert len(png_files) == len(mmd_files)
    spec_root = tmp_path / "odylith/registry/source/components"
    specs = {path.parent.name: path.read_text(encoding="utf-8") for path in spec_root.glob("*/CURRENT_SPEC.md")}
    permit_spec = specs["permit-file-registry"]
    zoning_spec = specs["zoning-check-ledger"]
    revision_spec = next(text for slug, text in specs.items() if slug.endswith("revision-tracker"))
    decision_spec = specs["decision-package-review"]
    permit_spec_lower = permit_spec.casefold()
    assert "permit identity attachment" in permit_spec_lower
    assert "document completeness" in permit_spec_lower
    assert "missing document blockers" in permit_spec_lower
    assert "zoning check ledger" in permit_spec_lower
    assert "handoff" in permit_spec_lower
    assert "zoning checks, reviewer comments, rule references, and pass or block outcomes" in zoning_spec
    assert "applicant revisions to the documents and checks they are meant to address" in revision_spec
    assert "evidence, reviewer notes, unresolved blockers, and final approval state" in decision_spec
    assert len({permit_spec, zoning_spec, revision_spec, decision_spec}) == 4
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
        assert "## Component Brief" not in text
        assert "## Boundary Narrative" not in text
        assert "## First Release Proof" not in text
        assert "Suggested fixture:" not in text
        assert "Failure Modes" not in text
        assert "Domain risk:" not in text
        assert "Security and policy posture:" not in text
        assert "**" not in text
        assert "…" not in text
    catalog = json.loads((tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json").read_text(encoding="utf-8"))
    for diagram in catalog["diagrams"]:
        assert diagram["change_watch_paths"]
        assert "odylith/atlas/source" not in diagram["change_watch_paths"]
        assert diagram["source_svg"]
        assert (tmp_path / diagram["source_svg"]).is_file()
        assert diagram["source_png"].endswith(".png")
        assert (tmp_path / diagram["source_png"]).is_file()
        assert diagram["reviewed_watch_fingerprints"]
        assert diagram["render_source_fingerprint"]


def test_greenfield_create_cli_completes_privacy_export_lifecycle_end_to_end(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith/runtime/greenfield/confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(
        """# Privacy Request Lifecycle Console

Product story
A privacy operations team needs one console to receive data-subject requests, verify requester authority, collect protected-record references, decide whether export or deletion is allowed, and preserve lifecycle evidence without hiding retention blockers.

State object
A privacy request lifecycle record tracks requester identity, authority proof, protected-record reference, request type, consent state, retention rule, export package state, deletion decision, blocked reason, audit event, and handoff status.

First complete path
A privacy coordinator opens one request, verifies requester authority, links the protected record, selects export or deletion, checks consent and retention rules, produces the allowed package or blocked decision, and reviews the audit event with lifecycle status.

Human actors
- Privacy coordinator: verifies requester authority, links records, and reviews lifecycle status.
- Data owner: receives export package or deletion outcome.
- Compliance reviewer: checks retention rules, blocked decisions, and audit evidence.

External systems
- Identity provider for requester authority.
- Protected record store for referenced data.
- Retention policy catalog for retention rules.

Internal product systems
- Request Intake and Authority Check - records requester identity, request type, authority proof, and missing-authority blockers.
- Protected Record Reference Store - links protected records, consent state, classification, and access scope before lifecycle action.
- Export and Deletion Decision Service - applies consent and retention rules, produces export package state or blocked deletion decision, and hands evidence to audit.
- Lifecycle Audit and Review View - records audit events, lifecycle status, blocked reasons, reviewer notes, and replay evidence.

Critical assumptions
- Release 0.0.1 uses fixture records and policy rules before live data mutation.
- The product must not delete protected data without explicit allowed-state proof.

Ambiguities
- Whether export package delivery is manual download or provider-backed delivery.
- Which retention rule catalog is authoritative in the first release.

Proof boundary
Release 0.0.1 succeeds when one authorized request can link a protected record, produce an export package or blocked deletion decision, preserve consent and retention evidence, and show an audit event that explains who requested the action, which protected state was affected, which rule applied, and what lifecycle marker was emitted.
""",
        encoding="utf-8",
    )
    _stub_dashboard_refresh(monkeypatch)
    monkeypatch.setattr(greenfield_apply_write.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a product-first greenfield proposal for a privacy request lifecycle console.",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--release",
            "0.0.1",
            "--confirm",
        ]
    )

    output = capsys.readouterr().out
    assert rc == 0, output
    assert "greenfield create wrote confirmed proposal" in output
    assert "- validation gate: passed" in output
    assert (tmp_path / ".odylith/runtime/greenfield/confirmed-intent.json").is_file()
    assert (tmp_path / "odylith/runtime/source/accepted-project.v1.json").is_file()
    assert (tmp_path / "odylith/registry/source/component_registry.v1.json").is_file()
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert list((tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md"))
    assert list((tmp_path / "odylith/atlas/source").glob("*.mmd"))
    accepted = (tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8")
    joined_specs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md")
    )
    joined_diagrams = "\n".join(path.read_text(encoding="utf-8") for path in (tmp_path / "odylith/atlas/source").glob("*.mmd"))
    rendered = "\n".join([accepted, joined_specs, joined_diagrams]).casefold()
    for expected in (
        "requester authority",
        "protected record",
        "consent",
        "retention",
        "export package",
        "blocked deletion",
        "audit event",
    ):
        assert expected in rendered
    for banned in (
        "owns maintains",
        "first path entry",
        "proof-token",
        "checklist progress",
        "workspace status",
        "case identity",
        "working title",
    ):
        assert banned not in rendered


def test_greenfield_create_cli_repairs_generic_confirmed_first_path_actor(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith/runtime/greenfield/confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(
        """# Cooking Robot Controller

Product story
A control system turns a recipe into safe repeatable physical cooking. A home cook selects a dish and the controller sequences motions, dosing, heat, and safety stops.

State object
A cook session: active recipe, current step, sensor readings, actuator state, and safety status.

First complete path
Operator picks a recipe, the controller validates the robot is ready, runs the step sequence, surfaces progress, and reaches a finished safe state.

Human actors
- Home cook / operator who selects dishes and responds to prompts
- Kitchen technician who calibrates, maintains, and clears faults
- Recipe author who defines the step-by-step cooking program

External systems
- Robot hardware: arm actuators, ingredient dispensers, and heat element
- Sensors: temperature probes, scales, and presence sensing
- Emergency-stop hardware interlock

Internal product systems
- Recipe / step sequencer that interprets cooking programs
- Real-time control loop for heat, timing, and motion
- Safety supervisor that can override the sequencer
- Session and telemetry state tracking the live cook

Critical assumptions
- A single robot cell per controller instance for the first version
- Recipes are pre-authored structured programs

Ambiguities
- Software simulation/controller only, or driving real hardware from day one?
- Target host: embedded device, edge box, or general server?

Proof boundary
First version proves load a recipe, run its steps with closed-loop control, hit a safe finished state, and honor an emergency stop.
""",
        encoding="utf-8",
    )
    _stub_dashboard_refresh(monkeypatch)
    monkeypatch.setattr(greenfield_apply_write.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a cooking robot controller",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--release",
            "0.0.1",
            "--confirm",
        ]
    )

    output = capsys.readouterr().out
    assert rc == 0, output
    assert "greenfield create wrote confirmed proposal" in output
    assert "- validation gate: passed" in output
    assert "generic actor label `Operator`" not in output
    accepted = json.loads((tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8"))
    project_brief = accepted["proposal"]["project_brief"]
    first_path = project_brief["blueprint_sections"][1]["must_capture"]
    joined_specs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md")
    )
    joined_diagrams = "\n".join(path.read_text(encoding="utf-8") for path in (tmp_path / "odylith/atlas/source").glob("*.mmd"))
    rendered = "\n".join([json.dumps(accepted, sort_keys=True), joined_specs, joined_diagrams])

    assert first_path.startswith("Home cook picks a recipe")
    assert "reaches a finished safe state" in first_path
    assert "home cook" in rendered.casefold()
    assert "robot is ready" in rendered.casefold()
    assert "safe finished state" in rendered.casefold() or "finished safe state" in rendered.casefold()
    assert "Operator picks a recipe" not in rendered
    assert "Home Cook / Operator" not in rendered
    assert "A finished safe state" not in first_path
    assert not re.search(r"\bOperator\b", first_path)
    assert "generic actor label" not in rendered
    assert "Preserve this accepted first path:" in output
    assert "safe finished state" in output


def test_greenfield_create_cli_bootstraps_missing_indexes_and_repairs_scaffold_language(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    intent_path = tmp_path / ".odylith/runtime/greenfield/confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(
        """# Field Operations Evidence Console

Product story
A field operations team needs one console to receive site observations, review source evidence, decide whether an inspection is ready for action, and keep blocked cases visible until the missing evidence is resolved.

State object
An operations evidence record tracks site identity, observation source, captured readings, supporting files, readiness status, blocker reason, reviewer decision, and handoff evidence.

First complete path
An operator opens one site record, adds a source-backed observation, attaches supporting evidence, marks missing readings as blockers when needed, reviews readiness, and hands the reviewed decision to the next action queue.

Human actors
- Field operator: records observations and attaches evidence.
- Operations reviewer: checks readiness, blockers, and handoff evidence.
- Program lead: reviews the final decision queue.

External systems
- Site source register for site identity.
- Sensor export file for fixture readings.
- Evidence file store for attached supporting files.

Internal product systems
- Site Record Intake - owns site identity, source reference, required observation fields, and missing-source blockers.
- Observation Evidence Ledger - records readings, supporting files, source references, invalid-input blockers, and evidence handoff.
- Readiness Review Queue - shows readiness status, blocker reason, reviewer decision, and next-action handoff.

Critical assumptions
- Release 0.0.1 uses fixture sensor exports before live device ingestion.
- Reviewers must see missing evidence instead of silently treating a record as ready.

Ambiguities
- Which source register is authoritative for the first release.
- Whether the first action queue is internal only or exported.

Proof boundary
Release 0.0.1 succeeds when one site record can be opened, linked to source evidence, reviewed for missing readings, marked ready or blocked with a reason, and handed to the next action queue with the evidence and reviewer decision still traceable.
""",
        encoding="utf-8",
    )
    _stub_dashboard_refresh(monkeypatch)
    monkeypatch.setattr(greenfield_apply_write.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Build a field operations evidence console",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--release",
            "0.0.1",
            "--confirm",
        ]
    )

    output = capsys.readouterr().out
    assert rc == 0, output
    assert "greenfield create wrote confirmed proposal" in output
    assert (tmp_path / "odylith/technical-plans/INDEX.md").is_file()
    assert (tmp_path / "odylith/radar/source/INDEX.md").is_file()
    accepted = (tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8")
    joined_specs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md")
    )
    joined_diagrams = "\n".join(path.read_text(encoding="utf-8") for path in (tmp_path / "odylith/atlas/source").glob("*.mmd"))
    rendered = "\n".join([accepted, joined_specs, joined_diagrams]).casefold()
    for expected in (
        "site identity",
        "source reference",
        "captured readings",
        "supporting files",
        "readiness status",
        "blocker reason",
    ):
        assert expected in rendered
    for banned in (
        "owns maintains",
        "first path entry",
        "proof-token",
        "case identity",
        "workspace status",
        "checklist progress",
        "working title",
        "no claim that",
        "sibling responsibilities",
        "accepted state object",
    ):
        assert banned not in rendered
    assert not re.search(r"\battache\b", rendered)


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
        _write_stubbed_atlas_render_outputs(Path(str(_kwargs["repo_root"])))

    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", noisy_refresh)
    monkeypatch.setattr(greenfield_apply_write.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
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
