from __future__ import annotations

import json
from pathlib import Path

from odylith.install import casebook_metadata_migration
from odylith.runtime.governance import casebook_source_validation


def _write_legacy_bug(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "- Bug ID: CB-155",
                "",
                "- Status: Mitigated locally; pending platform release",
                "",
                "- Created: 2026-04-26",
                "",
                "- Fixed: Pending release/deploy",
                "",
                "- Severity: P1",
                "",
                "- Reproducibility: Consistent",
                "",
                "- Type: OSW template upgrade repair / coroutine scheduler runtime / LocalStack proof UX",
                "",
                "- Description: Legacy Casebook metadata leaked prose into rendered detail cards.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_bug_with_type(path: Path, *, bug_id: str, bug_type: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"- Bug ID: {bug_id}",
                "",
                "- Status: Open",
                "",
                "- Created: 2026-04-26",
                "",
                "- Severity: P1",
                "",
                "- Reproducibility: High",
                "",
                f"- Type: {bug_type}",
                "",
                "- Description: Legacy consumer Casebook type migration fixture.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_casebook_metadata_migration_normalizes_source_and_rendered_payloads(tmp_path: Path) -> None:
    bug_path = tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-26-legacy-casebook-labels.md"
    _write_legacy_bug(bug_path)

    result = casebook_metadata_migration.migrate_casebook_compact_metadata(
        repo_root=tmp_path,
        previous_version="0.1.12",
        target_version="0.1.13",
    )

    source_text = bug_path.read_text(encoding="utf-8")
    payload_text = (tmp_path / "odylith" / "casebook" / "casebook-payload.v1.js").read_text(encoding="utf-8")
    detail_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((tmp_path / "odylith" / "casebook").glob("casebook-detail-shard-*.v1.js"))
    )
    validation = casebook_source_validation.validate_casebook_sources(repo_root=tmp_path)
    ledger = json.loads((tmp_path / result.ledger_path).read_text(encoding="utf-8"))

    assert result.applied is True
    assert "- Status: Mitigated" in source_text
    assert "- Fixed: Pending" in source_text
    assert "- Type: UX" in source_text
    assert validation.passed
    assert "Mitigated locally; pending platform release" not in payload_text + detail_text
    assert "Pending release/deploy" not in payload_text + detail_text
    assert "OSW template upgrade repair" not in payload_text + detail_text
    assert '"Status": "Mitigated"' in detail_text
    assert '"Fixed": "Pending"' in detail_text
    assert '"Type": "UX"' in detail_text
    assert len(result.written_paths) == len(set(result.written_paths))
    assert result.removed_paths == ()
    assert "odylith/casebook/bugs/2026-04-26-legacy-casebook-labels.md" in result.written_paths
    assert "odylith/casebook/casebook-payload.v1.js" in result.written_paths
    assert any(path.startswith("odylith/casebook/casebook-detail-shard-") for path in result.written_paths)
    assert ledger["migration_id"] == casebook_metadata_migration.MIGRATION_ID
    assert ledger["written_paths"] == list(result.written_paths)
    assert ledger["verification_result"]["status"] == "passed"


