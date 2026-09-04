from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.surfaces import update_mermaid_diagram


def _seed_catalog(root: Path) -> Path:
    source_path = root / "odylith" / "atlas" / "source" / "example.mmd"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("flowchart LR\n    A --> B\n", encoding="utf-8")
    old_code = root / "src" / "old.py"
    old_code.parent.mkdir(parents=True, exist_ok=True)
    old_code.write_text("old = True\n", encoding="utf-8")
    catalog_path = root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "diagrams": [
                    {
                        "diagram_id": "D-010",
                        "slug": "example",
                        "title": "Example Diagram",
                        "kind": "flowchart",
                        "status": "active",
                        "owner": "product",
                        "last_reviewed_utc": "2026-09-01",
                        "source_mmd": "odylith/atlas/source/example.mmd",
                        "source_svg": "odylith/atlas/source/example.svg",
                        "source_png": "odylith/atlas/source/example.png",
                        "change_watch_paths": ["src/old.py"],
                        "summary": "Existing Atlas summary with concrete ownership.",
                        "read_guide": "Read the existing diagram from source to proof.",
                        "components": [
                            {
                                "name": "Existing owner",
                                "description": "Owns the existing Atlas boundary.",
                            }
                        ],
                        "related_backlog": [],
                        "related_plans": [],
                        "related_docs": [],
                        "related_code": ["src/old.py"],
                        "reviewed_watch_fingerprints": {"src/old.py": "old-hash"},
                        "render_source_fingerprint": "render-hash",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return catalog_path


def test_update_replaces_only_supplied_fields_and_refreshes(tmp_path: Path, monkeypatch, capsys) -> None:
    catalog_path = _seed_catalog(tmp_path)
    new_code = tmp_path / "src" / "new.py"
    new_code.write_text("new = True\n", encoding="utf-8")
    refresh_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        update_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **kwargs: refresh_calls.append(dict(kwargs)),
    )

    rc = update_mermaid_diagram.main(
        [
            "--repo-root",
            str(tmp_path),
            "--diagram-id",
            "D-010",
            "--summary",
            "Updated Atlas summary with current ownership and proof.",
            "--component",
            "Current owner::Owns the current Atlas boundary and proof.",
            "--code",
            "src/new.py",
            "--watch",
            "src/new.py",
            "--review-date",
            "2026-09-03",
        ]
    )

    entry = json.loads(catalog_path.read_text(encoding="utf-8"))["diagrams"][0]
    assert rc == 0
    assert entry["title"] == "Example Diagram"
    assert entry["source_mmd"] == "odylith/atlas/source/example.mmd"
    assert entry["summary"] == "Updated Atlas summary with current ownership and proof."
    assert entry["components"] == [
        {"name": "Current owner", "description": "Owns the current Atlas boundary and proof."}
    ]
    assert entry["related_code"] == ["src/new.py"]
    assert entry["change_watch_paths"] == ["src/new.py"]
    assert entry["last_reviewed_utc"] == "2026-09-03"
    assert "reviewed_watch_fingerprints" not in entry
    assert entry["render_source_fingerprint"] == "render-hash"
    assert refresh_calls == [
        {
            "repo_root": tmp_path.resolve(),
            "surface": "atlas",
            "operation_label": "Atlas update",
        }
    ]
    assert "updated diagram: D-010 / example" in capsys.readouterr().out


def test_update_rejects_unknown_diagram_without_writing(tmp_path: Path, monkeypatch) -> None:
    catalog_path = _seed_catalog(tmp_path)
    before = catalog_path.read_bytes()
    monkeypatch.setattr(
        update_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )

    rc = update_mermaid_diagram.main(
        [
            "--repo-root",
            str(tmp_path),
            "--diagram-id",
            "D-999",
            "--summary",
            "A concrete replacement summary for a missing diagram.",
        ]
    )

    assert rc == 2
    assert catalog_path.read_bytes() == before


def test_update_rejects_repo_escaping_paths_without_writing(tmp_path: Path) -> None:
    catalog_path = _seed_catalog(tmp_path)
    before = catalog_path.read_bytes()

    rc = update_mermaid_diagram.main(
        [
            "--repo-root",
            str(tmp_path),
            "--diagram-id",
            "D-010",
            "--watch",
            "../outside.py",
        ]
    )

    assert rc == 2
    assert catalog_path.read_bytes() == before


def test_update_requires_a_replacement_field(tmp_path: Path) -> None:
    catalog_path = _seed_catalog(tmp_path)
    before = catalog_path.read_bytes()

    rc = update_mermaid_diagram.main(
        ["--repo-root", str(tmp_path), "--diagram-id", "D-010"]
    )

    assert rc == 2
    assert catalog_path.read_bytes() == before


def test_update_rejects_invalid_review_date_without_writing(tmp_path: Path) -> None:
    catalog_path = _seed_catalog(tmp_path)
    before = catalog_path.read_bytes()

    rc = update_mermaid_diagram.main(
        [
            "--repo-root",
            str(tmp_path),
            "--diagram-id",
            "D-010",
            "--review-date",
            "not-a-date",
        ]
    )

    assert rc == 2
    assert catalog_path.read_bytes() == before
