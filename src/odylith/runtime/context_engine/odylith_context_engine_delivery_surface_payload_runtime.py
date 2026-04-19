"""Delivery-surface payload loading for context-engine-backed product surfaces."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import odylith_context_engine_projection_search_runtime as projection_search_runtime
from odylith.runtime.context_engine import odylith_context_engine_runtime_learning_runtime as runtime_learning_runtime
from odylith.runtime.governance import delivery_intelligence_engine
from odylith.runtime.governance import sync_session as governed_sync_session


def load_delivery_surface_payload(
    *,
    repo_root: Path,
    surface: str,
    runtime_mode: str = "auto",
    buckets: Sequence[str] | None = None,
    include_shell_snapshots: bool = True,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    requested_buckets = {
        str(token or "").strip().lower()
        for token in (buckets or [])
        if str(token or "").strip()
    }
    surface_token = str(surface).strip().lower()
    session = governed_sync_session.active_sync_session()
    if session is not None and session.repo_root == root:
        cache_key = odylith_context_cache.fingerprint_payload(
            {
                "surface": surface_token,
                "runtime_mode": str(runtime_mode).strip().lower() or "auto",
                "requested_buckets": sorted(requested_buckets),
                "include_shell_snapshots": bool(include_shell_snapshots),
            }
        )
        cached = session.get_or_compute(
            namespace="delivery_surface_payload",
            key=cache_key,
            builder=lambda: _load_delivery_surface_payload_uncached(
                repo_root=root,
                surface_token=surface_token,
                runtime_mode=runtime_mode,
                requested_buckets=requested_buckets,
                include_shell_snapshots=include_shell_snapshots,
            ),
        )
        return copy.deepcopy(cached)
    return _load_delivery_surface_payload_uncached(
        repo_root=root,
        surface_token=surface_token,
        runtime_mode=runtime_mode,
        requested_buckets=requested_buckets,
        include_shell_snapshots=include_shell_snapshots,
    )


def _load_delivery_surface_payload_uncached(
    *,
    repo_root: Path,
    surface_token: str,
    runtime_mode: str,
    requested_buckets: set[str],
    include_shell_snapshots: bool,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    odylith_switch = runtime_learning_runtime._odylith_switch_snapshot(repo_root=root)  # noqa: SLF001
    payload: dict[str, Any] = {}
    if projection_search_runtime._warm_runtime(  # noqa: SLF001
        repo_root=root,
        runtime_mode=runtime_mode,
        reason="delivery_surface",
    ):
        connection = projection_search_runtime._connect(root)  # noqa: SLF001
        try:
            row = connection.execute(
                "SELECT payload_json FROM delivery_surfaces WHERE surface = ?",
                (surface_token,),
            ).fetchone()
            if row is not None:
                raw_payload = json.loads(str(row["payload_json"]))
                payload = dict(raw_payload) if isinstance(raw_payload, Mapping) else {}
        finally:
            connection.close()
    if not payload:
        try:
            artifact_payload = delivery_intelligence_engine.load_delivery_intelligence_artifact(repo_root=root)
        except Exception:
            artifact_payload = {}
        sliced = delivery_intelligence_engine.slice_delivery_intelligence_for_surface(
            payload=artifact_payload,
            surface=surface_token,
        )
        payload = dict(sliced) if isinstance(sliced, Mapping) else {}
    if requested_buckets:
        for bucket in (
            "summary",
            "case_queue",
            "systemic_brief",
            "surface_scope",
            "grid_scope",
            "components",
            "workstreams",
            "diagrams",
            "surfaces",
            "grid",
            "surface",
        ):
            if bucket in requested_buckets:
                continue
            payload.pop(bucket, None)
    if surface_token == "shell":
        payload["odylith_switch"] = odylith_switch
        payload["orchestration_adoption_snapshot"] = runtime_learning_runtime.load_orchestration_adoption_snapshot(
            repo_root=root
        )
    if surface_token == "shell" and include_shell_snapshots:
        if not bool(odylith_switch.get("enabled", True)):
            payload.pop("memory_snapshot", None)
            payload.pop("optimization_snapshot", None)
            payload.pop("evaluation_snapshot", None)
            payload.pop("odylith_drawer_history", None)
            return payload
        optimization_snapshot = (
            dict(payload.get("optimization_snapshot", {}))
            if isinstance(payload.get("optimization_snapshot"), Mapping)
            else runtime_learning_runtime.load_runtime_optimization_snapshot(repo_root=root)
        )
        evaluation_snapshot = (
            dict(payload.get("evaluation_snapshot", {}))
            if isinstance(payload.get("evaluation_snapshot"), Mapping)
            else _load_runtime_evaluation_snapshot(repo_root=root)
        )
        payload["optimization_snapshot"] = optimization_snapshot
        payload["evaluation_snapshot"] = evaluation_snapshot
        if "memory_snapshot" not in payload:
            payload["memory_snapshot"] = runtime_learning_runtime.load_runtime_memory_snapshot(
                repo_root=root,
                optimization_snapshot=optimization_snapshot,
                evaluation_snapshot=evaluation_snapshot,
            )
        payload["odylith_drawer_history"] = runtime_learning_runtime.load_odylith_drawer_history(repo_root=root)
    return payload


def _load_runtime_evaluation_snapshot(*, repo_root: Path) -> dict[str, Any]:
    from odylith.runtime.context_engine import odylith_context_engine_memory_snapshot_runtime

    return odylith_context_engine_memory_snapshot_runtime.load_runtime_evaluation_snapshot(repo_root=repo_root)


__all__ = ["load_delivery_surface_payload"]
