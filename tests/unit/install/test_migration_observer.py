"""Migration classification, exact assessments and release registry contracts."""

import json
from pathlib import Path

from odylith.install import migration_observer, migration_release_gate, migration_runtime
from odylith.install.value_engine_migration import MIGRATION_ID


def test_surface_migration_observer_classifies_consumer_visible_surface_paths(tmp_path: Path) -> None:
    report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=(
            "odylith/skills/odylith-sync/SKILL.md",
            "src/odylith/runtime/surfaces/render_casebook_dashboard.py",
            "src/odylith/install/agents.py",
            "src/odylith/cli.py",
            "README.md",
            "odylith/radar/source/ideas/2026-04/generated.md",
        ),
    )

    assert report.ok is False
    assert {need.need_id for need in report.needs} == {
        "browser-surfaces",
        "guidance-and-skills",
        "install-managed-assets",
        "operator-cli-contracts",
        "public-docs-and-release-guidance",
    }
    assert "odylith/radar/source/ideas/2026-04/generated.md" not in report.changed_paths
    assert all(need.governance_marker.startswith("migration-observer:0.1.12:") for need in report.needs)
    assert all(need.governance_marker != need.marker_family for need in report.needs)
    assert all(len(need.change_fingerprint) == 12 for need in report.needs)


def test_surface_migration_observer_passes_only_completed_target_specific_records(tmp_path: Path) -> None:
    first_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/skills/odylith-sync/SKILL.md",),
    )
    marker = first_report.needs[0].governance_marker
    record = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "migration.md"
    record.parent.mkdir(parents=True)
    record.write_text(
        "\n".join(
            [
                "status: finished",
                "idea_id: B-999",
                "title: Surface migration proof",
                "",
                "## Migration Observer Needs",
                f"- `{marker}`",
                "- stale prose token `migration-observer:0.1.11:guidance-and-skills` should not satisfy 0.1.12",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/skills/odylith-sync/SKILL.md",),
    )
    stale_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.13",
        changed_paths=("odylith/skills/odylith-sync/SKILL.md",),
    )

    assert report.ok is True
    assert report.blocked_need_ids == ()
    assert report.records[0].workstream_id == "B-999"
    assert stale_report.ok is False
    assert stale_report.blocked_need_ids == ("guidance-and-skills",)


def test_surface_migration_observer_requires_change_fingerprint_not_class_marker(tmp_path: Path) -> None:
    record = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "class-marker.md"
    record.parent.mkdir(parents=True)
    record.write_text(
        "\n".join(
            [
                "status: finished",
                "idea_id: B-997",
                "title: Class marker is not enough",
                "",
                "- `migration-observer:0.1.12:guidance-and-skills`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/skills/odylith-sync/SKILL.md",),
    )

    assert report.ok is False
    assert report.needs[0].marker_family in report.records[0].markers
    assert report.needs[0].governance_marker not in report.records[0].markers
    assert report.blocked_need_ids == ("guidance-and-skills",)


def test_surface_migration_observer_rechecks_same_path_when_content_changes(tmp_path: Path) -> None:
    skill_path = tmp_path / "odylith" / "skills" / "sample" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("first guidance contract\n", encoding="utf-8")
    first_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/skills/sample/SKILL.md",),
    )
    marker = first_report.needs[0].governance_marker
    record = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "migration.md"
    record.parent.mkdir(parents=True)
    record.write_text(
        "\n".join(
            [
                "status: finished",
                "idea_id: B-996",
                "title: Exact content marker",
                "",
                f"- `{marker}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    covered_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/skills/sample/SKILL.md",),
    )
    skill_path.write_text("second guidance contract\n", encoding="utf-8")
    changed_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/skills/sample/SKILL.md",),
    )

    assert covered_report.ok is True
    assert changed_report.ok is False
    assert changed_report.needs[0].governance_marker != marker
    assert changed_report.blocked_need_ids == ("guidance-and-skills",)


def test_surface_migration_observer_fingerprint_ignores_rendered_observer_markers(tmp_path: Path) -> None:
    rendered = tmp_path / "odylith" / "radar" / "radar.html"
    rendered.parent.mkdir(parents=True)
    rendered.write_text(
        "rendered release note migration-observer:0.1.12:browser-surfaces:aaaaaaaaaaaa\n"
        '<script src="backlog-payload.v1.js?v=aaaaaaaaaaaa"></script>\n',
        encoding="utf-8",
    )
    first_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/radar/radar.html",),
    )
    marker = first_report.needs[0].governance_marker
    record = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "migration.md"
    record.parent.mkdir(parents=True)
    record.write_text(
        "\n".join(
            [
                "status: finished",
                "idea_id: B-995",
                "title: Rendered observer marker proof",
                "",
                f"- `{marker}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    rendered.write_text(
        f"rendered release note {marker}\n"
        '<script src="backlog-payload.v1.js?v=bbbbbbbbbbbb"></script>\n',
        encoding="utf-8",
    )

    covered_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/radar/radar.html",),
    )

    assert covered_report.ok is True
    assert covered_report.needs[0].governance_marker == marker
    assert covered_report.blocked_need_ids == ()


def test_surface_migration_observer_fingerprint_ignores_added_observer_marker_lines(tmp_path: Path) -> None:
    rendered = tmp_path / "odylith" / "radar" / "radar.html"
    rendered.parent.mkdir(parents=True)
    rendered.write_text(
        "rendered release note without observer marker\n"
        '<script src="backlog-payload.v1.js?v=aaaaaaaaaaaa"></script>\n',
        encoding="utf-8",
    )
    first_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/radar/radar.html",),
    )
    marker = first_report.needs[0].governance_marker
    record = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "migration.md"
    record.parent.mkdir(parents=True)
    record.write_text(
        "\n".join(
            [
                "status: finished",
                "idea_id: B-994",
                "title: Added observer marker proof",
                "",
                "Assessment: generated browser refresh is covered by the renderer migration.",
                f"- `{marker}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    rendered.write_text(
        "rendered release note without observer marker\n"
        "Migration observer markers:\n"
        f"- `{marker}`\n"
        '<script src="backlog-payload.v1.js?v=bbbbbbbbbbbb"></script>\n',
        encoding="utf-8",
    )

    covered_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("odylith/radar/radar.html",),
    )

    assert covered_report.ok is True
    assert covered_report.needs[0].governance_marker == marker
    assert covered_report.blocked_need_ids == ()


def test_surface_migration_observer_fingerprint_ignores_generated_derivative_churn(tmp_path: Path) -> None:
    changed_paths = (
        "odylith/runtime/delivery_intelligence.v4.json",
        "odylith/atlas/source/catalog/diagrams.v1.json",
        "odylith/registry/source/components/radar/FORENSICS.v1.json",
    )
    for index, token in enumerate(changed_paths, start=1):
        path = tmp_path / token
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"generated": index, "marker": "migration-observer:0.1.12:browser-surfaces:aaaaaaaaaaaa"}),
            encoding="utf-8",
        )

    first_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=changed_paths,
    )
    markers = [need.governance_marker for need in first_report.needs]
    record = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "migration.md"
    record.parent.mkdir(parents=True)
    record.write_text(
        "\n".join(
            [
                "status: finished",
                "idea_id: B-994",
                "title: Generated derivative churn proof",
                "",
                *(f"- `{marker}`" for marker in markers),
                "",
            ]
        ),
        encoding="utf-8",
    )
    for index, token in enumerate(changed_paths, start=10):
        (tmp_path / token).write_text(
            json.dumps({"generated": index, "marker": "migration-observer:0.1.12:browser-surfaces:bbbbbbbbbbbb"}),
            encoding="utf-8",
        )

    covered_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=changed_paths,
    )

    assert covered_report.ok is True
    assert {need.governance_marker for need in covered_report.needs} == set(markers)
    assert covered_report.blocked_need_ids == ()


