from __future__ import annotations

import json
import os
import re
from dataclasses import replace
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_hash
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_to_dict
from odylith.runtime.domain_intelligence.greenfield_create_manifest import PRECONFIRM_ENGINE_VERSION
from odylith.runtime.domain_intelligence.greenfield_create_manifest import PRECONFIRM_QUALITY_MANIFEST_VERSION
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import write_structured_confirmed_intent_file
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import build_product_intent_envelope
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import product_intent_authority_from_envelope
from odylith.runtime.domain_intelligence.greenfield_text import normalize_domain_token
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_create_baseline
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_surface_refresh_proof
from odylith.runtime.surfaces import brand_assets
from tests.unit.runtime.greenfield_proposal_fixtures import CONFIRMED_INTENT_TEXT
from tests.unit.runtime.greenfield_proposal_fixtures import _host_reasoned_ecommerce_proposal
from tests.unit.runtime.greenfield_proposal_fixtures import _markdown_section
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import _write_confirmed_intent
from tests.unit.runtime.greenfield_proposal_fixtures import compiled_greenfield_package_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import surface_refresh_preview_fixture


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


def _approved_quality_manifest() -> dict[str, object]:
    return {
        "version": PRECONFIRM_QUALITY_MANIFEST_VERSION,
        "engine": PRECONFIRM_ENGINE_VERSION,
        "status": "passed",
        "validation_status": "passed",
        "issue_count": 0,
        "hard_blocker": None,
        "write_transaction": {
            "status": "not_started",
            "rollback_guard": "enabled",
            "prewrite_clean_before_commit": True,
        },
    }


def _confirmed_intent_with_authority(repo_root: Path) -> dict[str, object]:
    markdown_path = repo_root / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    structured_path = markdown_path.with_suffix(".json")
    intent = parse_confirmed_intent_text(
        CONFIRMED_INTENT_TEXT,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
    )
    envelope = build_product_intent_envelope(
        intent,
        source_text=CONFIRMED_INTENT_TEXT,
        source_path=markdown_path,
        source_format="markdown",
    )
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(CONFIRMED_INTENT_TEXT, encoding="utf-8")
    write_structured_confirmed_intent_file(markdown_path, intent, envelope=envelope)
    intent[PRODUCT_INTENT_AUTHORITY_KEY] = product_intent_authority_from_envelope(
        envelope,
        structured_intent_path=structured_path,
        markdown_source_path=markdown_path,
    )
    return intent


def _stub_dashboard_refresh(monkeypatch, calls: list[dict[str, object]] | None = None) -> None:
    def refresh(**kwargs: object) -> None:
        if calls is not None:
            calls.append(dict(kwargs))
        _write_stubbed_atlas_render_outputs(Path(str(kwargs["repo_root"])))

    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", refresh)
    def preview(**kwargs: object) -> dict[str, object]:
        _write_stubbed_atlas_render_outputs(Path(str(kwargs["repo_root"])))
        if calls is not None:
            calls.append(
                {
                    "repo_root": kwargs["repo_root"],
                    "surfaces": greenfield_surface_refresh_proof.GREENFIELD_VISIBLE_SURFACES,
                    "operation_label": "Greenfield pre-confirm staged surface refresh",
                }
            )
        return surface_refresh_preview_fixture()

    monkeypatch.setattr(
        greenfield_surface_refresh_proof,
        "build_prewrite_surface_refresh_preview",
        preview,
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {
            "status": "passed",
            "atlas_surface_count": 3,
            "atlas_diagram_count": 0,
        },
    )


def _run_confirmed_transaction_create(
    *,
    repo_root: Path,
    prompt: str,
    capsys,
    release: str = "0.0.1",
    edit_evidence_file: str = "",
    as_json: bool = False,
) -> tuple[int, str, dict[str, object]]:
    transaction_file = ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    propose_args = ["propose", "--repo-root", str(repo_root), "--prompt", prompt]
    if edit_evidence_file:
        propose_args.extend(("--edit-evidence", edit_evidence_file))
    propose_args.extend(("--format", "json"))
    compile_rc = greenfield_proposals.main(propose_args)
    compile_output = capsys.readouterr().out
    assert compile_rc == 0, compile_output
    compile_payload = json.loads(compile_output)
    transaction_hash = str(compile_payload["product_create_transaction"]["transaction_hash"])
    create_args = [
        "create",
        "--repo-root",
        str(repo_root),
        "--transaction-file",
        transaction_file,
        "--transaction-hash",
        transaction_hash,
        "--confirm",
    ]
    if as_json:
        create_args.append("--json")
    create_rc = greenfield_proposals.main(create_args)
    create_output = capsys.readouterr().out
    return create_rc, create_output, compile_payload


