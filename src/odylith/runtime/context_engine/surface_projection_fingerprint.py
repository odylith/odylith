"""Lightweight surface-input fingerprinting for hot render paths.

This module intentionally avoids importing the full projection store so render
commands can cheaply answer "did any Compass-relevant surface change?" before
they pay the heavier runtime-build import graph.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from odylith.runtime.common.consumer_profile import surface_root_path, truth_root_path
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine.projection_contract_versions import projection_contract_version

_DELIVERY_INTELLIGENCE_OUTPUT_PATH = "odylith/runtime/delivery_intelligence.v4.json"


def _path_fingerprint(path: Path, *, glob: str = "*.md") -> str:
    target = Path(path)
    if target.is_dir():
        return odylith_context_cache.fingerprint_tree(target, glob=glob)
    return odylith_context_cache.fingerprint_paths([target])


def _normalize_repo_token(token: str, *, repo_root: Path) -> str:
    from odylith.runtime.governance import workstream_inference as ws_inference

    return ws_inference.normalize_repo_token(token, repo_root=repo_root)


def _workspace_activity_fingerprint(*, repo_root: Path) -> str:
    from odylith.runtime.governance import agent_governance_intelligence as governance
    from odylith.runtime.governance import component_registry_intelligence as component_registry

    rows: list[dict[str, Any]] = []
    for raw in governance.collect_git_changed_paths(repo_root=repo_root):
        normalized = _normalize_repo_token(str(raw), repo_root=repo_root)
        if not normalized or not component_registry.is_meaningful_workspace_artifact(normalized):
            continue
        candidate = (repo_root / normalized).resolve()
        rows.append(
            {
                "path": normalized,
                "signature": odylith_context_cache.path_signature(candidate),
            }
        )
    return odylith_context_cache.fingerprint_payload(rows)


def default_surface_projection_input_fingerprint(*, repo_root: Path) -> str:
    """Return the default-scope projection fingerprint for Compass-like surfaces.

    The tracked inputs intentionally match the Odylith Context Engine default
    projection scope so Compass stays reactive to backlog, plan, bug, component,
    diagram, traceability, delivery, event-stream, and workspace-activity
    changes without importing the full compiler-backed store on the hot path.
    """

    root = Path(repo_root).resolve()
    radar_source_root = truth_root_path(repo_root=root, key="radar_source")
    technical_plans_root = truth_root_path(repo_root=root, key="technical_plans")
    casebook_bugs_root = truth_root_path(repo_root=root, key="casebook_bugs")
    component_specs_root = truth_root_path(repo_root=root, key="component_specs")
    component_registry_path = truth_root_path(repo_root=root, key="component_registry")
    product_root = surface_root_path(repo_root=root, key="product_root")
    atlas_catalog_path = product_root / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    compass_stream_path = product_root / "compass" / "runtime" / "codex-stream.v1.jsonl"
    traceability_graph_path = product_root / "radar" / "traceability-graph.v1.json"
    payload = {
        "workstreams": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("workstreams"),
                "backlog_index": _path_fingerprint(radar_source_root / "INDEX.md"),
                "backlog_archive": _path_fingerprint(radar_source_root / "archive"),
                "ideas": _path_fingerprint(radar_source_root / "ideas"),
            }
        ),
        "plans": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("plans"),
                "plan_index": _path_fingerprint(technical_plans_root / "INDEX.md"),
                "plan_done": _path_fingerprint(technical_plans_root / "done"),
                "plan_parked": _path_fingerprint(technical_plans_root / "parked"),
            }
        ),
        "bugs": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("bugs"),
                "bugs_index": _path_fingerprint(casebook_bugs_root / "INDEX.md"),
                "bugs_archive": _path_fingerprint(casebook_bugs_root / "archive"),
            }
        ),
        "diagrams": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("diagrams"),
                "catalog": _path_fingerprint(atlas_catalog_path),
            }
        ),
        "components": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("components"),
                "manifest": _path_fingerprint(component_registry_path),
                "catalog": _path_fingerprint(atlas_catalog_path),
                "ideas": _path_fingerprint(radar_source_root / "ideas"),
                "stream": _path_fingerprint(compass_stream_path),
                "component_specs": _path_fingerprint(component_specs_root),
                "traceability": _path_fingerprint(traceability_graph_path),
                "workspace_activity": _workspace_activity_fingerprint(repo_root=root),
            }
        ),
        "codex_events": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("codex_events"),
                "stream": _path_fingerprint(compass_stream_path),
            }
        ),
        "traceability": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("traceability"),
                "graph": _path_fingerprint(traceability_graph_path),
            }
        ),
        "delivery": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("delivery"),
                "output": _path_fingerprint(root / _DELIVERY_INTELLIGENCE_OUTPUT_PATH),
            }
        ),
    }
    return odylith_context_cache.fingerprint_payload(
        {
            "schema": "v1",
            "scope": "default",
            "inputs": payload,
        }
    )


__all__ = ["default_surface_projection_input_fingerprint"]
