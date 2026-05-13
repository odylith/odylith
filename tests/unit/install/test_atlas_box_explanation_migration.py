from __future__ import annotations

import json
from pathlib import Path

from odylith.install import atlas_box_explanation_migration


def _seed_atlas_catalog(repo_root: Path) -> Path:
    atlas_root = repo_root / "odylith" / "atlas"
    source_root = atlas_root / "source"
    catalog_path = source_root / "catalog" / "diagrams.v1.json"
    mmd_path = source_root / "box-fixture.mmd"
    svg_path = source_root / "box-fixture.svg"
    png_path = source_root / "box-fixture.png"
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
    svg_path.write_text("<svg viewBox='0 0 1200 800'></svg>\n", encoding="utf-8")
    png_path.write_bytes(b"png")
    catalog_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "diagrams": [
                    {
                        "diagram_id": "D-901",
                        "slug": "box-fixture",
                        "title": "Box Fixture",
                        "kind": "flowchart",
                        "status": "active",
                        "owner": "product",
                        "last_reviewed_utc": "2026-05-01",
                        "source_mmd": "odylith/atlas/source/box-fixture.mmd",
                        "source_svg": "odylith/atlas/source/box-fixture.svg",
                        "source_png": "odylith/atlas/source/box-fixture.png",
                        "summary": "Atlas box explanation fixture.",
                        "change_watch_paths": ["odylith/atlas/source/box-fixture.mmd"],
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
    (atlas_root / "atlas.html").write_text("<html><body>old atlas</body></html>\n", encoding="utf-8")
    (atlas_root / "mermaid-payload.v1.js").write_text("window.__MERMAID_PAYLOAD__ = {};\n", encoding="utf-8")
    (atlas_root / "mermaid-app.v1.js").write_text("", encoding="utf-8")
    return catalog_path


def _read_payload(repo_root: Path) -> dict[str, object]:
    text = (repo_root / "odylith" / "atlas" / "mermaid-payload.v1.js").read_text(encoding="utf-8")
    return json.loads(text.split("=", 1)[1].strip().rstrip(";"))


def test_atlas_box_explanation_migration_flags_old_payload_without_inner_boxes(tmp_path: Path) -> None:
    _seed_atlas_catalog(tmp_path)

    inspection = atlas_box_explanation_migration.inspect_atlas_box_explanation_migration(
        repo_root=tmp_path,
        previous_version="0.1.14",
        target_version="0.1.15",
    )

    assert inspection.target_in_window is True
    assert inspection.expected_box_count == 3
    assert inspection.migration_required is True
    assert any("missing" in item for item in inspection.generated_surface_violations)


def test_atlas_box_explanation_migration_applies_from_each_supported_prior_release(tmp_path: Path) -> None:
    for previous_version in ("0.1.10", "0.1.11", "0.1.12", "0.1.13", "0.1.14"):
        repo_root = tmp_path / previous_version.replace(".", "_")
        _seed_atlas_catalog(repo_root)

        result = atlas_box_explanation_migration.migrate_atlas_box_explanation_contract(
            repo_root=repo_root,
            previous_version=previous_version,
            target_version="0.1.15",
        )
        payload = _read_payload(repo_root)
        diagram = payload["diagrams"][0]

        assert result.applied is True
        assert result.previous_version == previous_version
        assert (repo_root / result.ledger_path).is_file()
        assert [box["label"] for box in diagram["diagram_boxes"]] == ["Source truth", "Catalog", "Renderer"]
        assert diagram["diagram_boxes"][1]["description"] == (
            "Inside Source truth, Catalog stores the source information that downstream boxes read or update."
        )


def test_atlas_box_explanation_migration_is_idempotent_after_verified_ledger(tmp_path: Path) -> None:
    _seed_atlas_catalog(tmp_path)

    first = atlas_box_explanation_migration.migrate_atlas_box_explanation_contract(
        repo_root=tmp_path,
        previous_version="0.1.14",
        target_version="0.1.15",
    )
    second = atlas_box_explanation_migration.migrate_atlas_box_explanation_contract(
        repo_root=tmp_path,
        previous_version="0.1.15",
        target_version="0.1.15",
    )

    assert first.applied is True
    assert second.applied is False
    assert second.skipped_reason == "ledger_and_atlas_box_explanations_already_verify"


def test_atlas_box_explanation_migration_skips_pre_v015_targets(tmp_path: Path) -> None:
    _seed_atlas_catalog(tmp_path)

    result = atlas_box_explanation_migration.migrate_atlas_box_explanation_contract(
        repo_root=tmp_path,
        previous_version="0.1.13",
        target_version="0.1.14",
    )

    assert result.applied is False
    assert result.skipped_reason == "target_not_in_v0_1_15_migration_window"