def test_casebook_metadata_migration_preserves_allowed_taxonomy_and_normalizes_legacy_type_labels(
    tmp_path: Path,
) -> None:
    expected_types = {
        "App": "App",
        "Config": "Config",
        "Data": "Data",
        "Dependency": "Dependency",
        "Deployment": "Deployment",
        "IaC": "IaC",
        "Infra": "Infra",
        "Observability": "Observability",
        "Operational": "Operational",
        "OperatorUX": "OperatorUX",
        "Product": "Product",
        "Release": "Release",
        "Runtime": "Runtime",
        "Security": "Security",
        "Tooling": "Tooling",
        "UX": "UX",
        "Workflow": "Workflow",
        "Database": "Database",
        "RandomProjectWord": "Product",
        "UI": "UX",
        "UX / lifecycle": "UX",
        "ForwardFixUpdatedLocallyPendingPlatformReleaseDeploy": "Release",
        "OSW template upgrade repair / coroutine scheduler runtime / LocalStack proof UX": "UX",
        "AccountLifecycleOnboardi": "Install",
        "AuthWorkflowContract": "Security",
        "ControlPlaneDeploy": "Deployment",
        "ControlPlaneDeployIAMSco": "Security",
        "CredentialBootstrap": "Security",
        "Day2ManifestMetadataPath": "Deployment",
        "Day2WaveTaskDefinitionCo": "Deployment",
        "DiagnosticsOwnership": "Observability",
        "HiddenCLISurfaceDrift": "Tooling",
        "HostedLongWaitAuthAndRes": "Security",
        "HostedPreviewFalseNegati": "Workflow",
        "HostedProofSandboxStateC": "Workflow",
        "HostedProofSourceAnchorI": "Workflow",
        "HostedProofZeroCredentia": "Security",
        "InfraLifecycleProtectedR": "Infra",
        "KafkaTopicContractOSWUpg": "Runtime",
        "ManagedWorkflowSourceOfT": "Workflow",
        "OSWUpgradeContractRegres": "Install",
        "ObservabilityCorrelation": "Observability",
        "ObservabilityDiagnostics": "Observability",
        "PlatformRunnerDependency": "Dependency",
        "PlatformRunnerKafkaTopic": "Runtime",
        "PrivateJobsRunnerManifes": "Deployment",
        "PublicReadPlanePermissio": "Security",
        "TestHarnessInfraRegressi": "Infra",
        "ZeroCredentialOSWContrac": "Security",
        "ZeroCredentialOnboarding": "Security",
    }
    bug_root = tmp_path / "odylith" / "casebook" / "bugs"
    for index, bug_type in enumerate(expected_types, start=1):
        _write_bug_with_type(
            bug_root / f"2026-04-26-type-fixture-{index:03}.md",
            bug_id=f"CB-{index:03}",
            bug_type=bug_type,
        )

    result = casebook_metadata_migration.migrate_casebook_compact_metadata(
        repo_root=tmp_path,
        previous_version="0.1.12",
        target_version="0.1.13",
    )

    migrated_by_id: dict[str, str] = {}
    for path in sorted(bug_root.glob("2026-04-26-type-fixture-*.md")):
        bug_id = ""
        bug_type = ""
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("- Bug ID:"):
                bug_id = line.split(":", 1)[1].strip()
            if line.startswith("- Type:"):
                bug_type = line.split(":", 1)[1].strip()
        assert bug_id
        assert bug_type
        migrated_by_id[bug_id] = bug_type

    expected_by_id = {
        f"CB-{index:03}": expected
        for index, expected in enumerate(expected_types.values(), start=1)
    }
    validation = casebook_source_validation.validate_casebook_sources(repo_root=tmp_path)
    payload_text = (tmp_path / "odylith" / "casebook" / "casebook-payload.v1.js").read_text(encoding="utf-8")

    assert result.applied is True
    assert migrated_by_id == expected_by_id
    assert validation.passed
    assert "ForwardFixUpdatedLocallyPendingPlatformReleaseDeploy" not in payload_text
    assert "OSW template upgrade repair" not in payload_text
    assert "UX / lifecycle" not in payload_text
    assert "Database" in payload_text
    assert "RandomProjectWord" not in payload_text
    assert "Workflow" in payload_text


def test_casebook_metadata_migration_is_idempotent_after_verified_ledger(tmp_path: Path) -> None:
    bug_path = tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-26-legacy-casebook-labels.md"
    _write_legacy_bug(bug_path)

    first = casebook_metadata_migration.migrate_casebook_compact_metadata(
        repo_root=tmp_path,
        previous_version="0.1.12",
        target_version="0.1.13",
    )
    second = casebook_metadata_migration.migrate_casebook_compact_metadata(
        repo_root=tmp_path,
        previous_version="0.1.13",
        target_version="0.1.13",
    )
    inspection = casebook_metadata_migration.inspect_casebook_compact_metadata_migration(
        repo_root=tmp_path,
        previous_version="0.1.13",
        target_version="0.1.13",
    )

    assert first.applied is True
    assert second.applied is False
    assert second.skipped_reason == "ledger_and_casebook_metadata_already_verify"
    assert inspection.verification_passed is True


