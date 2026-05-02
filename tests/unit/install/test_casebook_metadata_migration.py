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
