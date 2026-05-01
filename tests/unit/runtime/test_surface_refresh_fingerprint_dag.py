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


def _write(repo_root: Path, relative_path: str, content: str) -> Path:
    path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _seed_surface_dag_repo(repo_root: Path) -> dict[str, Path]:
    radar_helper = _seed_radar_fingerprint_repo(repo_root)
    registry_helper = _seed_registry_fingerprint_repo(repo_root)
    return {
        "compass": _write(repo_root, "odylith/runtime/delivery_intelligence.v4.json", "{\"state\":\"a\"}\n"),
        "tooling_shell": _write(repo_root, "odylith/runtime/delivery_intelligence.v4.json", "{\"state\":\"a\"}\n"),
        "radar": radar_helper,
        "registry": registry_helper,
        "casebook": _write(repo_root, "odylith/casebook/bugs/INDEX.md", "# Bugs\n\n- CB-1\n"),
        "atlas": _write(repo_root, "odylith/atlas/source/system.mmd", "flowchart TD\n  A-->B\n"),
    }


def _surface_fingerprints(repo_root: Path) -> dict[str, str]:
    return {
        surface: surface_refresh_fingerprint_dag.surface_input_fingerprint(
            repo_root=repo_root,
            surface=surface,
            atlas_sync=False,
        )
        for surface in ("compass", "tooling_shell", "radar", "registry", "casebook", "atlas")
    }


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


def test_all_governance_surface_dags_react_to_owned_inputs(tmp_path: Path) -> None:
    owned_inputs = _seed_surface_dag_repo(tmp_path)
    baseline = _surface_fingerprints(tmp_path)

    owned_inputs["compass"].write_text("{\"state\":\"compass\"}\n", encoding="utf-8")
    compass = _surface_fingerprints(tmp_path)
    assert compass["compass"] != baseline["compass"]

    owned_inputs["tooling_shell"].write_text("{\"state\":\"tooling\"}\n", encoding="utf-8")
    tooling = _surface_fingerprints(tmp_path)
    assert tooling["tooling_shell"] != baseline["tooling_shell"]

    owned_inputs["radar"].write_text("# traceability paths\nTRACEABILITY_OWNER = True\n", encoding="utf-8")
    radar = _surface_fingerprints(tmp_path)
    assert radar["radar"] != baseline["radar"]

    owned_inputs["registry"].write_text("# forensic evidence helper\nDIGEST = True\n", encoding="utf-8")
    registry = _surface_fingerprints(tmp_path)
    assert registry["registry"] != baseline["registry"]

    owned_inputs["casebook"].write_text("# Bugs\n\n- CB-1\n- CB-2\n", encoding="utf-8")
    casebook = _surface_fingerprints(tmp_path)
    assert casebook["casebook"] != baseline["casebook"]

    owned_inputs["atlas"].write_text("flowchart TD\n  A-->B\n  B-->C\n", encoding="utf-8")
    atlas = _surface_fingerprints(tmp_path)
    assert atlas["atlas"] != baseline["atlas"]


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
