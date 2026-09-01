"""Shared fixtures for Greenfield matrix campaign tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    combined_prompt_evidence_source,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    supported_greenfield_model_profile_ids,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    SUPPORTED_COMPLEXITY_BANDS,
    SUPPORTED_PUBLIC_INPUT_FORMATS,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def matrix_campaign_runner_module(name: str):
    return load_module(SCRIPTS_ROOT / "greenfield_matrix_campaign_runner.py", name)


def command_arg(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


def write_payload(path: Path, *, status: str, cluster: str = "") -> None:
    clusters = [{"cluster": cluster, "count": 1, "cases": ["case one"]}] if cluster else []
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "status": status,
                "campaign": {
                    "completed_case_count": 1,
                    "failed_case_count": 0 if status == "passed" else 1,
                    "failure_clusters": clusters,
                },
            }
        ),
        encoding="utf-8",
    )


def write_case_file(
    path: Path,
    *,
    name: str,
    stressors: tuple[str, ...],
    case_id: str = "",
) -> None:
    path.write_text(
        json.dumps(
            {
                "version": "odylith.greenfield.matrix.case-file.v1",
                "cases": [
                    {
                        "name": name,
                        **({"case_id": case_id} if case_id else {}),
                        "prompt": (
                            f"Create a greenfield proposal for {name} with modal registry proof "
                            f"and {name} leakage phrase."
                        ),
                        "required_terms": ("modal", "registry"),
                        "leakage_terms": (f"{name} leakage phrase",),
                        "stressors": stressors,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def write_semantic_release_fixture(*, repo_root: Path, temp_root: Path) -> tuple[Path, Path]:
    """Write a minimal frozen holdout spanning all model execution profiles."""

    tracked_path = repo_root / "tests/fixtures/tracked.json"
    tracked_path.parent.mkdir(parents=True)
    tracked_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "tracked-1",
                        "name": "tracked",
                        "prompt": "Alpha reviewer records one result.",
                        "required_terms": ["Alpha"],
                        "leakage_terms": ["Alpha"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    cases = (
        {
            "prompt": "Omega Operator records one proof token.",
            "edit_evidence": "",
            "complexity": {},
        },
        {
            "prompt": "Sigma Operator accepts one permit decision.",
            "edit_evidence": "Keep the accepted decision visible for review.",
            "complexity": {"actors": 5},
        },
        {
            "prompt": "Delta Operator publishes one readiness result.",
            "edit_evidence": "",
            "complexity": {
                "actors": 17,
                "internal_systems": 17,
                "ambiguities": 9,
                "safety_boundaries": 9,
            },
        },
    )
    holdout_path = temp_root / "holdout.json"
    holdout_path.write_text(
        json.dumps(
            {
                "version": "odylith.greenfield.final-holdout.v2",
                "claim_class": "blinded-independent-synthetic-holdout",
                "cases": [
                    {
                        "case_id": f"holdout-{index}",
                        "name": f"holdout {index}",
                        "prompt": row["prompt"],
                        "required_terms": [row["prompt"].split()[0]],
                        "leakage_terms": [" ".join(row["prompt"].rstrip(".").split()[-2:])],
                        **(
                            {"confirmed_intent_markdown": row["edit_evidence"]}
                            if row["edit_evidence"]
                            else {}
                        ),
                    }
                    for index, row in enumerate(cases, start=1)
                ],
                "annotations": [
                    _semantic_annotation(
                        f"holdout-{index}",
                        row["prompt"],
                        edit_evidence=row["edit_evidence"],
                        complexity_overrides=row["complexity"],
                    )
                    for index, row in enumerate(cases, start=1)
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest_path = repo_root / "evaluation-splits.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": "odylith.greenfield.evaluation-splits.v2",
                "tracked_corpus": {
                    "path": "tests/fixtures/tracked.json",
                    "sha256": hashlib.sha256(tracked_path.read_bytes()).hexdigest(),
                    "case_count": 1,
                    "assignment": {
                        "algorithm": "metamorphic-or-source-group-sha256-bucket-v1",
                        "seed": "a" * 64,
                        "buckets": {
                            "development": [0, 5999],
                            "regression": [6000, 8499],
                            "private_validation": [8500, 9999],
                        },
                    },
                },
                "final_holdout": {
                    "sha256": hashlib.sha256(holdout_path.read_bytes()).hexdigest(),
                    "byte_size": holdout_path.stat().st_size,
                    "case_count": 3,
                    "annotation_count": 3,
                    "claim_class": "blinded-independent-synthetic-holdout",
                },
                "profiles": {
                    "complexity_bands": list(SUPPORTED_COMPLEXITY_BANDS),
                    "evidence_formats": list(SUPPORTED_PUBLIC_INPUT_FORMATS),
                    "models": list(supported_greenfield_model_profile_ids()),
                    "model_assignment": {
                        "version": "case-id-balanced-sha256-v1",
                        "seed": "f1e5a66a5cce578b0bd9f56d96f08887358632627231769667c432933b9dfe6f",
                    },
                },
                "frozen_floors": {
                    "version": "odylith.greenfield.structural-floors.v1",
                    "atomic_semantic_fidelity": 1.0,
                    "clarification_identity": 1.0,
                    "unnecessary_question_rate_ceiling": 0.0,
                    "overall_case_success": 1.0,
                    "worst_slice_success": 1.0,
                },
            }
        ),
        encoding="utf-8",
    )
    return holdout_path, manifest_path


def _semantic_annotation(
    case_id: str,
    prompt: str,
    *,
    edit_evidence: str = "",
    complexity_overrides: dict[str, int] | None = None,
) -> dict[str, object]:
    actor = "Operator"
    evidence = combined_prompt_evidence_source(prompt=prompt, edit_evidence=edit_evidence)
    actor_bytes = actor.encode("utf-8")
    actor_start = evidence.encode("utf-8").index(actor_bytes)
    return {
        "case_id": case_id,
        "split": "final_holdout",
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "expected_outcome": "commit",
        "expected_clarification": None,
        "atoms": [
            {
                "id": "actor-1",
                "category": "actors",
                "evaluation_role": "scored",
                "materiality": "material",
                "expected_custody": "accepted_fact",
                "expected_polarity": "affirmed",
                "source": {
                    "source_id": "operator_evidence",
                    "start_byte": actor_start,
                    "end_byte": actor_start + len(actor_bytes),
                    "quote_sha256": hashlib.sha256(actor_bytes).hexdigest(),
                },
                "projection_links": [
                    {
                        "field": "human_actors",
                        "path": "/human_actors/0",
                        "value_sha256": hashlib.sha256(actor_bytes).hexdigest(),
                        "projection_start_byte": 0,
                        "projection_end_byte": len(actor_bytes),
                        "relation_order": 0,
                        "relation_role": "",
                    }
                ],
            }
        ],
        "complexity": {
            "evidence_bytes": len(evidence.encode("utf-8")),
            "documents": 2 if edit_evidence else 1,
            "actors": 1,
            "state_objects": 1,
            "paths": 1,
            "external_systems": 0,
            "internal_systems": 0,
            "contradictions": 0,
            "ambiguities": 0,
            "safety_boundaries": 0,
            "success_metrics": 0,
            "evidence_requirements": 0,
            "component_responsibilities": 0,
            "assumptions": 0,
            "non_goals": 0,
            **dict(complexity_overrides or {}),
        },
    }
