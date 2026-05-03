from __future__ import annotations

import json
from pathlib import Path

from odylith.install import atlas_surface_migration
from odylith.runtime.surfaces import auto_update_mermaid_diagrams


def _write_old_cluster_svg(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80" viewBox="0 0 120 80">',
                '  <g class="cluster default"><rect x="2" y="2" width="100" height="60" style=""></rect></g>',
                '  <g class="nodes"><g class="node default"><rect class="basic label-container" x="8" y="10" width="80" height="28" style=""></rect></g></g>',
                "</svg>",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_polished_cluster_svg(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80" viewBox="0 0 120 80">',
                '  <g class="cluster default"><rect x="2" y="2" width="100" height="60" style="fill:#f7fdfb !important;stroke:#b8e1db !important;"></rect></g>',
                '  <g class="nodes"><g class="node default"><rect class="basic label-container" x="8" y="10" width="80" height="28" style="fill:#eafbf7 !important;stroke:#78c9bd !important;"></rect></g></g>',
                "</svg>",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _seed_atlas_catalog(repo_root: Path) -> Path:
    atlas_root = repo_root / "odylith" / "atlas"
    source_root = atlas_root / "source"
    catalog_path = source_root / "catalog" / "diagrams.v1.json"
    mmd_path = source_root / "migration-fixture.mmd"
    svg_path = source_root / "migration-fixture.svg"
    png_path = source_root / "migration-fixture.png"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    mmd_path.write_text(
        "\n".join(
            [
                "flowchart TB",
                "  subgraph SourceTruth[Source truth]",
                "    A[Catalog] --> B[Renderer]",
                "  end",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _write_old_cluster_svg(svg_path)
    png_path.write_bytes(b"old-png")
    catalog_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "diagrams": [
                    {
                        "diagram_id": "D-900",
                        "slug": "migration-fixture",
                        "title": "Migration Fixture",
                        "kind": "flowchart",
                        "status": "active",
                        "owner": "product",
                        "last_reviewed_utc": "2026-04-01",
                        "source_mmd": "odylith/atlas/source/migration-fixture.mmd",
                        "source_svg": "odylith/atlas/source/migration-fixture.svg",
                        "source_png": "odylith/atlas/source/migration-fixture.png",
                        "summary": "Atlas migration fixture.",
                        "change_watch_paths": ["odylith/atlas/source/migration-fixture.mmd"],
                        "related_workstreams": ["B-900"],
                        "components": [{"name": "atlas", "description": "Atlas surface."}],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    atlas_root.mkdir(parents=True, exist_ok=True)
    (atlas_root / "atlas.html").write_text(
        ".viewer-stage::before { background-size: 42px 42px; }\n",
        encoding="utf-8",
    )
    (atlas_root / "mermaid-payload.v1.js").write_text("window.__MERMAID_PAYLOAD__ = {};\n", encoding="utf-8")
    (atlas_root / "mermaid-app.v1.js").write_text("", encoding="utf-8")
    return catalog_path


def _patch_mermaid_render(monkeypatch) -> None:
    def fake_render_batch(*, repo_root: Path, render_jobs, cli_version: str) -> None:
        assert cli_version
        for job in render_jobs:
            svg_path = repo_root / str(job["source_svg"])
            png_path = repo_root / str(job["source_png"])
            _write_polished_cluster_svg(svg_path)
            png_path.write_bytes(b"new-png")

    monkeypatch.setattr(auto_update_mermaid_diagrams, "_render_diagrams_batch", fake_render_batch)


def test_atlas_surface_migration_renders_polished_assets_and_dashboard(tmp_path: Path, monkeypatch) -> None:
    catalog_path = _seed_atlas_catalog(tmp_path)
    _patch_mermaid_render(monkeypatch)

    inspection = atlas_surface_migration.inspect_atlas_surface_migration(
        repo_root=tmp_path,
        previous_version="0.1.13",
        target_version="0.1.14",
    )
    result = atlas_surface_migration.migrate_atlas_surface_polish(
        repo_root=tmp_path,
        previous_version="0.1.13",
        target_version="0.1.14",
    )

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    html_text = (tmp_path / "odylith" / "atlas" / "atlas.html").read_text(encoding="utf-8")
    svg_text = (tmp_path / "odylith" / "atlas" / "source" / "migration-fixture.svg").read_text(encoding="utf-8")
    ledger = json.loads((tmp_path / result.ledger_path).read_text(encoding="utf-8"))
    verification = atlas_surface_migration.inspect_atlas_surface_migration(
        repo_root=tmp_path,
        previous_version="0.1.14",
        target_version="0.1.14",
    )

    assert inspection.migration_required is True
    assert result.applied is True
    assert result.migration_id == atlas_surface_migration.MIGRATION_ID
    assert catalog["diagrams"][0]["render_source_fingerprint"]
    assert "fill:#f7fdfb" in svg_text
    assert "fill:#eafbf7" in svg_text
    assert ".viewer-stage::before" not in html_text
    assert "background: #ffffff;" in html_text
    assert ledger["migration_id"] == atlas_surface_migration.MIGRATION_ID
    assert ledger["verification_result"]["status"] == "passed"
    assert ledger["verification_result"]["topology_integrity"]["status"] == "passed"
    assert ledger["verification_result"]["topology_integrity"]["algorithm"] == "multipartite-spine-v1"
    assert verification.verification_passed is True


def test_atlas_surface_migration_is_idempotent_after_verified_ledger(tmp_path: Path, monkeypatch) -> None:
    _seed_atlas_catalog(tmp_path)
    _patch_mermaid_render(monkeypatch)

    first = atlas_surface_migration.migrate_atlas_surface_polish(
        repo_root=tmp_path,
        previous_version="0.1.13",
        target_version="0.1.14",
    )
    second = atlas_surface_migration.migrate_atlas_surface_polish(
        repo_root=tmp_path,
        previous_version="0.1.14",
        target_version="0.1.14",
    )

    assert first.applied is True
    assert second.applied is False
    assert second.skipped_reason == "ledger_and_atlas_surfaces_already_verify"


def test_atlas_surface_migration_applies_from_each_supported_prior_release(tmp_path: Path, monkeypatch) -> None:
    _patch_mermaid_render(monkeypatch)
    for previous_version in ("0.1.10", "0.1.11", "0.1.12", "0.1.13"):
        repo_root = tmp_path / previous_version.replace(".", "_")
        _seed_atlas_catalog(repo_root)

        result = atlas_surface_migration.migrate_atlas_surface_polish(
            repo_root=repo_root,
            previous_version=previous_version,
            target_version="0.1.14",
        )

        assert result.applied is True
        assert result.previous_version == previous_version
        assert (repo_root / result.ledger_path).is_file()


def test_atlas_surface_migration_skips_pre_v014_targets(tmp_path: Path, monkeypatch) -> None:
    _seed_atlas_catalog(tmp_path)
    _patch_mermaid_render(monkeypatch)

    result = atlas_surface_migration.migrate_atlas_surface_polish(
        repo_root=tmp_path,
        previous_version="0.1.12",
        target_version="0.1.13",
    )

    assert result.applied is False
    assert result.skipped_reason == "target_not_in_v0_1_14_migration_window"


def test_atlas_surface_migration_reports_stale_ledger(tmp_path: Path) -> None:
    _seed_atlas_catalog(tmp_path)
    ledger = tmp_path / ".odylith" / "state" / "migrations" / "v0.1.14-atlas-render-surface-polish.v1.json"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("{not json", encoding="utf-8")

    inspection = atlas_surface_migration.inspect_atlas_surface_migration(
        repo_root=tmp_path,
        previous_version="0.1.13",
        target_version="0.1.14",
    )
    state, reason = atlas_surface_migration.atlas_surface_decision_state(
        repo_scenario="healthy_pinned_consumer",
        inspection=inspection,
    )

    assert state == "ledger_stale"
    assert "migration ledger is stale" in reason