def test_casebook_metadata_migration_applies_from_each_prior_release(tmp_path: Path) -> None:
    for previous_version in ("0.1.10", "0.1.11", "0.1.12"):
        repo_root = tmp_path / previous_version.replace(".", "_")
        bug_path = repo_root / "odylith" / "casebook" / "bugs" / "2026-04-26-legacy-casebook-labels.md"
        _write_legacy_bug(bug_path)

        result = casebook_metadata_migration.migrate_casebook_compact_metadata(
            repo_root=repo_root,
            previous_version=previous_version,
            target_version="0.1.13",
        )

        source_text = bug_path.read_text(encoding="utf-8")
        assert result.applied is True
        assert result.previous_version == previous_version
        assert "- Status: Mitigated" in source_text
        assert "- Fixed: Pending" in source_text
        assert "- Type: UX" in source_text
        assert (repo_root / result.ledger_path).is_file()


def test_casebook_status_fsm_migration_applies_from_0_1_13_to_0_1_14(tmp_path: Path) -> None:
    bug_path = tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-26-legacy-casebook-labels.md"
    _write_legacy_bug(bug_path)

    result = casebook_metadata_migration.migrate_casebook_status_fsm(
        repo_root=tmp_path,
        previous_version="0.1.13",
        target_version="0.1.14",
    )

    source_text = bug_path.read_text(encoding="utf-8")
    payload_text = (tmp_path / "odylith" / "casebook" / "casebook-payload.v1.js").read_text(encoding="utf-8")
    validation = casebook_source_validation.validate_casebook_sources(repo_root=tmp_path)
    ledger = json.loads((tmp_path / result.ledger_path).read_text(encoding="utf-8"))

    assert result.applied is True
    assert result.migration_id == casebook_metadata_migration.STATUS_FSM_MIGRATION_ID
    assert "- Status: Mitigated" in source_text
    assert "- Fixed: Pending" in source_text
    assert "- Type: UX" in source_text
    assert validation.passed
    assert '"status": "Mitigated"' in payload_text
    assert '"status_token": "mitigated"' in payload_text
    assert ledger["migration_id"] == casebook_metadata_migration.STATUS_FSM_MIGRATION_ID
    assert ledger["verification_result"]["status"] == "passed"


def test_casebook_status_fsm_migration_applies_from_each_supported_prior_release(tmp_path: Path) -> None:
    for previous_version in ("0.1.10", "0.1.11", "0.1.12", "0.1.13"):
        repo_root = tmp_path / f"status_{previous_version.replace('.', '_')}"
        bug_path = repo_root / "odylith" / "casebook" / "bugs" / "2026-04-26-legacy-casebook-labels.md"
        _write_legacy_bug(bug_path)

        result = casebook_metadata_migration.migrate_casebook_status_fsm(
            repo_root=repo_root,
            previous_version=previous_version,
            target_version="0.1.14",
        )

        assert result.applied is True
        assert result.previous_version == previous_version
        assert "- Status: Mitigated" in bug_path.read_text(encoding="utf-8")
        assert (repo_root / result.ledger_path).is_file()


def test_casebook_status_fsm_migration_is_idempotent_after_verified_ledger(tmp_path: Path) -> None:
    bug_path = tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-26-legacy-casebook-labels.md"
    _write_legacy_bug(bug_path)

    first = casebook_metadata_migration.migrate_casebook_status_fsm(
        repo_root=tmp_path,
        previous_version="0.1.13",
        target_version="0.1.14",
    )
    second = casebook_metadata_migration.migrate_casebook_status_fsm(
        repo_root=tmp_path,
        previous_version="0.1.14",
        target_version="0.1.14",
    )

    assert first.applied is True
    assert second.applied is False
    assert second.skipped_reason == "ledger_and_casebook_status_fsm_already_verify"


