from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
from pathlib import Path


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
        SCRIPTS_ROOT / "greenfield_matrix_shards.py",
        "greenfield_matrix_shards_test",
    )


def _write_cases(path: Path) -> None:
    rows = []
    for index, stressors in enumerate(
        (
            ("modal-expert-lens", "scientific-casing"),
            ("path-grant",),
            ("noun-verb-homonym",),
            ("long-first-path", "latency-pressure"),
            ("atlas-label-pressure",),
            ("registry-contract-pressure",),
            ("domain-depth-obligations",),
            ("final-memory-pressure",),
        ),
        start=1,
    ):
        rows.append(
            {
                "case_id": f"case-{index:03d}",
                "name": f"case {index} evidence review",
                "prompt": f"Create a greenfield proposal for case {index} evidence review.",
                "required_terms": ("case", "evidence"),
                "leakage_terms": (f"case {index} evidence review",),
                "tags": ("test",),
                "stressors": stressors,
                "confirmed_intent_markdown": f"# Case {index}\n\nProof boundary: evidence review.",
            }
        )
    path.write_text(json.dumps({"cases": rows}), encoding="utf-8")


def test_shard_builder_writes_stratified_tier_files_and_campaign_env(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "cases.json"
    _write_cases(case_file)

    payload = module.build_shards(
        case_files=(case_file,),
        output_dir=tmp_path / "shards",
        shard_size=3,
        regression_size=5,
        volume_size=7,
        deep_volume_size=8,
        release_size=4,
        required_stressors=("modal-expert-lens", "path-grant", "atlas-label-pressure"),
    )

    assert payload["version"] == "odylith.greenfield.matrix.shards.v1"
    assert payload["tiers"]["60-case-regression"]["case_count"] == 5
    assert payload["tiers"]["volume-discovery"]["shard_count"] == 3
    assert payload["tiers"]["240-case-discovery"]["shard_count"] == 3
    assert payload["tiers"]["release-proof"]["shard_count"] == 1
    assert payload["source_variance_evaluation"]["status"] == "passed"
    assert payload["source_variance_evaluation"]["score"] >= 8
    assert payload["source_case_stratification"]["tag_counts"]["test"] == 8
    assert payload["tiers"]["volume-discovery"]["case_stratification"]["stressor_counts"]["atlas-label-pressure"] == 1
    assert payload["tiers"]["60-case-regression"]["variance_evaluation"]["required_coverage_ratio"] == 1.0
    assert payload["tiers"]["60-case-regression"]["variance_evaluation"]["stressor_density"] >= 1.0
    assert payload["campaign_env"]["GREENFIELD_MATRIX_VOLUME_CASE_FILES"]
    assert payload["campaign_env"]["GREENFIELD_MATRIX_DEEP_VOLUME_CASE_FILES"]
    first_regression = Path(payload["tiers"]["60-case-regression"]["files"][0])
    loaded = module.load_case_file(first_regression)
    covered = {stressor for case in loaded for stressor in case.stressors}
    assert {"modal-expert-lens", "path-grant", "atlas-label-pressure"} <= covered
    assert loaded[0].confirmed_intent_markdown.startswith("# Case")


def test_shard_builder_extracts_failed_subset_from_matrix_and_campaign_payloads(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "cases.json"
    _write_cases(case_file)
    matrix_result = tmp_path / "matrix-result.json"
    campaign_result = tmp_path / "campaign-result.json"
    matrix_result.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "name": "renamed failed case",
                        "status": "failed",
                        "evidence": {"case": {"id": "case-002", "prompt_sha256": "unused"}},
                    },
                    {"name": "case 3 evidence review", "status": "passed", "quality": {"passed": True}},
                ]
            }
        ),
        encoding="utf-8",
    )
    campaign_result.write_text(
        json.dumps(
            {
                "failure_clusters": [
                    {"cluster": "manifest.generated-copy-quality", "case_ids": ["case-007"]}
                ],
                "tiers": [
                    {
                        "shards": [
                            {
                                "failure_clusters": [
                                    {"cluster": "scores.copy", "case_ids": ["case-005"]}
                                ]
                            }
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = module.build_shards(
        case_files=(case_file,),
        output_dir=tmp_path / "shards",
        failed_result_jsons=(matrix_result, campaign_result),
        shard_size=10,
        regression_size=8,
        volume_size=8,
        deep_volume_size=8,
        release_size=8,
    )

    failed_files = payload["tiers"]["failed-subset"]["files"]
    assert len(failed_files) == 1
    failed_names = [case.name for case in module.load_case_file(Path(failed_files[0]))]
    assert failed_names == [
        "case 2 evidence review",
        "case 5 evidence review",
        "case 7 evidence review",
    ]


def test_shard_builder_can_emit_only_failed_subset_replay_tier(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "cases.json"
    _write_cases(case_file)
    failed_result = tmp_path / "failed.json"
    failed_result.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "name": "case 4 evidence review",
                        "status": "failed",
                        "evidence": {"case": {"id": "case-004"}},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = module.build_shards(
        case_files=(case_file,),
        output_dir=tmp_path / "failed-subset-only",
        failed_result_jsons=(failed_result,),
        failed_subset_only=True,
    )

    assert payload["failed_subset_only"] is True
    assert list(payload["tiers"]) == ["failed-subset"]
    assert payload["tiers"]["failed-subset"]["case_count"] == 1
    assert payload["campaign_env"]["GREENFIELD_MATRIX_FAILED_CASE_FILES"]
    assert "GREENFIELD_MATRIX_VOLUME_CASE_FILES" not in payload["campaign_env"]


def test_shard_builder_uses_content_identity_for_duplicate_names_without_case_ids(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "cases.json"
    prompts = (
        "Create a greenfield proposal for alpha review with source packet one.",
        "Create a greenfield proposal for alpha review with source packet two.",
    )
    rows = [
        {
            "name": "alpha review",
            "prompt": prompt,
            "required_terms": ("alpha", "review"),
            "leakage_terms": ("alpha review",),
            "stressors": ("modal-expert-lens",),
        }
        for prompt in prompts
    ]
    case_file.write_text(json.dumps({"cases": rows}), encoding="utf-8")
    failed_result = tmp_path / "failed.json"
    failed_result.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "name": "alpha review",
                        "status": "failed",
                        "evidence": {
                            "case": {
                                "name": "alpha review",
                                "prompt_sha256": hashlib.sha256(prompts[1].encode("utf-8")).hexdigest(),
                            }
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = module.build_shards(
        case_files=(case_file,),
        output_dir=tmp_path / "shards",
        failed_result_jsons=(failed_result,),
        shard_size=10,
        regression_size=2,
        volume_size=2,
        deep_volume_size=2,
        release_size=2,
    )

    assert payload["source_case_count"] == 2
    failed_files = payload["tiers"]["failed-subset"]["files"]
    assert len(failed_files) == 1
    failed_cases = module.load_case_file(Path(failed_files[0]))
    assert [case.prompt for case in failed_cases] == [prompts[1]]


def test_shard_builder_matches_cluster_only_case_names_without_case_ids(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "cases.json"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "alpha review",
                        "prompt": "Create a greenfield proposal for alpha review.",
                        "required_terms": ("alpha", "review"),
                        "leakage_terms": ("alpha review",),
                        "stressors": ("modal-expert-lens",),
                    },
                    {
                        "name": "beta review",
                        "prompt": "Create a greenfield proposal for beta review.",
                        "required_terms": ("beta", "review"),
                        "leakage_terms": ("beta review",),
                        "stressors": ("path-grant",),
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    failed_result = tmp_path / "failed.json"
    failed_result.write_text(
        json.dumps({"failure_clusters": [{"cluster": "generated-copy", "cases": ["alpha review"]}]}),
        encoding="utf-8",
    )

    payload = module.build_shards(
        case_files=(case_file,),
        output_dir=tmp_path / "shards",
        failed_result_jsons=(failed_result,),
        shard_size=10,
        regression_size=2,
        volume_size=2,
        deep_volume_size=2,
        release_size=2,
    )

    failed_files = payload["tiers"]["failed-subset"]["files"]
    assert len(failed_files) == 1
    failed_cases = module.load_case_file(Path(failed_files[0]))
    assert [case.name for case in failed_cases] == ["alpha review"]


def test_shard_builder_does_not_overselect_duplicate_name_cluster_only_failures(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "cases.json"
    prompts = (
        "Create a greenfield proposal for alpha review with source packet one.",
        "Create a greenfield proposal for alpha review with source packet two.",
    )
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "alpha review",
                        "prompt": prompt,
                        "required_terms": ("alpha", "review"),
                        "leakage_terms": ("alpha review",),
                        "stressors": ("modal-expert-lens",),
                    }
                    for prompt in prompts
                ]
            }
        ),
        encoding="utf-8",
    )
    failed_result = tmp_path / "failed.json"
    failed_result.write_text(
        json.dumps({"failure_clusters": [{"cluster": "generated-copy", "cases": ["alpha review"]}]}),
        encoding="utf-8",
    )

    payload = module.build_shards(
        case_files=(case_file,),
        output_dir=tmp_path / "shards",
        failed_result_jsons=(failed_result,),
        shard_size=10,
        regression_size=2,
        volume_size=2,
        deep_volume_size=2,
        release_size=2,
    )

    assert payload["tiers"]["failed-subset"]["case_count"] == 0
    assert payload["tiers"]["failed-subset"]["files"] == []
    assert "alpha-review" in payload["failed_case_identity_classes"]["weak_ambiguous"]


def test_shard_builder_fails_default_60_120_240_labels_on_undersized_source_pool(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "cases.json"
    _write_cases(case_file)

    try:
        module.build_shards(
            case_files=(case_file,),
            output_dir=tmp_path / "shards",
        )
    except RuntimeError as exc:
        message = str(exc)
        assert "60-case-regression requires 60 case(s), source pool has 8" in message
        assert "volume-discovery requires 120 case(s), source pool has 8" in message
        assert "240-case-discovery requires 240 case(s), source pool has 8" in message
    else:
        raise AssertionError("default tier labels must not silently downsize an undersized source pool")


def test_shard_builder_rejects_missing_required_stressor_before_volume_run(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "cases.json"
    _write_cases(case_file)

    try:
            module.build_shards(
                case_files=(case_file,),
                output_dir=tmp_path / "shards",
                regression_size=8,
                volume_size=8,
                deep_volume_size=8,
                release_size=8,
                required_stressors=("not-present",),
            )
    except RuntimeError as exc:
        assert "does not cover required stressor classes: not-present" in str(exc)
    else:
        raise AssertionError("missing stressor should fail before shard output")


def test_shard_builder_rejects_ungrounded_required_terms_before_writing_shards(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "cases.json"
    output_dir = tmp_path / "shards"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "restaurant-reinspection",
                        "name": "restaurant health reinspection",
                        "prompt": "Create a greenfield proposal for restaurant health reinspection.",
                        "required_terms": ("restaurant", "inspection"),
                        "leakage_terms": ("restaurant health reinspection",),
                        "stressors": ("semantic-grounding", "domain-variance"),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    try:
        module.build_shards(
            case_files=(case_file,),
            output_dir=output_dir,
            regression_size=1,
            volume_size=1,
            deep_volume_size=1,
            release_size=1,
        )
    except RuntimeError as exc:
        message = str(exc)
        assert "restaurant health reinspection" in message
        assert "ungrounded required_terms: inspection" in message
    else:
        raise AssertionError("ungrounded required_terms should fail before shard output")

    assert not output_dir.exists()


def test_load_case_file_rejects_required_term_hidden_inside_prefixed_token(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "cases.json"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "restaurant health reinspection",
                        "prompt": "Create a greenfield proposal for restaurant health reinspection.",
                        "required_terms": ("inspection",),
                        "leakage_terms": ("restaurant health reinspection",),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    try:
        module.load_case_file(case_file)
    except RuntimeError as exc:
        assert "ungrounded required_terms: inspection" in str(exc)
    else:
        raise AssertionError("prefixed source token must not ground a shorter required term")


def test_load_case_file_rejects_ungrounded_leakage_terms_before_simulation(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "cases.json"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "quantum communication lab",
                        "prompt": (
                            "Create a greenfield proposal for a quantum communication lab with Bell inequality "
                            "checks and QBER threshold review."
                        ),
                        "required_terms": ("quantum", "qber"),
                        "leakage_terms": ("court interpreter",),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    try:
        module.load_case_file(case_file)
    except RuntimeError as exc:
        message = str(exc)
        assert "quantum communication lab" in message
        assert "ungrounded leakage_terms: court interpreter" in message
    else:
        raise AssertionError("stale leakage sentinel must not mask source-domain vocabulary")


def test_shard_builder_accepts_reinspection_when_required_term_matches_source_token(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "cases.json"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "restaurant-reinspection",
                        "name": "restaurant health reinspection",
                        "prompt": "Create a greenfield proposal for restaurant health reinspection.",
                        "required_terms": ("restaurant", "reinspection"),
                        "leakage_terms": ("restaurant health reinspection",),
                        "stressors": ("semantic-grounding", "domain-variance"),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = module.build_shards(
        case_files=(case_file,),
        output_dir=tmp_path / "shards",
        shard_size=10,
        regression_size=1,
        volume_size=1,
        deep_volume_size=1,
        release_size=1,
    )
    loaded = module.load_case_file(Path(payload["tiers"]["volume-discovery"]["files"][0]))

    assert payload["source_case_count"] == 1
    assert loaded[0].required_terms == ("restaurant", "reinspection")