def test_greenfield_domain_token_normalizer_keeps_common_words_legible() -> None:
    assert normalize_domain_token("attaches") == "attach"
    assert normalize_domain_token("matches") == "match"
    assert normalize_domain_token("processes") == "process"
    assert normalize_domain_token("statuses") == "status"
    assert normalize_domain_token("readings") == "reading"


def test_greenfield_text_compiles_concrete_prompt_into_transaction_with_assumptions(tmp_path, capsys) -> None:
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            (
                "Design a mathematics research workspace where researchers record a spectral graph question, "
                "run one analysis, review the derivation, and save a reproducible result."
            ),
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert "ProductCreateTransaction ready for final command" in output
    assert "transaction hash:" in output
    assert "### Command: `CONFIRM`" in output
    assert "Commit this exact validated package now" in output


def test_greenfield_edit_rebuilds_the_staged_transaction_without_governed_writes(tmp_path, capsys) -> None:
    prompt = (
        "Create a flood shelter intake system that helps city staff register displaced residents, match household needs "
        "to shelter capacity, track accessibility constraints, preserve consent evidence, and produce a daily placement "
        "readiness report."
    )
    initial_rc = greenfield_proposals.main(
        ["propose", "--repo-root", str(tmp_path), "--prompt", prompt, "--format", "json"]
    )
    initial = json.loads(capsys.readouterr().out)

    edited_rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--edit",
            (
                "EDIT\n\nFirst complete path: A shelter coordinator registers a displaced household, records "
                "accessibility needs, matches an available bed, obtains consent, and sees a confirmed placement receipt."
            ),
            "--format",
            "json",
        ]
    )
    edited = json.loads(capsys.readouterr().out)

    assert initial_rc == edited_rc == 0
    assert initial["product_create_transaction"]["transaction_hash"] != edited["product_create_transaction"]["transaction_hash"]
    assert initial["product_create_transaction"]["product_facts_sha256"] != edited["product_create_transaction"]["product_facts_sha256"]
    assert "shelter coordinator" in edited["intent_hypothesis"]["first_path"].casefold()
    assert not (tmp_path / "odylith/radar/source").exists()
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_sentence_form_edit_rebuilds_without_schema_shaped_input(tmp_path, capsys) -> None:
    prompt = (
        "Create a flood shelter intake system that helps city staff register displaced residents, match household needs "
        "to shelter capacity, preserve consent evidence, and publish a daily placement readiness result."
    )

    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--edit",
            "EDIT\nThe first path should be completed by shelter coordinators rather than city staff.",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["product_create_transaction"]["quality_status"] == "passed"
    assert payload["intent_hypothesis"]["first_path"].startswith("Shelter coordinators can")
    assert payload["intent_hypothesis"]["product_intent_authority"]["source_format"] == (
        "operator_prompt_with_edit_evidence"
    )
    assert not (tmp_path / "odylith/radar/source").exists()


def test_greenfield_short_actor_edit_rebuilds_without_schema_shaped_input(tmp_path, capsys) -> None:
    prompt = (
        "Create a flood shelter intake system that helps city staff register displaced residents, match household needs "
        "to shelter capacity, preserve consent evidence, and publish a daily placement readiness result."
    )

    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--edit",
            "EDIT\nIt is for shelter coordinators rather than city staff.",
            "--format",
            "json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["intent_hypothesis"]["first_path"].startswith("Shelter coordinators can")
    assert "city staff" not in " ".join(payload["intent_hypothesis"]["human_actors"]).casefold()


def test_greenfield_visible_result_edit_rebuilds_without_schema_shaped_input(tmp_path, capsys) -> None:
    prompt = (
        "Create a flood shelter intake system that helps city staff register displaced residents, match household needs "
        "to shelter capacity, preserve consent evidence, and publish a daily placement readiness result."
    )

    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--edit",
            "EDIT\nActually the visible result should be a confirmed placement receipt for the household.",
            "--format",
            "json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert "confirmed placement receipt for the household" in payload["intent_hypothesis"]["first_path"].casefold()
    assert payload["product_create_transaction"]["quality_status"] == "passed"


