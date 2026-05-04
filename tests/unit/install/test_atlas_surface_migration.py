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
                '  <g class="cluster default"><rect x="2" y="2" width="100" height="60" style="fill:#fafffe !important;stroke:#d8f2ed !important;"></rect><g class="cluster-label"><text>Source truth</text></g></g>',
                '  <g class="nodes"><g class="node default"><rect class="basic label-container" x="8" y="10" width="80" height="28" style="fill:#e8fbf7 !important;stroke:#5bbfb2 !important;"></rect></g></g>',
                "</svg>",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_legacy_palette_svg(path: Path) -> None:
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


def _write_order_based_semantic_cluster_svg(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                '<svg xmlns="http://www.w3.org/2000/svg" width="360" height="160" viewBox="0 0 360 160">',
                '  <g class="cluster" id="memory_lane"><rect style="fill:#effcf9 !important;stroke:#9bd8cf !important;"></rect><g class="cluster-label"><text>Clean runtime memory</text></g></g>',
                '  <g class="cluster" id="confirmation_lane"><rect style="fill:#f1f7ff !important;stroke:#a8c7f7 !important;"></rect><g class="cluster-label"><text>Confirmation-gated apply</text></g></g>',
                '  <g class="cluster" id="reasoning_lane"><rect style="fill:#fff3f0 !important;stroke:#efb3a4 !important;"></rect><g class="cluster-label"><text>Domain intelligence compiler</text></g></g>',
                '  <g class="cluster" id="intent_lane"><rect style="fill:#f2fbef !important;stroke:#a9d69e !important;"></rect><g class="cluster-label"><text>Intent and shallow evidence</text></g></g>',
                '  <g class="nodes"><g class="node default"><rect style="fill:#eaf3ff !important;stroke:#77a9ef !important;"></rect></g></g>',
                "</svg>",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_matching_semantic_cluster_svg_with_label_fill(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="120" viewBox="0 0 180 120">',
                '  <g class="cluster" id="decision_gate"><rect style="fill:#fff9f8 !important;stroke:#f6d8d0 !important;"></rect><g class="cluster-label"><text style="fill:#5c2418 !important;">Decision gate</text></g></g>',
                '  <g class="nodes"><g class="node default"><rect style="fill:#ffece7 !important;stroke:#df8f7d !important;"></rect></g></g>',
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


def test_atlas_surface_migration_flags_legacy_palette_tokens(tmp_path: Path) -> None:
    svg_path = tmp_path / "legacy.svg"
    _write_legacy_palette_svg(svg_path)

    assert atlas_surface_migration._svg_cluster_needs_polish(svg_path) is True  # noqa: SLF001
    assert atlas_surface_migration._svg_node_needs_polish(svg_path) is True  # noqa: SLF001


def test_atlas_surface_migration_flags_order_based_semantic_cluster_colors(tmp_path: Path) -> None:
    svg_path = tmp_path / "order-based.svg"
    _write_order_based_semantic_cluster_svg(svg_path)

    assert atlas_surface_migration._svg_cluster_needs_polish(svg_path) is True  # noqa: SLF001


def test_atlas_surface_migration_accepts_semantic_cluster_rect_despite_label_fill(tmp_path: Path) -> None:
    mmd_path = tmp_path / "semantic.mmd"
    svg_path = tmp_path / "semantic.svg"
    mmd_path.write_text("flowchart TB\n  subgraph Gate[Decision gate]\n    A[Confirm]\n  end\n", encoding="utf-8")
    _write_matching_semantic_cluster_svg_with_label_fill(svg_path)

    assert atlas_surface_migration._svg_needs_polish(svg_path, source_mmd_path=mmd_path) is False  # noqa: SLF001


def test_atlas_surface_migration_flags_cluster_inherited_node_fill(tmp_path: Path) -> None:
    svg_path = tmp_path / "cluster-tone-node.svg"
    svg_path.write_text(
        "\n".join(
            [
                '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="120" viewBox="0 0 180 120">',
                '  <g class="cluster" id="memory_lane"><rect style="fill:#f2fbef !important;stroke:#a9d69e !important;"></rect><g class="cluster-label"><text>Memory lane</text></g></g>',
                '  <g class="nodes"><g class="node default"><rect style="fill:#f2fbef !important;stroke:#a9d69e !important;"></rect><g class="label"><text>projection bundle</text></g></g></g>',
                "</svg>",
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert atlas_surface_migration._svg_needs_polish(svg_path) is True  # noqa: SLF001


def test_atlas_surface_migration_accepts_effective_final_wash_over_stale_authored_tokens(tmp_path: Path) -> None:
    svg_path = tmp_path / "final-style-wins.svg"
    svg_path.write_text(
        "\n".join(
            [
                '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="120" viewBox="0 0 180 120">',
                '  <g class="cluster" id="input_lane"><rect style="fill:#effcf9 !important;stroke:#9bd8cf !important;fill:#fafffe !important;stroke:#d8f2ed !important;"></rect><g class="cluster-label"><text>Input lane</text></g></g>',
                '  <g class="nodes"><g class="node default"><rect class="basic label-container" style="fill:#eafbf7 !important;stroke:#78c9bd !important;fill:#e8fbf7 !important;stroke:#5bbfb2 !important;"></rect><g class="label"><text>source request</text></g></g></g>',
                "</svg>",
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert atlas_surface_migration._svg_needs_polish(svg_path) is False  # noqa: SLF001


def test_atlas_surface_migration_flags_partial_final_wash_with_legacy_stroke(tmp_path: Path) -> None:
    svg_path = tmp_path / "partial-style.svg"
    svg_path.write_text(
        "\n".join(
            [
                '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="120" viewBox="0 0 180 120">',
                '  <g class="cluster" id="input_lane"><rect style="fill:#fafffe !important;stroke:#9bd8cf !important;"></rect><g class="cluster-label"><text>Input lane</text></g></g>',
                '  <g class="nodes"><g class="node default"><rect class="basic label-container" style="fill:#e8fbf7 !important;stroke:#5bbfb2 !important;"></rect></g></g>',
                "</svg>",
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert atlas_surface_migration._svg_needs_polish(svg_path) is True  # noqa: SLF001


def test_atlas_surface_migration_uses_cluster_identifier_like_renderer(tmp_path: Path) -> None:
    mmd_path = tmp_path / "release.mmd"
    svg_path = tmp_path / "release.svg"
    mmd_path.write_text(
        "\n".join(
            [
                "flowchart TB",
                '  subgraph Release["Maintainer proof and public claim"]',
                "    A[Publish claim]",
                "  end",
                "",
            ]
        ),
        encoding="utf-8",
    )
    svg_path.write_text(
        "\n".join(
            [
                '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="120" viewBox="0 0 180 120">',
                '  <g class="cluster" id="flowchart-Release-1"><rect style="fill:#fdfaff !important;stroke:#e8dcfb !important;"></rect><g class="cluster-label"><text>Maintainer proof and public claim</text></g></g>',
                '  <g class="nodes"><g class="node default"><rect style="fill:#f4ebff !important;stroke:#ad8ae6 !important;"></rect></g></g>',
                "</svg>",
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert atlas_surface_migration._semantic_cluster_expected_fills(mmd_path) == ("#fdfaff",)  # noqa: SLF001
    assert atlas_surface_migration._svg_needs_polish(svg_path, source_mmd_path=mmd_path) is False  # noqa: SLF001


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
    assert "fill:#fafffe" in svg_text
    assert "stroke:#d8f2ed" in svg_text
    assert "fill:#e8fbf7" in svg_text
    assert "stroke:#5bbfb2" in svg_text
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


def test_atlas_surface_migration_rerenders_existing_014_consumers_when_palette_rule_changes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_atlas_catalog(tmp_path)
    _patch_mermaid_render(monkeypatch)
    ledger = tmp_path / ".odylith" / "state" / "migrations" / "v0.1.14-atlas-render-surface-polish.v1.json"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        json.dumps(
            {
                "schema_version": atlas_surface_migration.MIGRATION_SCHEMA_VERSION,
                "migration_id": atlas_surface_migration.MIGRATION_ID,
                "verification_result": {"status": "passed"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    inspection = atlas_surface_migration.inspect_atlas_surface_migration(
        repo_root=tmp_path,
        previous_version="0.1.14",
        target_version="0.1.15",
    )
    result = atlas_surface_migration.migrate_atlas_surface_polish(
        repo_root=tmp_path,
        previous_version="0.1.14",
        target_version="0.1.15",
    )

    assert inspection.ledger_valid is True
    assert inspection.migration_required is True
    assert result.applied is True


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
