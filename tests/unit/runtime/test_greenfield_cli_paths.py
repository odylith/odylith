from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from odylith import cli
from odylith.runtime.domain_intelligence import (
    greenfield_apply_diagrams,
    greenfield_create_baseline,
    greenfield_create_commit,
    greenfield_post_confirm_handoff,
    greenfield_proposals,
    greenfield_proposals_cli,
    greenfield_surface_refresh_proof,
)
from odylith.runtime.domain_intelligence.greenfield_create_manifest import (
    PRECONFIRM_ENGINE_VERSION,
    PRECONFIRM_QUALITY_MANIFEST_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    build_product_create_transaction,
    product_create_transaction_hash,
    product_create_transaction_to_dict,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_text import normalize_domain_token
from odylith.runtime.surfaces import brand_assets
from tests.unit.runtime.greenfield_proposal_fixtures import (
    _seed_empty_governance_repo,
    _write_confirmed_intent,
    _canonical_model_authored_greenfield_fixture,
    approved_authored_quality_manifest_fixture,
    canonical_model_authored_intent_fixture,
    compiled_greenfield_package_fixture,
    surface_refresh_preview_fixture,
)


@pytest.fixture(autouse=True)
def _prevent_real_browser_launch(monkeypatch) -> None:
    monkeypatch.setattr(greenfield_post_confirm_handoff.webbrowser, "open", lambda *_args, **_kwargs: False)


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
    return approved_authored_quality_manifest_fixture()


def _stub_dashboard_refresh(monkeypatch, calls: list[dict[str, object]] | None = None) -> None:
    def refresh(**kwargs: object) -> None:
        if calls is not None:
            calls.append(dict(kwargs))
        _write_stubbed_atlas_render_outputs(Path(str(kwargs["repo_root"])))

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
    propose_args = ["propose", "--repo-root", str(repo_root), "--prompt", prompt]
    if edit_evidence_file:
        propose_args.extend(("--edit-evidence", edit_evidence_file))
    propose_args.extend(("--format", "json"))
    compile_rc = greenfield_proposals_cli.main(propose_args)
    compile_output = capsys.readouterr().out
    assert compile_rc == 0, compile_output
    compile_payload = json.loads(compile_output)
    assert "product_create_transaction" in compile_payload, compile_output
    transaction_hash = str(compile_payload["product_create_transaction"]["transaction_hash"])
    transaction_file = str(compile_payload["transaction_file"])
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
    create_rc = greenfield_proposals_cli.main(create_args)
    create_output = capsys.readouterr().out
    return create_rc, create_output, compile_payload


def test_greenfield_domain_token_normalizer_keeps_common_words_legible() -> None:
    assert normalize_domain_token("attaches") == "attach"
    assert normalize_domain_token("matches") == "match"
    assert normalize_domain_token("processes") == "process"
    assert normalize_domain_token("statuses") == "status"
    assert normalize_domain_token("readings") == "reading"


def test_greenfield_completion_opens_exact_committed_project_url(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("ODYLITH_NO_BROWSER", raising=False)
    navigation = greenfield_post_confirm_handoff.post_confirm_navigation(tmp_path)
    opened: list[tuple[str, int]] = []
    monkeypatch.setattr(
        greenfield_post_confirm_handoff.webbrowser,
        "open",
        lambda url, new=0: opened.append((url, new)) or True,
    )

    result = greenfield_post_confirm_handoff.open_committed_dashboard(navigation)

    expected_url = f"{(tmp_path / 'odylith/index.html').resolve().as_uri()}?tab=project"
    assert result == {"status": "opened", "url": expected_url, "reason": ""}
    assert opened == [(expected_url, 2)]


def test_greenfield_completion_browser_failure_does_not_raise(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("ODYLITH_NO_BROWSER", raising=False)
    navigation = greenfield_post_confirm_handoff.post_confirm_navigation(tmp_path)
    monkeypatch.setattr(
        greenfield_post_confirm_handoff.webbrowser,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("browser unavailable")),
    )

    result = greenfield_post_confirm_handoff.open_committed_dashboard(navigation)

    assert result["status"] == "unavailable"
    assert result["reason"] == "OSError: browser unavailable"


def test_greenfield_completion_respects_automated_browser_opt_out(tmp_path, monkeypatch) -> None:
    navigation = greenfield_post_confirm_handoff.post_confirm_navigation(tmp_path)

    def fail_open(*_args, **_kwargs) -> bool:
        raise AssertionError("automated validation must not open a desktop browser")

    monkeypatch.setattr(greenfield_post_confirm_handoff.webbrowser, "open", fail_open)

    result = greenfield_post_confirm_handoff.open_committed_dashboard(navigation)

    assert result["status"] == "unavailable"
    assert result["reason"] == "browser auto-open disabled by ODYLITH_NO_BROWSER"


def test_greenfield_confirm_intent_flag_is_retired(tmp_path, capsys) -> None:
    rc = greenfield_proposals_cli.main(
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


def test_greenfield_apply_cli_rejects_legacy_confirm_path_before_compile(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    assert not hasattr(greenfield_proposals, "load_proposal")
    assert not hasattr(greenfield_proposals, "apply_greenfield_proposal")

    rc = greenfield_proposals_cli.main(
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


def test_greenfield_help_marks_apply_as_disabled_and_create_as_confirmed_write_path(capsys) -> None:
    with pytest.raises(SystemExit) as exit_error:
        cli.main(["greenfield", "--help"])

    output = capsys.readouterr().out
    assert exit_error.value.code == 0
    assert "Disabled legacy command; confirmed writes use create." in output
    assert "create" in output
    assert "Commit a compiled ProductCreateTransaction." in output


def _compiled_transaction_for_cli(tmp_path: Path):
    proposal = _canonical_model_authored_greenfield_fixture(tmp_path)
    authority = dict(proposal[PRODUCT_INTENT_AUTHORITY_KEY])
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
    monkeypatch.setattr(greenfield_create_commit, "commit_greenfield_create_transaction", forbidden)

    rc = greenfield_proposals_cli.main(
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
        assert kwargs["transaction_file"] == transaction_path
        assert kwargs["transaction_hash"] == transaction.transaction_hash
        assert kwargs["confirm"] is True
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
    monkeypatch.setattr(greenfield_create_commit, "commit_greenfield_create_transaction", fake_commit)
    dashboard = (tmp_path / "odylith/index.html").resolve()
    monkeypatch.setattr(
        greenfield_post_confirm_handoff,
        "post_confirm_navigation",
        lambda _repo_root, *, transaction_hash="": {
            "dashboard_path": str(dashboard),
            "project_url": f"{dashboard.as_uri()}?tab=project",
            "generation_transaction_hash": transaction_hash,
        },
    )

    rc = greenfield_proposals_cli.main(
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
        raise AssertionError("a transaction without a compiler receipt must fail before governed writes")

    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", forbidden)
    monkeypatch.setattr(greenfield_create_commit.greenfield_compiled_write, "write_compiled_greenfield_package", forbidden)

    rc = greenfield_proposals_cli.main(
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
        raise AssertionError("a receipt-drifted transaction must fail before governed writes")

    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", forbidden)
    monkeypatch.setattr(greenfield_create_commit.greenfield_compiled_write, "write_compiled_greenfield_package", forbidden)

    rc = greenfield_proposals_cli.main(
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
    monkeypatch.setattr(greenfield_create_commit, "commit_greenfield_create_transaction", forbidden)

    rc = greenfield_proposals_cli.main(
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

    monkeypatch.setattr(greenfield_create_commit, "load_sealed_product_create_commit", forbidden)
    monkeypatch.setattr(greenfield_proposals, "build_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_proposals, "compile_greenfield_create_transaction", forbidden)
    monkeypatch.setattr(greenfield_create_commit, "commit_greenfield_create_transaction", forbidden)

    rc = greenfield_proposals_cli.main(
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
    monkeypatch.setattr(greenfield_create_commit, "commit_greenfield_create_transaction", forbidden)

    rc = greenfield_proposals_cli.main(
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
    rc = greenfield_proposals_cli.main(
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


def test_greenfield_create_cli_requires_confirmation_before_writes(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    rc = greenfield_proposals_cli.main(
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
    assert "Open the generated governance workspace:" not in out
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_create_cli_requires_compiled_transaction_before_writes(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    rc = greenfield_proposals_cli.main(
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
    assert "unexpected options: --prompt, --release" in out
    assert "Use EDIT to add evidence and rebuild the ProductCreateTransaction" in out
    assert "create only verifies the hash and commits the compiled package" in out
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_apply_json_output_is_machine_clean(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("legacy JSON apply must fail before proposal load, compile, or commit")

    assert not hasattr(greenfield_proposals, "load_proposal")

    rc = greenfield_proposals_cli.main(
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

    rc = greenfield_proposals_cli.main(
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
