from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_diagrams


def test_greenfield_diagram_owner_validates_rendered_surface_custody(tmp_path: Path) -> None:
    for relative_path in (
        "odylith/atlas/atlas.html",
        "odylith/atlas/mermaid-payload.v1.js",
        "odylith/atlas/mermaid-app.v1.js",
        "odylith/atlas/source/demo.svg",
        "odylith/atlas/source/demo.png",
    ):
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("rendered\n", encoding="utf-8")
    catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(
            {
                "diagrams": [
                    {
                        "diagram_id": "D-001",
                        "source_svg": "odylith/atlas/source/demo.svg",
                        "source_png": "odylith/atlas/source/demo.png",
                        "render_source_fingerprint": "sha256:demo",
                        "reviewed_watch_fingerprints": {
                            "odylith/atlas/source/demo.mmd": "sha256:source"
                        },
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = greenfield_apply_diagrams.raise_for_greenfield_rendered_surface_custody(
        repo_root=tmp_path,
        diagram_ids=("D-001",),
    )

    assert result == {"status": "passed", "atlas_surface_count": 3, "atlas_diagram_count": 1}


def test_greenfield_diagram_owner_reports_rendered_surface_custody_failures(tmp_path: Path) -> None:
    for relative_path in (
        "odylith/atlas/atlas.html",
        "odylith/atlas/mermaid-payload.v1.js",
        "odylith/atlas/mermaid-app.v1.js",
        "odylith/atlas/source/demo.svg",
    ):
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("rendered\n", encoding="utf-8")
    catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(
            {
                "diagrams": [
                    {
                        "diagram_id": "D-001",
                        "source_svg": "odylith/atlas/source/demo.svg",
                        "source_png": "odylith/atlas/source/demo.png",
                        "render_source_fingerprint": "",
                        "reviewed_watch_fingerprints": {},
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError) as exc_info:
        greenfield_apply_diagrams.raise_for_greenfield_rendered_surface_custody(
            repo_root=tmp_path,
            diagram_ids=("D-001",),
        )

    message = str(exc_info.value)
    assert "D-001: missing rendered Atlas source_png" in message
    assert "D-001: missing Atlas render_source_fingerprint" in message
    assert "D-001: missing Atlas reviewed_watch_fingerprints" in message


def test_greenfield_diagram_owner_validates_compiled_ids_and_sources() -> None:
    package = SimpleNamespace(
        atlas_diagram_ids=("d-001", " D-002 "),
        atlas_catalog_rows=(
            {"diagram_id": "D-001", "source_mmd": "odylith/atlas/source/one.mmd"},
            {"diagram_id": "D-002", "source_mmd": "odylith/atlas/source/two.mmd"},
        ),
    )

    assert greenfield_apply_diagrams.compiled_atlas_diagram_ids(package, expected_count=2) == [
        "D-001",
        "D-002",
    ]
    assert [
        row["source_mmd"]
        for row in greenfield_apply_diagrams.compiled_atlas_catalog_rows(
            package,
            expected_ids=("D-001", "D-002"),
        )
    ] == ["odylith/atlas/source/one.mmd", "odylith/atlas/source/two.mmd"]
    with pytest.raises(ValueError, match="missing or incomplete"):
        greenfield_apply_diagrams.compiled_atlas_diagram_ids(package, expected_count=3)


def _traceability_plan(path: str) -> SimpleNamespace:
    return SimpleNamespace(
        diagram_links=(
            SimpleNamespace(diagram_id="D-001", related_backlog_paths=(path,)),
        )
    )


def _catalog_rows(root: Path, path: str) -> tuple[dict[str, object], ...]:
    return greenfield_apply_diagrams.render_prewrite_atlas_catalog_rows(
        root=root,
        rows=(
            {
                "slug": "demo-flow",
                "title": "Demo Flow",
                "kind": "flowchart",
                "owner": "repo",
                "summary": "Shows the demo path.",
                "read_guide": "Read from intake to outcome.",
                "components": [{"name": "Demo", "description": "Owns the demo path."}],
                "watch_paths": [],
            },
        ),
        diagram_ids=("D-001",),
        traceability_plan=_traceability_plan(path),
        review_date="2026-07-10",
    )


def test_prewrite_atlas_catalog_rebases_absolute_backlog_links_to_repo_paths(
    tmp_path: Path,
) -> None:
    rows = _catalog_rows(
        tmp_path,
        str(tmp_path / "odylith/radar/source/ideas/2026-07/demo.md"),
    )

    assert rows[0]["related_backlog"] == ["odylith/radar/source/ideas/2026-07/demo.md"]


def test_prewrite_atlas_catalog_rejects_backlog_links_outside_repo(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Atlas path escapes repo root"):
        _catalog_rows(tmp_path, str(tmp_path.parent / "outside.md"))


def test_prewrite_atlas_catalog_rejects_symlinked_backlog_escape(tmp_path: Path) -> None:
    external_root = tmp_path.parent / f"{tmp_path.name}-external"
    external_root.mkdir()
    (external_root / "outside.md").write_text("outside\n", encoding="utf-8")
    linked_root = tmp_path / "odylith/radar/source/linked"
    linked_root.parent.mkdir(parents=True)
    linked_root.symlink_to(external_root, target_is_directory=True)

    with pytest.raises(ValueError, match="Atlas path escapes repo root"):
        _catalog_rows(tmp_path, str(linked_root / "outside.md"))
