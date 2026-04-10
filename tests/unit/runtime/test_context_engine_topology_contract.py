from __future__ import annotations

import json
from pathlib import Path


def _atlas_diagram_by_id(*, repo_root: Path, diagram_id: str) -> dict[str, object]:
    catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    diagrams = payload.get("diagrams", []) if isinstance(payload, dict) else []
    for row in diagrams:
        if isinstance(row, dict) and row.get("diagram_id") == diagram_id:
            return row
    raise AssertionError(f"missing Atlas diagram {diagram_id}")


def test_context_engine_projection_runtime_modules_are_watched_by_context_stack_diagrams() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    projection_targets = {
        "src/odylith/runtime/context_engine/odylith_context_engine_projection_entity_runtime.py",
        "src/odylith/runtime/context_engine/odylith_context_engine_projection_backlog_runtime.py",
        "src/odylith/runtime/context_engine/odylith_context_engine_projection_registry_runtime.py",
    }
    proof_targets = {
        "src/odylith/runtime/context_engine/odylith_context_engine_projection_entity_runtime.py",
        "src/odylith/runtime/context_engine/odylith_context_engine_packet_session_runtime.py",
        "src/odylith/runtime/context_engine/odylith_context_engine_packet_summary_runtime.py",
    }

    context_stack = _atlas_diagram_by_id(repo_root=repo_root, diagram_id="D-002")
    proof_state = _atlas_diagram_by_id(repo_root=repo_root, diagram_id="D-026")

    for target in projection_targets:
        assert target in context_stack["change_watch_paths"]
        assert target in context_stack["related_code"]
    for target in proof_targets:
        assert target in proof_state["change_watch_paths"]
        assert target in proof_state["related_code"]


def test_context_engine_spec_documents_projection_and_packet_runtime_modules() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    spec_path = repo_root / "odylith" / "registry" / "source" / "components" / "odylith-context-engine" / "CURRENT_SPEC.md"
    spec_text = spec_path.read_text(encoding="utf-8")

    assert "`odylith_context_engine_projection_entity_runtime.py`" in spec_text
    assert "`odylith_context_engine_projection_backlog_runtime.py`" in spec_text
    assert "`odylith_context_engine_projection_registry_runtime.py`" in spec_text
    assert "`odylith_context_engine_packet_session_runtime.py`" in spec_text
    assert "`odylith_context_engine_packet_summary_runtime.py`" in spec_text
    assert "Exact entity resolution, release selector routing" in spec_text
