"""Runtime posture and warm-cache helpers for benchmark proof lanes."""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any
from typing import Mapping

from odylith.runtime.context_engine import odylith_context_engine_memory_snapshot_runtime as memory_snapshot_runtime
from odylith.runtime.context_engine import odylith_context_engine_runtime_learning_runtime as runtime_learning_runtime
from odylith.runtime.context_engine import odylith_context_engine_store as store

_RUNTIME_POSTURE_MANAGED_HELPER_ENV = "ODYLITH_BENCHMARK_RUNTIME_POSTURE_MANAGED_HELPER"
_BENCHMARK_WARM_CACHE_SECONDS = 30.0


def _memory_backed_retrieval_ready(
    *,
    actual_backend: Mapping[str, Any],
    local_backend_status: Mapping[str, Any],
    entity_counts: Mapping[str, Any],
) -> bool:
    return (
        bool(local_backend_status.get("ready"))
        and str(actual_backend.get("storage", "")).strip() == "lance_local_columnar"
        and str(actual_backend.get("sparse_recall", "")).strip() == "tantivy_sparse_recall"
        and int(entity_counts.get("indexed_entity_count", 0) or 0) > 0
        and int(entity_counts.get("evidence_documents", 0) or 0) > 0
    )


def runtime_posture_summary(*, repo_root: Path) -> dict[str, Any]:
    optimization = runtime_learning_runtime.load_runtime_optimization_snapshot(repo_root=repo_root)
    evaluation = memory_snapshot_runtime.load_runtime_evaluation_snapshot(repo_root=repo_root)
    memory = memory_snapshot_runtime.load_runtime_memory_snapshot(
        repo_root=repo_root,
        optimization_snapshot=optimization,
        evaluation_snapshot=evaluation,
    )
    backend_transition = (
        dict(memory.get("backend_transition", {}))
        if isinstance(memory.get("backend_transition"), Mapping)
        else {}
    )
    actual_backend = (
        dict(backend_transition.get("actual_local_backend", {}))
        if isinstance(backend_transition.get("actual_local_backend"), Mapping)
        else {}
    )
    target_backend = (
        dict(backend_transition.get("target_local_backend", {}))
        if isinstance(backend_transition.get("target_local_backend"), Mapping)
        else {}
    )
    local_backend_status = (
        dict(backend_transition.get("local_backend_status", {}))
        if isinstance(backend_transition.get("local_backend_status"), Mapping)
        else {}
    )
    signature = (
        dict(backend_transition.get("signature", {}))
        if isinstance(backend_transition.get("signature"), Mapping)
        else {}
    )
    degraded_fallback = (
        dict(memory.get("repo_scan_degraded_fallback", {}))
        if isinstance(memory.get("repo_scan_degraded_fallback"), Mapping)
        else {}
    )
    governance_runtime_first = (
        dict(memory.get("governance_runtime_first", {}))
        if isinstance(memory.get("governance_runtime_first"), Mapping)
        else {}
    )
    entity_counts = (
        dict(memory.get("entity_counts", {}))
        if isinstance(memory.get("entity_counts"), Mapping)
        else {}
    )
    remote_retrieval = (
        dict(memory.get("remote_retrieval", {}))
        if isinstance(memory.get("remote_retrieval"), Mapping)
        else {}
    )
    quality_posture = (
        dict(optimization.get("quality_posture", {}))
        if isinstance(optimization.get("quality_posture"), Mapping)
        else {}
    )
    architecture = (
        dict(evaluation.get("architecture", {}))
        if isinstance(evaluation.get("architecture"), Mapping)
        else {}
    )
    storage = str(actual_backend.get("storage", "")).strip()
    sparse_recall = str(actual_backend.get("sparse_recall", "")).strip()
    payload = {
        "memory_standardization_state": str(backend_transition.get("status", "")).strip(),
        "memory_backend_actual": {
            "storage": storage,
            "sparse_recall": sparse_recall,
        },
        "memory_backend_target": {
            "storage": str(target_backend.get("storage", "")).strip(),
            "sparse_recall": str(target_backend.get("sparse_recall", "")).strip(),
        },
        "memory_backed_retrieval_ready": _memory_backed_retrieval_ready(
            actual_backend=actual_backend,
            local_backend_status=local_backend_status,
            entity_counts=entity_counts,
        ),
        "memory_local_backend_ready": bool(local_backend_status.get("ready")),
        "memory_projection_scope": str(signature.get("projection_scope", "")).strip(),
        "memory_indexed_entity_count": int(entity_counts.get("indexed_entity_count", 0) or 0),
        "memory_evidence_document_count": int(entity_counts.get("evidence_documents", 0) or 0),
        "remote_retrieval_enabled": bool(remote_retrieval.get("enabled")),
        "remote_retrieval_configured": bool(remote_retrieval.get("configured")),
        "remote_retrieval_mode": str(remote_retrieval.get("mode", "")).strip() or "disabled",
        "remote_retrieval_provider": str(remote_retrieval.get("provider", "")).strip(),
        "remote_retrieval_status": str(remote_retrieval.get("status", "")).strip() or "disabled",
        "repo_scan_degraded_fallback_rate": float(
            degraded_fallback.get("repo_scan_degraded_fallback_rate", 0.0) or 0.0
        ),
        "repo_scan_degraded_reason_distribution": (
            dict(degraded_fallback.get("repo_scan_degraded_reason_distribution", {}))
            if isinstance(degraded_fallback.get("repo_scan_degraded_reason_distribution"), Mapping)
            else {}
        ),
        "governance_runtime_first_usage_rate": float(governance_runtime_first.get("usage_rate", 0.0) or 0.0),
        "governance_runtime_first_fallback_rate": float(
            governance_runtime_first.get("fallback_rate", 0.0) or 0.0
        ),
        "governance_runtime_first_fallback_reason_distribution": (
            dict(governance_runtime_first.get("fallback_reason_distribution", {}))
            if isinstance(governance_runtime_first.get("fallback_reason_distribution"), Mapping)
            else {}
        ),
        "route_ready_rate": float(quality_posture.get("route_ready_rate", 0.0) or 0.0),
        "native_spawn_ready_rate": float(quality_posture.get("native_spawn_ready_rate", 0.0) or 0.0),
        "architecture_covered_case_count": int(architecture.get("covered_case_count", 0) or 0),
        "architecture_satisfied_case_count": int(architecture.get("satisfied_case_count", 0) or 0),
        "architecture_coverage_rate": float(architecture.get("coverage_rate", 0.0) or 0.0),
        "architecture_satisfaction_rate": float(architecture.get("satisfaction_rate", 0.0) or 0.0),
    }
    if payload["memory_backed_retrieval_ready"]:
        return payload
    managed_payload = managed_runtime_posture_summary(repo_root=repo_root)
    if not managed_payload:
        return payload
    managed_actual_backend = (
        dict(managed_payload.get("memory_backend_actual", {}))
        if isinstance(managed_payload.get("memory_backend_actual"), Mapping)
        else {}
    )
    if (
        bool(managed_payload.get("memory_backed_retrieval_ready"))
        and bool(managed_payload.get("memory_local_backend_ready"))
        and str(managed_actual_backend.get("storage", "")).strip() == "lance_local_columnar"
        and str(managed_actual_backend.get("sparse_recall", "")).strip() == "tantivy_sparse_recall"
    ):
        return managed_payload
    return payload


