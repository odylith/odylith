from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.evaluation import odylith_benchmark_runtime_posture_runtime as posture_runtime


def test_prime_benchmark_runtime_cache_warms_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[Path, str, str]] = []
    primed: list[Path] = []
    guidance_primed: list[Path] = []
    judgment_primed: list[Path] = []
    git_branch_primed: list[Path] = []
    git_head_primed: list[Path] = []

    def _fake_warm_projections(*, repo_root: Path, reason: str, scope: str) -> dict[str, bool]:
        calls.append((repo_root, reason, scope))
        return {"ok": True}

    monkeypatch.setattr(posture_runtime.store, "warm_projections", _fake_warm_projections)
    monkeypatch.setattr(
        posture_runtime.store,
        "prime_reasoning_projection_cache",
        lambda *, repo_root: primed.append(repo_root),
    )
    monkeypatch.setattr(
        posture_runtime.store,
        "projection_input_fingerprint",
        lambda *, repo_root, scope="default": f"{scope}-fingerprint",
    )
    monkeypatch.setattr(
        posture_runtime.store.tooling_guidance_catalog,
        "load_guidance_catalog",
        lambda *, repo_root: guidance_primed.append(repo_root)
        or {"chunk_count": 1, "source_doc_count": 1, "task_family_count": 1},
    )
    monkeypatch.setattr(
        posture_runtime.store,
        "_judgment_memory_snapshot_cached",
        lambda *, repo_root: judgment_primed.append(repo_root) or {},
    )
    monkeypatch.setattr(
        posture_runtime.store,
        "_git_branch_name",
        lambda *, repo_root: git_branch_primed.append(repo_root) or "main",
    )
    monkeypatch.setattr(
        posture_runtime.store,
        "_git_head_oid",
        lambda *, repo_root: git_head_primed.append(repo_root) or "abc123",
    )
    monkeypatch.setattr(
        posture_runtime.memory_snapshot_runtime,
        "load_runtime_memory_snapshot",
        lambda *, repo_root: {
            "backend_transition": {
                "actual_local_backend": {
                    "storage": "lance_local_columnar",
                    "sparse_recall": "tantivy_sparse_recall",
                },
                "local_backend_status": {"ready": True},
            },
            "entity_counts": {
                "indexed_entity_count": 12,
                "evidence_documents": 14,
            },
        },
    )
    monkeypatch.setattr(posture_runtime.store, "_PROCESS_WARM_CACHE", {})
    monkeypatch.setattr(posture_runtime.store, "_PROCESS_WARM_CACHE_FINGERPRINTS", {})

    posture_runtime.prime_benchmark_runtime_cache(repo_root=tmp_path)

    assert calls == [(tmp_path.resolve(), "benchmark", "full")]
    assert primed == [tmp_path.resolve()]
    assert guidance_primed == [tmp_path.resolve()]
    assert judgment_primed == [tmp_path.resolve()]
    assert git_branch_primed == [tmp_path.resolve()]
    assert git_head_primed == [tmp_path.resolve()]
    assert posture_runtime.store._PROCESS_WARM_CACHE[f"{tmp_path.resolve()}:full"] > 0  # noqa: SLF001
    assert posture_runtime.store._PROCESS_WARM_CACHE[f"{tmp_path.resolve()}:reasoning"] > 0  # noqa: SLF001
    assert posture_runtime.store._PROCESS_WARM_CACHE[f"{tmp_path.resolve()}:default"] > 0  # noqa: SLF001
    assert (
        posture_runtime.store._PROCESS_WARM_CACHE_FINGERPRINTS[f"{tmp_path.resolve()}:full"]  # noqa: SLF001
        == "full-fingerprint"
    )
    assert (
        posture_runtime.store._PROCESS_WARM_CACHE_FINGERPRINTS[f"{tmp_path.resolve()}:reasoning"]  # noqa: SLF001
        == "reasoning-fingerprint"
    )
    assert (
        posture_runtime.store._PROCESS_WARM_CACHE_FINGERPRINTS[f"{tmp_path.resolve()}:default"]  # noqa: SLF001
        == "default-fingerprint"
    )


def test_prime_benchmark_runtime_cache_requires_active_local_memory_substrate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(posture_runtime.store, "warm_projections", lambda **_: {"ok": True})
    monkeypatch.setattr(posture_runtime.store, "prime_reasoning_projection_cache", lambda **_: None)
    monkeypatch.setattr(
        posture_runtime.store.tooling_guidance_catalog,
        "load_guidance_catalog",
        lambda **_: {"chunk_count": 1, "source_doc_count": 1, "task_family_count": 1},
    )
    monkeypatch.setattr(posture_runtime.store, "_judgment_memory_snapshot_cached", lambda **_: {})
    monkeypatch.setattr(posture_runtime.store, "_git_branch_name", lambda **_: "main")
    monkeypatch.setattr(posture_runtime.store, "_git_head_oid", lambda **_: "abc123")
    monkeypatch.setattr(
        posture_runtime.memory_snapshot_runtime,
        "load_runtime_memory_snapshot",
        lambda *, repo_root: {
            "backend_transition": {
                "actual_local_backend": {
                    "storage": "compiler_projection_snapshot",
                    "sparse_recall": "repo_scan_fallback",
                },
                "local_backend_status": {"ready": False},
            },
            "entity_counts": {
                "indexed_entity_count": 0,
                "evidence_documents": 0,
            },
        },
    )

    with pytest.raises(RuntimeError, match="active local LanceDB/Tantivy memory substrate"):
        posture_runtime.prime_benchmark_runtime_cache(repo_root=tmp_path)