def test_surface_migration_observer_rejects_incomplete_records_with_matching_markers(tmp_path: Path) -> None:
    first_report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("src/odylith/cli.py",),
    )
    marker = first_report.needs[0].governance_marker
    record = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "queued.md"
    record.parent.mkdir(parents=True)
    record.write_text(
        "\n".join(
            [
                "status: queued",
                "idea_id: B-998",
                "title: Queued surface migration assessment",
                "",
                f"- `{marker}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report = migration_observer.observe_surface_migration_needs(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("src/odylith/cli.py",),
    )

    assert report.ok is False
    assert report.records[0].completed() is False
    assert report.blocked_need_ids == ("operator-cli-contracts",)


def test_release_gate_blocks_surface_changes_without_completed_observer_record(tmp_path: Path) -> None:
    report = migration_release_gate.validate_release_migration_gate(
        repo_root=tmp_path,
        target_version="0.1.12",
        changed_paths=("src/odylith/install/agents.py",),
    )

    assert report.ok is False
    assert report.surface_migration_observer.blocked_need_ids == ("install-managed-assets",)
    assert any("surface migration assessment incomplete" in item for item in report.blocked_manual_migrations)


def test_release_gate_reports_registered_migrations_and_no_lifecycle_bypass() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    report = migration_release_gate.validate_release_migration_gate(
        repo_root=repo_root,
        target_version="0.1.12",
        changed_paths=(),
    )

    assert report.ok is True
    assert not report.ungated_lifecycle_paths
    assert report.fixture_matrix[migration_runtime.LEGACY_ROOT_MIGRATION_ID]["apply"] is True
    assert report.fixture_matrix[MIGRATION_ID]["dry_run"] is True
    assert report.fixture_matrix[MIGRATION_ID]["stale_ledger"] is True
    assert report.destructive_write_matrix["host.claude.preverified-settings"][
        "test_install_bundle_preserves_host_settings_when_runtime_download_fails"
    ] is True
    assert report.destructive_write_matrix["migration.legacy-product-conflict"][
        "test_legacy_odyssey_product_conflict_blocks_before_overwrite"
    ] is True
    assert report.destructive_write_matrix["governance.first-install-authoring-order"][
        "test_first_install_governance_records_can_be_created_in_every_surface_order"
    ] is True
    assert "destructive_write_scenarios" in report.as_dict()
    assert report.surface_migration_observer.ok is True
    assert report.as_dict()["surface_migration_observer"]["schema_version"] == (
        migration_observer.OBSERVER_SCHEMA_VERSION
    )


def test_release_gate_blocks_migration_required_manifest_without_definition(tmp_path: Path) -> None:
    report = migration_release_gate.validate_release_migration_gate(
        repo_root=tmp_path,
        target_version="0.1.10",
        release_manifest={"migration_required": True, "repo_schema_version": 1},
    )

    assert report.ok is False
    assert any("no registered migration definition" in item for item in report.blocked_manual_migrations)
    assert json.loads(json.dumps(report.as_dict()))["ok"] is False