def _runtime_posture_python_candidates(*, repo_root: Path) -> list[Path]:
    root = Path(repo_root).resolve()
    rows = [
        root / ".odylith" / "runtime" / "current" / "bin" / "python",
        root / ".venv" / "bin" / "python",
    ]
    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in rows:
        token = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if token in seen:
            continue
        seen.add(token)
        deduped.append(candidate)
    return deduped


def managed_runtime_posture_summary(*, repo_root: Path) -> dict[str, Any] | None:
    if os.environ.get(_RUNTIME_POSTURE_MANAGED_HELPER_ENV) == "1":
        return None
    root = Path(repo_root).resolve()
    current_python = Path(sys.executable).resolve()
    script = (
        "import json\n"
        "from pathlib import Path\n"
        "from odylith.runtime.evaluation import odylith_benchmark_runtime_posture_runtime as posture_runtime\n"
        f"print(json.dumps(posture_runtime.runtime_posture_summary(repo_root=Path({str(root)!r})), sort_keys=True))\n"
    )
    for candidate in _runtime_posture_python_candidates(repo_root=root):
        if not candidate.is_file():
            continue
        with contextlib.suppress(OSError):
            if candidate.resolve() == current_python:
                continue
        env = os.environ.copy()
        existing_pythonpath = str(env.get("PYTHONPATH", "")).strip()
        env["PYTHONPATH"] = os.pathsep.join(
            token
            for token in [str((root / "src").resolve()), existing_pythonpath]
            if token
        )
        env[_RUNTIME_POSTURE_MANAGED_HELPER_ENV] = "1"
        completed = subprocess.run(  # noqa: S603
            [str(candidate), "-c", script],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if completed.returncode != 0:
            continue
        output = str(completed.stdout or "").strip().splitlines()
        if not output:
            continue
        with contextlib.suppress(json.JSONDecodeError):
            payload = json.loads(output[-1])
            if isinstance(payload, Mapping):
                return dict(payload)
    return None


def prime_benchmark_runtime_cache(*, repo_root: Path) -> None:
    root = Path(repo_root).resolve()
    store.warm_projections(repo_root=root, reason="benchmark", scope="full")
    store.prime_reasoning_projection_cache(repo_root=root)
    guidance_catalog = store.tooling_guidance_catalog.load_guidance_catalog(repo_root=root)
    guidance_chunk_count = int(guidance_catalog.get("chunk_count", 0) or 0)
    guidance_source_doc_count = int(guidance_catalog.get("source_doc_count", 0) or 0)
    guidance_task_family_count = int(guidance_catalog.get("task_family_count", 0) or 0)
    if guidance_chunk_count <= 0 or guidance_source_doc_count <= 0 or guidance_task_family_count <= 0:
        raise RuntimeError(
            "Benchmark warm cache requires a populated guidance catalog before proof runs."
        )
    store._judgment_memory_snapshot_cached(repo_root=root)  # noqa: SLF001
    store._git_branch_name(repo_root=root)  # noqa: SLF001
    store._git_head_oid(repo_root=root)  # noqa: SLF001
    memory_snapshot = memory_snapshot_runtime.load_runtime_memory_snapshot(repo_root=root)
    backend_transition = (
        dict(memory_snapshot.get("backend_transition", {}))
        if isinstance(memory_snapshot.get("backend_transition"), Mapping)
        else {}
    )
    actual_backend = (
        dict(backend_transition.get("actual_local_backend", {}))
        if isinstance(backend_transition.get("actual_local_backend"), Mapping)
        else {}
    )
    local_backend_status = (
        dict(backend_transition.get("local_backend_status", {}))
        if isinstance(backend_transition.get("local_backend_status"), Mapping)
        else {}
    )
    entity_counts = (
        dict(memory_snapshot.get("entity_counts", {}))
        if isinstance(memory_snapshot.get("entity_counts"), Mapping)
        else {}
    )
    if not _memory_backed_retrieval_ready(
        actual_backend=actual_backend,
        local_backend_status=local_backend_status,
        entity_counts=entity_counts,
    ):
        raise RuntimeError(
            "Benchmark warm cache requires an active local LanceDB/Tantivy memory substrate before proof runs."
        )
    cache_until = time.monotonic() + _BENCHMARK_WARM_CACHE_SECONDS
    full_fingerprint = store.projection_input_fingerprint(repo_root=root, scope="full")
    reasoning_fingerprint = store.projection_input_fingerprint(repo_root=root, scope="reasoning")
    default_fingerprint = store.projection_input_fingerprint(repo_root=root, scope="default")
    store._PROCESS_WARM_CACHE[f"{root}:full"] = cache_until  # noqa: SLF001
    store._PROCESS_WARM_CACHE_FINGERPRINTS[f"{root}:full"] = full_fingerprint  # noqa: SLF001
    store._PROCESS_WARM_CACHE[f"{root}:reasoning"] = cache_until  # noqa: SLF001
    store._PROCESS_WARM_CACHE_FINGERPRINTS[f"{root}:reasoning"] = reasoning_fingerprint  # noqa: SLF001
    store._PROCESS_WARM_CACHE[f"{root}:default"] = cache_until  # noqa: SLF001
    store._PROCESS_WARM_CACHE_FINGERPRINTS[f"{root}:default"] = default_fingerprint  # noqa: SLF001
