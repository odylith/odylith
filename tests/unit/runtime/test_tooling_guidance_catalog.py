from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.context_engine import tooling_guidance_catalog


def _write_manifest(
    repo_root: Path,
    *,
    manifest_path: str,
    chunk_id: str,
    chunk_path: str,
    canonical_source: str,
    task_families: list[str],
) -> None:
    chunk_file = repo_root / chunk_path
    chunk_file.parent.mkdir(parents=True, exist_ok=True)
    chunk_file.write_text("# Guidance\n\nKeep the packet bounded.\n", encoding="utf-8")

    manifest_file = repo_root / manifest_path
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(
        json.dumps(
            {
                "version": "v1",
                "chunks": [
                    {
                        "chunk_id": chunk_id,
                        "note_kind": "workflow",
                        "canonical_source": canonical_source,
                        "chunk_path": chunk_path,
                        "title": "Guidance",
                        "summary": "Bound the packet.",
                        "task_families": task_families,
                        "component_affinity": ["benchmark"],
                        "path_refs": ["odylith/skills/subagent-router/SKILL.md"],
                        "workstreams": ["B-038"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_compile_guidance_catalog_prefers_repo_local_manifest(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        manifest_path=tooling_guidance_catalog.CANONICAL_MANIFEST_PATH,
        chunk_id="canonical",
        chunk_path="odylith/agents-guidelines/GROUNDING_AND_NARROWING.md",
        canonical_source="odylith/agents-guidelines/GROUNDING_AND_NARROWING.md",
        task_families=["component_governance"],
    )
    _write_manifest(
        tmp_path,
        manifest_path=tooling_guidance_catalog.LEGACY_MANIFEST_PATHS[0],
        chunk_id="legacy",
        chunk_path="agents-guidelines/WORKFLOW.md",
        canonical_source="agents-guidelines/WORKFLOW.md",
        task_families=["explicit_workstream"],
    )

    payload = tooling_guidance_catalog.compile_guidance_catalog(repo_root=tmp_path)

    assert payload["manifest_path"] == tooling_guidance_catalog.CANONICAL_MANIFEST_PATH
    assert [row["chunk_id"] for row in payload["chunks"]] == ["canonical"]


def test_compile_guidance_catalog_falls_back_to_legacy_manifest_path(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        manifest_path=tooling_guidance_catalog.LEGACY_MANIFEST_PATHS[0],
        chunk_id="legacy",
        chunk_path="agents-guidelines/WORKFLOW.md",
        canonical_source="agents-guidelines/WORKFLOW.md",
        task_families=["explicit_workstream"],
    )

    payload = tooling_guidance_catalog.compile_guidance_catalog(repo_root=tmp_path)

    assert payload["manifest_path"] == tooling_guidance_catalog.LEGACY_MANIFEST_PATHS[0]
    assert payload["canonical_manifest_path"] == tooling_guidance_catalog.CANONICAL_MANIFEST_PATH
    assert payload["chunk_count"] == 1


def test_compact_catalog_summary_tracks_source_docs_and_task_families(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        manifest_path=tooling_guidance_catalog.CANONICAL_MANIFEST_PATH,
        chunk_id="catalog-counts",
        chunk_path="odylith/agents-guidelines/VALIDATION_AND_TESTING.md",
        canonical_source="odylith/agents-guidelines/VALIDATION_AND_TESTING.md",
        task_families=["component_governance", "daemon_security"],
    )

    summary = tooling_guidance_catalog.compact_catalog_summary(
        tooling_guidance_catalog.compile_guidance_catalog(repo_root=tmp_path)
    )

    assert summary["manifest_path"] == tooling_guidance_catalog.CANONICAL_MANIFEST_PATH
    assert summary["chunk_count"] == 1
    assert summary["source_doc_count"] == 1
    assert summary["task_family_count"] == 2
    assert summary["task_families"] == ["component_governance", "daemon_security"]