def test_greenfield_propose_stdout_can_be_confirmed_and_created(tmp_path, monkeypatch, capsys) -> None:
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
    assert "ProductCreateTransaction ready for final command" in confirmation
    assert confirmation.count("## Choose one command") == 1
    _stub_dashboard_refresh(monkeypatch)
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    rc, output, compile_payload = _run_confirmed_transaction_create(
        repo_root=tmp_path,
        prompt=prompt,
        capsys=capsys,
        release="0.0.1",
        as_json=True,
    )

    assert rc == 0, output
    assert compile_payload["mode"] == "product_create_transaction"
    assert compile_payload["product_create_transaction"]["transaction_hash"]
    assert "No governed records were written" not in output
    assert "post-confirm completion failed" not in output
    assert (tmp_path / "odylith/radar/source").is_dir()
    assert (tmp_path / "odylith/registry/source/components").is_dir()
    assert (tmp_path / "odylith/atlas/source").is_dir()
    assert (tmp_path / ".odylith/runtime/greenfield/candidate-intent.json").is_file()


def test_greenfield_propose_shows_single_transaction_handoff(tmp_path, capsys) -> None:
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            (
                "Create a municipal permit review workspace where permit clerks intake applications, validate zoning "
                "attachments, route reviewer decisions, and show applicants a clear approval packet with blockers and proof."
            ),
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert "ProductCreateTransaction ready for final command" in output
    assert "transaction hash:" in output
    assert "transaction file:" in output
    assert "## Choose one command" in output
    assert "**Start your reply with exactly one command:** `CONFIRM`, `EDIT`, or `REJECT`." in output
    assert "Only the first command counts. Do not paste Odylith system commands in your reply." in output
    assert "### Command: `CONFIRM`" in output
    assert "**Reply starts with:** `CONFIRM`" in output
    assert "Commit this exact validated package now" in output
    assert "### Command: `EDIT`" in output
    assert "**Reply starts with:** `EDIT`" in output
    assert "Put corrections after EDIT" in output
    assert "### Command: `REJECT`" in output
    assert "**Reply starts with:** `REJECT`" in output
    assert "Stop. No governed records are written." in output
    choose_index = output.index("## Choose one command")
    confirm_index = output.index("### Command: `CONFIRM`", choose_index)
    edit_index = output.index("### Command: `EDIT`", confirm_index)
    reject_index = output.index("### Command: `REJECT`", edit_index)
    transaction_index = output.index("transaction hash:")
    assert transaction_index < choose_index < confirm_index < edit_index < reject_index
    assert output.count("## Choose one command") == 1
    assert "greenfield create --repo-root ." in output
    assert "--transaction-hash" in output
    assert "No product reinterpretation, repair, or generation runs after CONFIRM." in output
    assert "internal apply payload" not in output
    assert "active-proposal.v1.json" not in output
    assert "host_instruction" not in output
    assert "reasoning_contract" not in output


def test_greenfield_propose_cli_asks_one_product_question_for_a_bare_title(tmp_path, capsys) -> None:
    transaction_path = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"

    rc = greenfield_proposals.main(
        ["propose", "--repo-root", str(tmp_path), "--prompt", "Create assay review."]
    )

    output = capsys.readouterr().out
    assert rc == 0
    assert "Odylith needs one product decision." in output
    assert "what should the first person complete and what result should they see" in output.casefold()
    assert "No transaction or governed records were created." in output
    assert "ProductCreateTransaction ready for final command" not in output
    assert not transaction_path.exists()


def test_greenfield_propose_cli_asks_one_product_question_for_a_title_like_path(tmp_path, capsys) -> None:
    transaction_path = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"

    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Create a booking workspace for repairs and scheduling.",
        ]
    )

    output = capsys.readouterr().out
    assert rc == 0
    assert "Odylith needs one product decision." in output
    assert "what should the first person complete and what result should they see" in output.casefold()
    assert "No transaction or governed records were created." in output
    assert "ProductCreateTransaction ready for final command" not in output
    assert not transaction_path.exists()


def test_greenfield_propose_cli_returns_typed_clarification_without_staging(tmp_path, capsys) -> None:
    transaction_path = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"

    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            (
                "A regional cell-therapy network needs a product for autologous CAR-T operations across collection "
                "clinics, apheresis couriers, manufacturing suites, and infusion centers. It must preserve chain of "
                "identity from leukapheresis bag through cryoshipper receipt, CD3+ enrichment, vector transduction, "
                "release assay, and patient infusion."
            ),
            "--format",
            "json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload == {
        "mode": "clarification_required",
        "clarification": {
            "question": (
                "For Regional Cell-therapy Network Needs A Product For Autologous CAR-T Operations Across Collection "
                "Clinics, Apheresis Couriers, Manufacturing, what should the first person complete and what result "
                "should they see? One plain-language sentence is enough."
            ),
            "required_fields": ["first_path"],
        },
    }
    assert not transaction_path.exists()
    assert not (tmp_path / "odylith/radar/source").exists()


