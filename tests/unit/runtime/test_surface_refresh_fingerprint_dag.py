from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.governance import surface_refresh_fingerprint_dag


def _seed_registry_fingerprint_repo(repo_root: Path) -> Path:
    for relative_path, content in (
        (
            "odylith/registry/source/component_registry.v1.json",
            json.dumps({"version": "v1", "components": []}) + "\n",
        ),
        (
            "odylith/registry/source/components/registry/CURRENT_SPEC.md",
            "# Registry\n\nRegistry spec.\n",
        ),
        ("odylith/runtime/delivery_intelligence.v4.json", "{}\n"),
        (
            "src/odylith/runtime/surfaces/render_registry_dashboard.py",
            "# registry renderer\n",
        ),
        (
            "src/odylith/runtime/surfaces/registry_forensic_evidence_ui.py",
            "# forensic evidence helper\n",
        ),
    ):
        path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return repo_root / "src/odylith/runtime/surfaces/registry_forensic_evidence_ui.py"


def _seed_radar_fingerprint_repo(repo_root: Path) -> Path:
    for relative_path, content in (
        ("odylith/radar/source/INDEX.md", "# Backlog\n"),
        ("odylith/technical-plans/INDEX.md", "# Plans\n"),
        ("odylith/casebook/bugs/INDEX.md", "# Bugs\n"),
        ("odylith/registry/source/component_registry.v1.json", "{\"version\":\"v1\",\"components\":[]}\n"),
        ("odylith/atlas/source/catalog/diagrams.v1.json", "{\"version\":\"v1\",\"diagrams\":[]}\n"),
        ("odylith/compass/runtime/agent-stream.v1.jsonl", ""),
        ("odylith/radar/traceability-graph.v1.json", "{}\n"),
        ("odylith/runtime/delivery_intelligence.v4.json", "{}\n"),
        ("src/odylith/runtime/surfaces/backlog_detail_pages.py", "# detail pages\n"),
        ("src/odylith/runtime/surfaces/backlog_render_support.py", "# support\n"),
        ("src/odylith/runtime/surfaces/backlog_rich_text.py", "# rich text\n"),
        ("src/odylith/runtime/surfaces/backlog_traceability_paths.py", "# traceability paths\n"),
        ("src/odylith/runtime/surfaces/render_backlog_ui.py", "# radar renderer\n"),
        ("src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py", "# html shell\n"),
        ("src/odylith/runtime/surfaces/render_backlog_ui_payload_runtime.py", "# payload\n"),
    ):
        path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return repo_root / "src/odylith/runtime/surfaces/backlog_traceability_paths.py"


def test_registry_surface_input_fingerprint_includes_renderer_helper_source(tmp_path: Path) -> None:
    helper_path = _seed_registry_fingerprint_repo(tmp_path)

    baseline = surface_refresh_fingerprint_dag.surface_input_fingerprint(
        repo_root=tmp_path,
        surface="registry",
        atlas_sync=False,
    )

    helper_path.write_text("# forensic evidence helper\nDIGEST = True\n", encoding="utf-8")

    updated = surface_refresh_fingerprint_dag.surface_input_fingerprint(
        repo_root=tmp_path,
        surface="registry",
        atlas_sync=False,
    )

    assert updated != baseline


def test_radar_surface_input_fingerprint_includes_traceability_helper_source(tmp_path: Path) -> None:
    helper_path = _seed_radar_fingerprint_repo(tmp_path)

    baseline = surface_refresh_fingerprint_dag.surface_input_fingerprint(
        repo_root=tmp_path,
        surface="radar",
        atlas_sync=False,
    )

    helper_path.write_text("# traceability paths\nTRACEABILITY_OWNER = True\n", encoding="utf-8")

    updated = surface_refresh_fingerprint_dag.surface_input_fingerprint(
        repo_root=tmp_path,
        surface="radar",
        atlas_sync=False,
    )

    assert updated != baseline