def test_casebook_status_fsm_migration_repairs_stale_detail_layout_surface(tmp_path: Path) -> None:
    bug_path = tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-26-legacy-casebook-labels.md"
    _write_legacy_bug(bug_path)
    first = casebook_metadata_migration.migrate_casebook_status_fsm(
        repo_root=tmp_path,
        previous_version="0.1.13",
        target_version="0.1.14",
    )
    app_path = tmp_path / "odylith" / "casebook" / "casebook-app.v1.js"
    app_path.write_text(
        "\n".join(
            [
                "function renderDetail(detail) {",
                "  detailPane.innerHTML = `${summary}<div class=\"detail-meta\">${chips.join(\"\")}</div><div class=\"detail-links\"></div>`;",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    inspection = casebook_metadata_migration.inspect_casebook_status_fsm_migration(
        repo_root=tmp_path,
        previous_version="0.1.14",
        target_version="0.1.14",
    )
    second = casebook_metadata_migration.migrate_casebook_status_fsm(
        repo_root=tmp_path,
        previous_version="0.1.14",
        target_version="0.1.14",
    )
    repaired_text = app_path.read_text(encoding="utf-8")

    assert first.applied is True
    assert inspection.migration_required is True
    assert any("boxed detail card contract" in violation for violation in inspection.generated_surface_violations)
    assert second.applied is True
    assert 'class="brief-card casebook-summary-card"' in repaired_text
    assert '<p class="brief-card-title">Summary</p>' in repaired_text
    assert '<p class="brief-card-title">Casebook</p>' not in repaired_text
    assert repaired_text.find('<div class="detail-meta">${chips.join("")}</div>') < repaired_text.find("${summary}")


def test_casebook_metadata_migration_skips_pre_v013_targets(tmp_path: Path) -> None:
    bug_path = tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-26-legacy-casebook-labels.md"
    _write_legacy_bug(bug_path)

    result = casebook_metadata_migration.migrate_casebook_compact_metadata(
        repo_root=tmp_path,
        previous_version="0.1.11",
        target_version="0.1.12",
    )

    assert result.applied is False
    assert result.skipped_reason == "target_not_in_v0_1_13_migration_window"
    assert "Mitigated locally; pending platform release" in bug_path.read_text(encoding="utf-8")


def test_casebook_metadata_migration_skips_index_only_casebook(tmp_path: Path) -> None:
    index_path = tmp_path / "odylith" / "casebook" / "bugs" / "INDEX.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("# Bugs Index\n", encoding="utf-8")

    result = casebook_metadata_migration.migrate_casebook_compact_metadata(
        repo_root=tmp_path,
        previous_version="0.1.12",
        target_version="0.1.13",
    )
    inspection = casebook_metadata_migration.inspect_casebook_compact_metadata_migration(
        repo_root=tmp_path,
        previous_version="0.1.12",
        target_version="0.1.13",
    )

    assert result.applied is False
    assert result.skipped_reason == "no_casebook_bug_source_records"
    assert inspection.casebook_bug_source_exists is False
    assert inspection.migration_required is False
    assert index_path.read_text(encoding="utf-8") == "# Bugs Index\n"
    assert not (tmp_path / "odylith" / "casebook" / "casebook.html").exists()


def test_casebook_metadata_migration_reports_unreadable_generated_payload(tmp_path: Path) -> None:
    bug_path = tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-26-legacy-casebook-labels.md"
    _write_legacy_bug(bug_path)
    casebook_root = tmp_path / "odylith" / "casebook"
    (casebook_root / "casebook.html").write_text("", encoding="utf-8")
    (casebook_root / "casebook-app.v1.js").write_text("", encoding="utf-8")
    (casebook_root / "casebook-payload.v1.js").write_bytes(b"\xff")

    inspection = casebook_metadata_migration.inspect_casebook_compact_metadata_migration(
        repo_root=tmp_path,
        previous_version="0.1.12",
        target_version="0.1.13",
    )

    assert any(
        violation.endswith("casebook-payload.v1.js: unreadable generated Casebook surface: UnicodeDecodeError")
        for violation in inspection.generated_surface_violations
    )