def test_greenfield_clarification_removes_a_stale_default_transaction(tmp_path, capsys) -> None:
    transaction_path = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    transaction_path.parent.mkdir(parents=True)
    transaction_path.write_text('{"stale": true}\n', encoding="utf-8")

    rc = greenfield_proposals.main(
        ["propose", "--repo-root", str(tmp_path), "--prompt", "Create assay review.", "--format", "json"]
    )

    assert rc == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "clarification_required"
    assert not transaction_path.exists()


def test_greenfield_compile_clarification_removes_stale_requested_output(tmp_path, capsys) -> None:
    default_transaction = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    requested_output = tmp_path / "transactions/compiled.json"
    for path in (default_transaction, requested_output):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"stale": true}\n', encoding="utf-8")

    rc = greenfield_proposals.main(
        [
            "compile-transaction",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Create assay review.",
            "--output",
            str(requested_output),
            "--format",
            "json",
        ]
    )

    assert rc == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "clarification_required"
    assert not default_transaction.exists()
    assert not requested_output.exists()


def test_greenfield_confirm_intent_flag_is_retired(tmp_path, capsys) -> None:
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
    assert "separate Product Intent confirmation flow is retired" in output
    assert "--edit-evidence" in output


def test_greenfield_propose_compiles_prompt_evidence_without_intent_file(tmp_path, capsys) -> None:
    prompt = (
        "Create a greenfield product for municipal permit clerks to intake permit applications, "
        "validate zoning attachments, route reviewer decisions, and show applicants a clear approval packet "
        "without issuing permits or promising legal approval."
    )

    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            prompt,
            "--format",
            "json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "product_create_transaction"
    assert payload["product_create_transaction"]["transaction_hash"]
    assert (tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json").is_file()
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_text_full_detail_keeps_single_commit_path_available(tmp_path, capsys) -> None:
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            (
                "Create a municipal permit review workspace where permit clerks intake applications, validate zoning "
                "attachments, route reviewer decisions, and show applicants a clear approval packet with blockers and proof."
            ),
            "--detail",
            "full",
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert "Product Intent Preview" in output
    assert "Product story" in output
    assert "ProductCreateTransaction" in output
    assert "## Choose one command" in output
    assert "**Start your reply with exactly one command:** `CONFIRM`, `EDIT`, or `REJECT`." in output
    assert "Only the first command counts. Do not paste Odylith system commands in your reply." in output
    assert "### Command: `CONFIRM`" in output
    assert "**Reply starts with:** `CONFIRM`" in output
    assert "Commit this exact validated package now" in output
    assert "### Command: `EDIT`" in output
    assert "**Reply starts with:** `EDIT`" in output
    assert "Put corrections after EDIT" in output
    assert "### Command: `REJECT`" in output
    assert "**Reply starts with:** `REJECT`" in output
    assert "Stop. No governed records are written." in output
    choose_index = output.index("## Choose one command")
    confirm_index = output.index("### Command: `CONFIRM`", choose_index)
    edit_index = output.index("### Command: `EDIT`", confirm_index)
    reject_index = output.index("### Command: `REJECT`", edit_index)
    transaction_index = output.index("transaction hash:")
    assert transaction_index < choose_index < confirm_index < edit_index < reject_index
    assert output.count("## Choose one command") == 1
    assert "odylith greenfield create --repo-root ." in output
    assert "--transaction-hash" in output
    assert "internal apply payload" not in output
    assert ".odylith/runtime/greenfield/active-proposal.v1.json" not in output
    assert len(output.splitlines()) <= 275


def test_greenfield_title_preserves_meaningful_trailing_domain_terms(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="field inspection evidence workspace for municipal building permits",
        confirmed_intent=_confirmed_intent_with_authority(tmp_path),
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
            (
                "Build a statistics notebook workspace where analysts upload a dataset, run one reproducible analysis, "
                "review the output, and save a notebook result with its source data and method."
            ),
            "--format",
            "json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "product_create_transaction"
    assert payload["product_create_transaction"]["transaction_hash"]
    assert payload["product_create_transaction"]["quality_status"] == "passed"
    assert Path(payload["transaction_file"]).is_file()
    assert payload["intent_hypothesis"]["product_story"]
    assert "host_reasoning_task" not in payload
    assert "backlog" not in payload
    assert "components" not in payload
    assert "diagrams" not in payload


def test_greenfield_cli_json_is_transaction_audit_from_typed_prompt_evidence(tmp_path, capsys) -> None:
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            (
                "Create a municipal permit review workspace where permit clerks intake applications, validate zoning "
                "attachments, route reviewer decisions, and show applicants a clear approval packet with blockers and proof."
            ),
            "--format",
            "json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "product_create_transaction"
    assert payload["product_create_transaction"]["transaction_hash"]
    assert payload["product_create_transaction"]["quality_status"] == "passed"
    encoded = json.dumps(payload)
    assert "host_instruction" not in payload
    assert "canonical_proposal" not in payload
    assert "proposal_template" not in payload
    assert "backlog" not in payload
    assert "components" not in payload
    assert "diagrams" not in payload


def test_greenfield_apply_cli_rejects_legacy_confirm_path_before_compile(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("legacy apply must fail before proposal load, compile, or commit")

    monkeypatch.setattr(greenfield_proposals, "load_proposal", forbidden)
    monkeypatch.setattr(greenfield_proposals, "apply_greenfield_proposal", forbidden)

    rc = greenfield_proposals.main(
        [
            "apply",
            "--repo-root",
            str(tmp_path),
            "--proposal-json",
            "{not-json",
            "--confirm",
            "--release",
            "0.0.1",
        ]
    )

    out = capsys.readouterr().out
    assert rc == 2
    assert "greenfield apply is disabled for confirmed writes" in out
    assert "Confirm now commits only an already compiled ProductCreateTransaction" in out
    assert "greenfield propose" in out
    assert "greenfield create" in out
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_prompt_paths_do_not_expose_legacy_apply_ready_scaffold(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a plant-care irrigation device that waters and monitors houseplants.",
        ]
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert "Product Intent Preview" in out
    assert "Product story" in out
    assert "First complete path" in out
    assert "ProductCreateTransaction ready for final command" in out
    assert out.count("## Choose one command") == 1
    assert "Host reasoning task" not in out
    assert "raw greenfield intent" not in out

    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a plant-care irrigation device that waters and monitors houseplants.",
            "--confirm-intent",
        ]
    )
    out = capsys.readouterr().out

    assert rc == 2
    assert "separate Product Intent confirmation flow is retired" in out
    assert "--edit-evidence" in out
    assert "internal apply payload" not in out
    assert "active-proposal.v1.json" not in out
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []


def test_greenfield_create_cli_applies_confirmed_prompt(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    _write_confirmed_intent(tmp_path)
    dashboard_calls: list[dict[str, object]] = []
    _stub_dashboard_refresh(monkeypatch, dashboard_calls)
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(
        greenfield_proposals,
        "assert_greenfield_completion_ready",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("builder must not own final create readiness")),
    )

    rc, out, compile_payload = _run_confirmed_transaction_create(
        repo_root=tmp_path,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
        capsys=capsys,
        release="0.0.1",
        edit_evidence_file=".odylith/runtime/greenfield/confirmed-intent.md",
    )

    assert rc == 0
    assert compile_payload["product_create_transaction"]["verified"] is True
    assert dashboard_calls
    assert dashboard_calls[-1]["surfaces"] == ("radar", "registry", "atlas", "compass", "tooling_shell")
    assert dashboard_calls[-1]["operation_label"] == "Greenfield pre-confirm staged surface refresh"
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


def _compiled_transaction_for_cli(tmp_path: Path):
    intent = _confirmed_intent_with_authority(tmp_path)
    authority = dict(intent[PRODUCT_INTENT_AUTHORITY_KEY])
    proposal = {
        "intent": {"title": "Municipal Permit Review Workspace"},
        PRODUCT_INTENT_AUTHORITY_KEY: authority,
        "backlog": [{"title": "Prove permit review path"}],
        "components": [],
        "diagrams": [],
    }
    package = compiled_greenfield_package_fixture(
        proposal=proposal,
        repo_root=tmp_path,
        baseline_writes=greenfield_create_baseline.precompiled_greenfield_create_baseline_writes(tmp_path),
        brand_asset_writes=brand_assets.precompiled_brand_asset_writes(repo_root=tmp_path),
    )
    transaction = build_product_create_transaction(
        proposal=proposal,
        release_selector="0.0.1",
        validation_gate={"status": "passed", "issues": []},
        prewrite_package=package,
        backlog_result=package.backlog_result or {},
        intent_authority=authority,
        quality_manifest=_approved_quality_manifest(),
        repo_root=tmp_path,
    )
    return proposal, transaction


def test_greenfield_create_cli_rejects_intent_file_without_compiled_transaction(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    _write_confirmed_intent(tmp_path)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("intent-file create must fail before build, compile, apply, or commit")

    monkeypatch.setattr(greenfield_proposals, "build_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_proposals, "compile_greenfield_create_transaction", forbidden)
    monkeypatch.setattr(greenfield_proposals, "apply_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_create_commit, "commit_greenfield_create_transaction", forbidden)

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
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert "greenfield create no longer accepts --intent-file" in payload["error"]
    assert "greenfield propose" in payload["error"]
    assert "--transaction-file, --transaction-hash, and --confirm" in payload["error"]


def test_greenfield_propose_cli_outputs_hash_ready_contract(
    tmp_path,
    capsys,
) -> None:
    transaction_path = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            (
                "Create a municipal permit review product where permit clerks intake applications, validate zoning "
                "attachments, route reviewer decisions, and show applicants a clear approval packet with blockers and proof."
            ),
        ]
    )

    output = capsys.readouterr().out
    assert rc == 0
    assert "ProductCreateTransaction ready for final command" in output
    assert "exact file writes" in output
    assert "hashed repo preconditions" in output
    assert "**Start your reply with exactly one command:** `CONFIRM`, `EDIT`, or `REJECT`." in output
    assert "Only the first command counts. Do not paste Odylith system commands in your reply." in output
    assert "### Command: `CONFIRM`" in output
    assert "**Reply starts with:** `CONFIRM`" in output
    assert "Commit this exact validated package now." in output
    assert "verifies the hash and repo preconditions, writes the sealed bytes, and validates readback" in output
    assert "### Command: `EDIT`" in output
    assert "**Reply starts with:** `EDIT`" in output
    assert "Do not commit. Put corrections after EDIT" in output
    assert "### Command: `REJECT`" in output
    assert "**Reply starts with:** `REJECT`" in output
    assert "Stop. No governed records are written" in output
    choose_index = output.index("## Choose one command")
    confirm_index = output.index("### Command: `CONFIRM`", choose_index)
    edit_index = output.index("### Command: `EDIT`", confirm_index)
    reject_index = output.index("### Command: `REJECT`", edit_index)
    assert choose_index < confirm_index < edit_index < reject_index
    assert output.count("## Choose one command") == 1
    assert "Compile transaction:" not in output
    assert "compile a validated ProductCreateTransaction" not in output
    assert "compiles a validated ProductCreateTransaction" not in output
    assert "--transaction-file" in output
    assert "--transaction-hash" in output
    assert transaction_path.is_file()
    assert transaction_path.with_name(transaction_path.name + ".compiler-receipt.v1.json").is_file()
    saved = json.loads(transaction_path.read_text(encoding="utf-8"))
    assert saved["transaction_hash"] in output
    assert saved["prewrite_package"]["surface_refresh_preview"]
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []


def test_greenfield_create_cli_commits_transaction_file_without_recompiling(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    _write_confirmed_intent(tmp_path)
    _proposal, transaction = _compiled_transaction_for_cli(tmp_path)
    transaction_path = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    greenfield_proposals.write_product_create_transaction_file(transaction_path, transaction)
    calls: list[tuple[str, dict[str, object]]] = []

    def forbidden(*_args, **_kwargs):
        raise AssertionError("transaction-file create must not build, repair, or compile")

    def fake_commit(**kwargs):
        calls.append(("commit", dict(kwargs)))
        assert kwargs["transaction"].transaction_hash == transaction.transaction_hash
        assert (
            kwargs["transaction"].prewrite_package.surface_refresh_preview
            == transaction.prewrite_package.surface_refresh_preview
        )
        return {
            "mode": "applied",
            "validation_gate": transaction.validation_gate,
            "backlog": [],
            "components": [],
            "diagrams": [],
            "product_create_transaction": transaction.summary(),
            "commit_manifest": {
                "status": "passed",
                "validation_status": "passed",
                "write_transaction": {
                    "status": "committed",
                    "commit_only": True,
                    "product_create_transaction_hash": transaction.transaction_hash,
                },
            },
        }

    monkeypatch.setattr(greenfield_proposals, "build_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_proposals, "compile_greenfield_create_transaction", forbidden)
    monkeypatch.setattr(greenfield_proposals, "apply_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_proposals, "complete_confirmed_proposal", forbidden)
    monkeypatch.setattr(greenfield_proposals, "complete_greenfield_semantic_apply_payload", forbidden)
    monkeypatch.setattr(greenfield_proposals, "_build_repaired_prewrite_package", forbidden)
    monkeypatch.setattr(greenfield_proposals, "run_greenfield_preconfirm_engine", forbidden)
    monkeypatch.setattr(greenfield_proposals, "apply_greenfield_patchset_repairs", forbidden)
    monkeypatch.setattr(greenfield_create_commit, "commit_greenfield_create_transaction", fake_commit)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            ".odylith/runtime/greenfield/product-create-transaction.v1.json",
            "--transaction-hash",
            transaction.transaction_hash,
            "--confirm",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert [name for name, _call in calls] == ["commit"]
    assert payload["product_create_transaction"]["transaction_hash"] == transaction.transaction_hash
    assert payload["product_create_transaction"]["verified"] is True
    assert payload["commit_manifest"]["write_transaction"]["commit_only"] is True


def test_greenfield_create_cli_rejects_transaction_without_compiler_receipt(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    _proposal, transaction = _compiled_transaction_for_cli(tmp_path)
    transaction_path = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    transaction_path.parent.mkdir(parents=True, exist_ok=True)
    transaction_path.write_text(
        json.dumps(product_create_transaction_to_dict(transaction), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("a transaction without a compiler receipt must fail before commit")

    monkeypatch.setattr(greenfield_create_commit, "commit_greenfield_create_transaction", forbidden)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            ".odylith/runtime/greenfield/product-create-transaction.v1.json",
            "--transaction-hash",
            transaction.transaction_hash,
            "--confirm",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert "missing its pre-confirm compiler receipt" in payload["error"]


def test_greenfield_create_cli_rejects_rehashed_manifest_drift_before_commit(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    _proposal, transaction = _compiled_transaction_for_cli(tmp_path)
    transaction_path = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    greenfield_proposals.write_product_create_transaction_file(transaction_path, transaction)
    candidate = replace(
        transaction,
        quality_manifest={**dict(transaction.quality_manifest), "status": "failed"},
    )
    forged = replace(candidate, transaction_hash=product_create_transaction_hash(candidate))
    transaction_path.write_text(
        json.dumps(product_create_transaction_to_dict(forged), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("a receipt-drifted transaction must fail before the commit boundary")

    monkeypatch.setattr(greenfield_create_commit, "commit_greenfield_create_transaction", forbidden)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            ".odylith/runtime/greenfield/product-create-transaction.v1.json",
            "--transaction-hash",
            forged.transaction_hash,
            "--confirm",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert "file does not match its pre-confirm compiler receipt" in payload["error"]
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


@pytest.mark.parametrize(
    ("flag", "value"),
    (
        ("--prompt", "Draft a different product after confirmation"),
        ("--release", "0.0.2"),
        ("--repair-tier", "deep"),
    ),
)
def test_greenfield_create_cli_rejects_uncompiled_input_overrides(
    tmp_path,
    monkeypatch,
    capsys,
    flag,
    value,
) -> None:
    _proposal, transaction = _compiled_transaction_for_cli(tmp_path)
    transaction_path = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    greenfield_proposals.write_product_create_transaction_file(transaction_path, transaction)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("post-confirm create overrides must fail before compile or commit")

    monkeypatch.setattr(greenfield_proposals, "build_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_proposals, "compile_greenfield_create_transaction", forbidden)
    monkeypatch.setattr(greenfield_proposals, "apply_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_create_commit, "commit_greenfield_create_transaction", forbidden)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            ".odylith/runtime/greenfield/product-create-transaction.v1.json",
            "--transaction-hash",
            transaction.transaction_hash,
            flag,
            value,
            "--confirm",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert "greenfield create accepts only --transaction-file, --transaction-hash, and --confirm" in payload["error"]
    assert flag in payload["error"]
    assert "Use EDIT to add evidence and rebuild the ProductCreateTransaction" in payload["error"]


def test_greenfield_create_cli_rejects_intent_file_even_with_compiled_transaction(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    _write_confirmed_intent(tmp_path)
    _proposal, transaction = _compiled_transaction_for_cli(tmp_path)
    transaction_path = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    transaction_path.parent.mkdir(parents=True, exist_ok=True)
    transaction_path.write_text(
        json.dumps(product_create_transaction_to_dict(transaction), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("intent-file create must fail before loading, compiling, or committing")

    monkeypatch.setattr(greenfield_proposals, "load_product_create_transaction_args", forbidden)
    monkeypatch.setattr(greenfield_proposals, "build_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_proposals, "compile_greenfield_create_transaction", forbidden)
    monkeypatch.setattr(greenfield_proposals, "apply_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_create_commit, "commit_greenfield_create_transaction", forbidden)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            ".odylith/runtime/greenfield/product-create-transaction.v1.json",
            "--transaction-hash",
            transaction.transaction_hash,
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--confirm",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert "greenfield create no longer accepts --intent-file" in payload["error"]
    assert "greenfield propose" in payload["error"]


def test_greenfield_create_cli_requires_visible_transaction_hash(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    _proposal, transaction = _compiled_transaction_for_cli(tmp_path)
    transaction_path = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    greenfield_proposals.write_product_create_transaction_file(transaction_path, transaction)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("transaction create without --transaction-hash must fail before commit")

    monkeypatch.setattr(greenfield_proposals, "build_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_proposals, "compile_greenfield_create_transaction", forbidden)
    monkeypatch.setattr(greenfield_proposals, "apply_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_create_commit, "commit_greenfield_create_transaction", forbidden)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            ".odylith/runtime/greenfield/product-create-transaction.v1.json",
            "--confirm",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert "requires --transaction-hash" in payload["error"]
    assert "Product Intent Confirmation" not in payload["error"]
    assert "post-confirm completion" not in payload["error"]
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_create_cli_rejects_transaction_file_without_compiler_provenance(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    _proposal, transaction = _compiled_transaction_for_cli(tmp_path)
    candidate = replace(transaction, compiler_provenance={})
    forged = replace(candidate, transaction_hash=product_create_transaction_hash(candidate))
    transaction_path = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    greenfield_proposals.write_product_create_transaction_file(transaction_path, forged)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("unapproved transaction provenance must fail before governed writes")

    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "write_greenfield_proposal", forbidden)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            ".odylith/runtime/greenfield/product-create-transaction.v1.json",
            "--transaction-hash",
            forged.transaction_hash,
            "--confirm",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert "invalidated by a runtime or repository-context change" in payload["error"]
    assert "no Product Intent was rejected" in payload["error"]
    assert "no governed records were written" in payload["error"]
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


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
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    rc, output, _compile_payload = _run_confirmed_transaction_create(
        repo_root=tmp_path,
        prompt="Draft a product-first greenfield proposal for a privacy request lifecycle console.",
        capsys=capsys,
        release="0.0.1",
        edit_evidence_file=".odylith/runtime/greenfield/confirmed-intent.md",
    )

    assert rc == 0, output
    assert "greenfield create wrote confirmed proposal" in output
    assert "- validation gate: passed" in output
    assert (tmp_path / ".odylith/runtime/greenfield/candidate-intent.json").is_file()
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
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    rc, output, _compile_payload = _run_confirmed_transaction_create(
        repo_root=tmp_path,
        prompt="Draft a greenfield proposal for a cooking robot controller",
        capsys=capsys,
        release="0.0.1",
        edit_evidence_file=".odylith/runtime/greenfield/confirmed-intent.md",
    )

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
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    rc, output, _compile_payload = _run_confirmed_transaction_create(
        repo_root=tmp_path,
        prompt="Build a field operations evidence console",
        capsys=capsys,
        release="0.0.1",
        edit_evidence_file=".odylith/runtime/greenfield/confirmed-intent.md",
    )

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


def test_greenfield_create_cli_requires_compiled_transaction_before_writes(tmp_path, capsys) -> None:
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
    assert "greenfield create accepts only --transaction-file, --transaction-hash, and --confirm" in out
    assert "unexpected options: --release" in out
    assert "Use EDIT to add evidence and rebuild the ProductCreateTransaction" in out
    assert "create only verifies the hash and commits the compiled package" in out
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_apply_json_output_is_machine_clean(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("legacy JSON apply must fail before proposal load, compile, or commit")

    monkeypatch.setattr(greenfield_proposals, "load_proposal", forbidden)
    monkeypatch.setattr(greenfield_proposals, "apply_greenfield_proposal", forbidden)

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
    assert "greenfield apply is disabled for confirmed writes" in payload["error"]
    assert "ProductCreateTransaction" in payload["error"]
    assert "operator_output" not in payload


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
    assert "greenfield apply is disabled for confirmed writes" in payload["error"]
    assert "greenfield propose" in payload["error"]