def test_runtime_posture_summary_reports_memory_and_remote_posture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        posture_runtime.runtime_learning_runtime,
        "load_runtime_optimization_snapshot",
        lambda *, repo_root: {"quality_posture": {"route_ready_rate": 0.8, "native_spawn_ready_rate": 0.6}},
    )
    monkeypatch.setattr(
        posture_runtime.memory_snapshot_runtime,
        "load_runtime_evaluation_snapshot",
        lambda *, repo_root: {
            "architecture": {
                "covered_case_count": 4,
                "satisfied_case_count": 3,
                "coverage_rate": 1.0,
                "satisfaction_rate": 0.75,
            }
        },
    )
    monkeypatch.setattr(
        posture_runtime.memory_snapshot_runtime,
        "load_runtime_memory_snapshot",
        lambda *, repo_root, optimization_snapshot=None, evaluation_snapshot=None: {
            "backend_transition": {
                "status": "standardized",
                "actual_local_backend": {
                    "storage": "lance_local_columnar",
                    "sparse_recall": "tantivy_sparse_recall",
                },
                "target_local_backend": {
                    "storage": "lance_local_columnar",
                    "sparse_recall": "tantivy_sparse_recall",
                },
                "local_backend_status": {"ready": True},
                "signature": {"projection_scope": "full"},
            },
            "repo_scan_degraded_fallback": {"repo_scan_degraded_fallback_rate": 0.02},
            "governance_runtime_first": {"usage_rate": 1.0, "fallback_rate": 0.0},
            "entity_counts": {"indexed_entity_count": 120, "evidence_documents": 145},
            "remote_retrieval": {
                "enabled": False,
                "configured": False,
                "mode": "disabled",
                "provider": "vespa_http",
                "status": "disabled",
            },
        },
    )

    posture = posture_runtime.runtime_posture_summary(repo_root=tmp_path)

    assert posture["memory_backed_retrieval_ready"] is True
    assert posture["memory_local_backend_ready"] is True
    assert posture["memory_projection_scope"] == "full"
    assert posture["memory_indexed_entity_count"] == 120
    assert posture["memory_evidence_document_count"] == 145
    assert posture["remote_retrieval_status"] == "disabled"
    assert posture["remote_retrieval_mode"] == "disabled"
    assert posture["remote_retrieval_enabled"] is False


def test_runtime_posture_summary_prefers_managed_runtime_when_host_python_lacks_memory_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        posture_runtime.runtime_learning_runtime,
        "load_runtime_optimization_snapshot",
        lambda *, repo_root: {"quality_posture": {}},
    )
    monkeypatch.setattr(
        posture_runtime.memory_snapshot_runtime,
        "load_runtime_evaluation_snapshot",
        lambda *, repo_root: {"architecture": {}},
    )
    monkeypatch.setattr(
        posture_runtime.memory_snapshot_runtime,
        "load_runtime_memory_snapshot",
        lambda *, repo_root, optimization_snapshot=None, evaluation_snapshot=None: {
            "backend_transition": {
                "status": "pending_target_swap",
                "actual_local_backend": {
                    "storage": "compiler_projection_snapshot",
                    "sparse_recall": "repo_scan_fallback",
                },
                "target_local_backend": {
                    "storage": "lance_local_columnar",
                    "sparse_recall": "tantivy_sparse_recall",
                },
                "local_backend_status": {"ready": False},
                "signature": {"projection_scope": "reasoning"},
            },
            "entity_counts": {"indexed_entity_count": 120, "evidence_documents": 145},
        },
    )
    managed_posture = {
        "memory_standardization_state": "standardized",
        "memory_backend_actual": {
            "storage": "lance_local_columnar",
            "sparse_recall": "tantivy_sparse_recall",
        },
        "memory_backend_target": {
            "storage": "lance_local_columnar",
            "sparse_recall": "tantivy_sparse_recall",
        },
        "memory_backed_retrieval_ready": True,
        "memory_local_backend_ready": True,
        "memory_projection_scope": "reasoning",
        "memory_indexed_entity_count": 120,
        "memory_evidence_document_count": 145,
        "remote_retrieval_enabled": False,
        "remote_retrieval_configured": False,
        "remote_retrieval_mode": "disabled",
        "remote_retrieval_provider": "vespa_http",
        "remote_retrieval_status": "disabled",
        "repo_scan_degraded_fallback_rate": 0.0,
        "repo_scan_degraded_reason_distribution": {},
        "governance_runtime_first_usage_rate": 1.0,
        "governance_runtime_first_fallback_rate": 0.0,
        "governance_runtime_first_fallback_reason_distribution": {},
        "route_ready_rate": 1.0,
        "native_spawn_ready_rate": 1.0,
        "architecture_covered_case_count": 0,
        "architecture_satisfied_case_count": 0,
        "architecture_coverage_rate": 0.0,
        "architecture_satisfaction_rate": 0.0,
    }
    monkeypatch.setattr(
        posture_runtime,
        "managed_runtime_posture_summary",
        lambda *, repo_root: dict(managed_posture),
    )

    posture = posture_runtime.runtime_posture_summary(repo_root=tmp_path)

    assert posture["memory_backed_retrieval_ready"] is True
    assert posture["memory_local_backend_ready"] is True
    assert posture["memory_backend_actual"] == managed_posture["memory_backend_actual"]
