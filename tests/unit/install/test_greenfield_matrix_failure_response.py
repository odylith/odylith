from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _module():
    return _load_module(
        SCRIPTS_ROOT / "greenfield_matrix_failure_response.py",
        "greenfield_matrix_failure_response_test",
    )


def test_synthetic_live_duplicate_name_failure_requires_source_shard_replay(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "volume-duplicate-name.json"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "shared review",
                        "prompt": "Create a greenfield proposal for shared review with path one.",
                        "required_terms": ("shared", "review"),
                        "leakage_terms": ("shared review",),
                        "stressors": ("registry-contract-pressure",),
                    },
                    {
                        "name": "shared review",
                        "prompt": "Create a greenfield proposal for shared review with path two.",
                        "required_terms": ("shared", "review"),
                        "leakage_terms": ("shared review",),
                        "stressors": ("atlas-label-pressure",),
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    output_json = tmp_path / "out" / "failed.json"
    payload = module.write_synthetic_shard_payload(
        output_json=output_json,
        shard=SimpleNamespace(case_file=case_file, tier="volume-discovery", proof_tier="discovery"),
        completed=subprocess.CompletedProcess(["greenfield-matrix"], 130, "", "live stop after failure"),
        stop_reason="cluster-threshold:matrix.generated-copy:1:live-telemetry",
        live_failure_snapshot={
            "failed_case_count": 1,
            "cluster_counts": {"matrix.generated-copy": 1},
            "failed_cases": [
                {
                    "name": "shared review",
                    "cluster": "matrix.generated-copy",
                }
            ],
        },
    )

    assert payload["synthetic"] is True
    assert payload["replay_scope"] == "source-shard"
    assert payload["exact_failed_subset_available"] is False
    assert payload["results"] == []
    assert payload["shard_replay_case_file"] == str(case_file)
    assert payload["campaign"]["failure_clusters"][0]["case_ids"] == []
    assert payload["campaign"]["failure_clusters"][0]["shard_replay_case_file"] == str(case_file)


def test_failure_response_uses_source_shard_replay_when_result_json_is_unreadable(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "volume-01.json"
    missing_result_json = tmp_path / "out" / "missing-result.json"
    tier_results = [
        {
            "tier": "volume-discovery",
            "cluster_counts": {"campaign.shard-process-failed": 1},
            "shards": [
                {
                    "name": "volume-discovery-001",
                    "case_file": str(case_file),
                    "output_json": str(missing_result_json),
                    "failed_case_count": 1,
                    "failure_clusters": [
                        {
                            "cluster": "campaign.shard-process-failed",
                            "count": 1,
                            "cases": ["volume-discovery-001"],
                        }
                    ],
                }
            ],
        }
    ]

    clusters = module.campaign_failure_clusters(tier_results)
    response = module.failure_response_plan(
        tier_results=tier_results,
        failure_clusters=clusters,
        stopped_reason="volume-discovery:campaign.shard-process-failed",
        release_readiness_proven=False,
    )

    assert response["exact_failed_subset_available"] is False
    assert response["failed_result_jsons"] == []
    assert response["shard_replay_case_files"] == [str(case_file)]
    assert "shard_replay_case_files" in response["operator_loop"][2]


def test_failure_response_uses_source_shard_replay_for_name_only_failure(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "duplicate-name-shard.json"
    result_json = tmp_path / "out" / "failed.json"
    result_json.parent.mkdir()
    result_json.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "name": "shared review",
                        "status": "failed",
                        "quality": {"passed": False},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    response = module.failure_response_plan(
        tier_results=[
            {
                "tier": "volume-discovery",
                "shards": [
                    {
                        "name": "duplicate-name-shard",
                        "case_file": str(case_file),
                        "output_json": str(result_json),
                        "failed_case_count": 1,
                        "failure_clusters": [{"cluster": "manifest.copy", "count": 1}],
                    }
                ],
            }
        ],
        failure_clusters=[{"cluster": "manifest.copy", "count": 1}],
        stopped_reason="volume-discovery:failure-threshold:1",
        release_readiness_proven=False,
    )

    assert response["exact_failed_subset_available"] is False
    assert response["failed_result_jsons"] == []
    assert response["shard_replay_case_files"] == [str(case_file)]
    assert "shard_replay_case_files" in response["operator_loop"][2]


def test_failure_response_does_not_trust_exact_replay_claim_without_identity(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "source-shard.json"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "case-001",
                        "name": "shared review",
                        "prompt": "Create a greenfield proposal for shared review recovery.",
                        "required_terms": ("shared", "recovery"),
                        "leakage_terms": ("shared review",),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result_json = tmp_path / "out" / "claimed-exact.json"
    result_json.parent.mkdir()
    result_json.write_text(
        json.dumps(
            {
                "exact_failed_subset_available": True,
                "results": [{"name": "shared review", "status": "failed"}],
            }
        ),
        encoding="utf-8",
    )

    response = module.failure_response_plan(
        tier_results=[
            {
                "tier": "volume-discovery",
                "shards": [
                    {
                        "name": "claimed-exact-shard",
                        "case_file": str(case_file),
                        "output_json": str(result_json),
                        "failed_case_count": 1,
                        "failure_clusters": [{"cluster": "manifest.copy", "count": 1}],
                    }
                ],
            }
        ],
        failure_clusters=[{"cluster": "manifest.copy", "count": 1}],
        stopped_reason="volume-discovery:failure-threshold:1",
        release_readiness_proven=False,
    )

    assert response["exact_failed_subset_available"] is False
    assert response["failed_result_jsons"] == []
    assert response["shard_replay_case_files"] == [str(case_file)]


def test_failure_response_rejects_partial_cluster_identity_coverage(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "source-shard.json"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "case-001",
                        "name": "case one",
                        "prompt": "Create a greenfield proposal for case one recovery.",
                        "required_terms": ("case", "recovery"),
                        "leakage_terms": ("case one",),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result_json = tmp_path / "out" / "partial-cluster.json"
    result_json.parent.mkdir()
    result_json.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "name": "case one",
                        "status": "failed",
                        "evidence": {"case": {"id": "case-001"}},
                    }
                ],
                "campaign": {
                    "failed_case_count": 2,
                    "failure_clusters": [
                        {
                            "cluster": "manifest.copy",
                            "count": 2,
                            "case_ids": ["case-001"],
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    response = module.failure_response_plan(
        tier_results=[
            {
                "tier": "volume-discovery",
                "shards": [
                    {
                        "name": "partial-cluster-shard",
                        "case_file": str(case_file),
                        "output_json": str(result_json),
                        "failed_case_count": 2,
                        "failure_clusters": [{"cluster": "manifest.copy", "count": 2}],
                    }
                ],
            }
        ],
        failure_clusters=[{"cluster": "manifest.copy", "count": 2}],
        stopped_reason="volume-discovery:failure-threshold:2",
        release_readiness_proven=False,
    )

    assert response["exact_failed_subset_available"] is False
    assert response["failed_result_jsons"] == []
    assert response["shard_replay_case_files"] == [str(case_file)]


def test_failure_response_rejects_derived_slug_without_source_case_id(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "duplicate-slug-source.json"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "shared review",
                        "prompt": "Create a greenfield proposal for shared review path one.",
                        "required_terms": ("shared", "review"),
                        "leakage_terms": ("shared review",),
                    },
                    {
                        "name": "shared review",
                        "prompt": "Create a greenfield proposal for shared review path two.",
                        "required_terms": ("shared", "review"),
                        "leakage_terms": ("shared review",),
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    result_json = tmp_path / "out" / "derived-slug.json"
    result_json.parent.mkdir()
    result_json.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "name": "shared review",
                        "status": "failed",
                        "evidence": {"case": {"id": "shared-review"}},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    response = module.failure_response_plan(
        tier_results=[
            {
                "tier": "volume-discovery",
                "shards": [
                    {
                        "name": "derived-slug-shard",
                        "case_file": str(case_file),
                        "output_json": str(result_json),
                        "failed_case_count": 1,
                        "failure_clusters": [{"cluster": "manifest.copy", "count": 1}],
                    }
                ],
            }
        ],
        failure_clusters=[{"cluster": "manifest.copy", "count": 1}],
        stopped_reason="volume-discovery:failure-threshold:1",
        release_readiness_proven=False,
    )

    assert response["exact_failed_subset_available"] is False
    assert response["failed_result_jsons"] == []
    assert response["shard_replay_case_files"] == [str(case_file)]


def test_campaign_failure_clusters_do_not_double_count_tier_and_shard_aggregates() -> None:
    module = _module()

    clusters = module.campaign_failure_clusters(
        [
            {
                "tier": "60-case-regression",
                "cluster_counts": {"manifest.generated-copy-quality.atlas-renderer.atlas": 2},
                "shards": [
                    {
                        "name": "shard-a",
                        "failure_clusters": [
                            {
                                "cluster": "manifest.generated-copy-quality.atlas-renderer.atlas",
                                "count": 1,
                                "cases": ["case one"],
                                "example_issue": "atlas repeated visible copy",
                            }
                        ],
                    },
                    {
                        "name": "shard-b",
                        "failure_clusters": [
                            {
                                "cluster": "manifest.generated-copy-quality.atlas-renderer.atlas",
                                "count": 1,
                                "cases": ["case two"],
                            }
                        ],
                    },
                ],
            },
            {
                "tier": "release-proof",
                "cluster_counts": {"manifest.generated-copy-quality.atlas-renderer.atlas": 1},
                "shards": [],
            },
        ]
    )

    assert clusters[0]["cluster"] == "manifest.generated-copy-quality.atlas-renderer.atlas"
    assert clusters[0]["count"] == 3
    assert clusters[0]["tiers"] == ["60-case-regression", "release-proof"]
    assert clusters[0]["shards"] == ["shard-a", "shard-b"]
    assert clusters[0]["cases"] == ["case one", "case two"]


def test_failure_response_ignores_interrupted_sibling_without_failure_evidence(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "failed-case.json"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "failed-case-001",
                        "name": "failed case",
                        "prompt": "Create a greenfield proposal for a failed case recovery path.",
                        "required_terms": ("failed", "recovery"),
                        "leakage_terms": ("failed case",),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    failed_result_json = tmp_path / "failed.json"
    failed_result_json.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "name": "failed case",
                        "status": "failed",
                        "evidence": {"case": {"id": "failed-case-001"}},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    response = module.failure_response_plan(
        tier_results=[
            {
                "tier": "volume-discovery",
                "shards": [
                    {
                        "name": "failed-shard",
                        "case_file": str(case_file),
                        "status": "failed",
                        "failed_case_count": 1,
                        "output_json": str(failed_result_json),
                        "failure_clusters": [{"cluster": "manifest.copy", "count": 1}],
                    },
                    {
                        "name": "interrupted-sibling",
                        "status": "stopped",
                        "failed_case_count": 0,
                        "output_json": "/tmp/stopped.json",
                        "failure_clusters": [],
                    },
                ],
            }
        ],
        failure_clusters=[{"cluster": "manifest.copy", "count": 1}],
        stopped_reason="volume-discovery:failure-threshold:1",
        release_readiness_proven=False,
    )

    assert response["failed_result_jsons"] == [str(failed_result_json)]
