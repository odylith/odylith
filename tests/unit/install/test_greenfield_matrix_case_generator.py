from __future__ import annotations

import importlib.util
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
        SCRIPTS_ROOT / "greenfield_matrix_case_generator.py",
        "greenfield_matrix_case_generator_test",
    )


def _case_file_module():
    return _load_module(
        SCRIPTS_ROOT / "greenfield_matrix_case_file.py",
        "greenfield_matrix_case_file_generator_test",
    )


def _write_pool(path: Path) -> None:
    taxonomy = (
        ("modal-expert-lens", "alpha tribunal"),
        ("path-grant", "beta grant"),
        ("noun-verb-homonym", "gamma record"),
        ("scientific-casing", "delta assay"),
        ("multi-role-tribunal", "epsilon council"),
        ("long-first-path", "zeta sequence"),
        ("domain-depth-obligations", "eta proof"),
        ("final-memory-pressure", "theta memory"),
        ("atlas-label-pressure", "iota diagram"),
        ("registry-contract-pressure", "kappa contract"),
        ("latency-pressure", "lambda timing"),
    )
    rows = []
    for index, (stressor, phrase) in enumerate(taxonomy, start=1):
        rows.append(
            {
                "case_id": f"seed-{index:03d}",
                "name": f"{phrase} review",
                "prompt": (
                    f"Create a greenfield proposal for {phrase} review where operators capture source evidence, "
                    "coordinate accountable review, preserve a first complete path, publish governed proof, and "
                    "keep implementation prompts accurate for the first release."
                ),
                "required_terms": phrase.split(),
                "leakage_terms": (phrase,),
                "tags": (f"group-{index % 3}",),
                "stressors": (stressor, "latency-pressure") if stressor != "latency-pressure" else (stressor,),
                "confirmed_intent_markdown": (
                    f"# {phrase.title()} Review\n\n"
                    "## Product story\nOperators coordinate evidence and review.\n\n"
                    "## First complete path\nOpen the workspace, capture evidence, review the decision, and publish proof.\n\n"
                    "## Proof boundary\nGoverned evidence and readable artifacts."
                ),
            }
        )
    path.write_text(json.dumps({"cases": rows}), encoding="utf-8")


def test_case_generator_requires_external_source_pool(tmp_path: Path) -> None:
    module = _module()

    try:
        module.generate_case_file(
            source_case_files=(),
            output_json=tmp_path / "generated.json",
            target_count=3,
        )
    except RuntimeError as exc:
        assert "requires at least one external source case" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected missing source pool to fail")


def test_case_generator_writes_source_grounded_stratified_case_file(tmp_path: Path) -> None:
    module = _module()
    case_file = _case_file_module()
    source = tmp_path / "source-cases.json"
    output = tmp_path / "generated-cases.json"
    _write_pool(source)

    payload = module.generate_case_file(
        source_case_files=(source,),
        output_json=output,
        target_count=8,
        required_stressors=("modal-expert-lens", "path-grant", "atlas-label-pressure"),
        min_variance_score=6,
    )

    generated = json.loads(output.read_text(encoding="utf-8"))
    loaded = case_file.load_case_file(output)
    covered = {stressor for case in loaded for stressor in case.stressors}

    assert payload["version"] == "odylith.greenfield.matrix.case-generator.v1"
    assert generated["generator_version"] == payload["version"]
    assert generated["case_count"] == 8
    assert generated["selection_strategy"] == "balanced-missing-rare-stressor-max-coverage"
    assert generated["source_stratification"]["tag_counts"]["group-0"] > 0
    assert generated["evaluation"]["stratification"]["case_count"] == 8
    assert generated["evaluation"]["stratification"]["stressor_counts"]["latency-pressure"] > 0
    assert {"modal-expert-lens", "path-grant", "atlas-label-pressure"} <= covered
    assert all(case.required_terms for case in loaded)
    assert all(case.leakage_terms for case in loaded)
    assert payload["status"] in {"passed", "warning"}
    warnings = " ".join(payload["evaluation"]["warnings"])
    assert "120-case discovery proof needs at least 120" in warnings
    assert "240-case discovery proof needs at least 240" in warnings


def test_case_generator_fails_when_required_stressor_is_absent(tmp_path: Path) -> None:
    module = _module()
    source = tmp_path / "source-cases.json"
    _write_pool(source)

    try:
        module.generate_case_file(
            source_case_files=(source,),
            output_json=tmp_path / "generated.json",
            target_count=6,
            required_stressors=("missing-stressor",),
        )
    except RuntimeError as exc:
        assert "missing-stressor" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected missing stressor to fail")


def test_case_generator_warns_or_fails_for_thin_deep_stressor_cases(tmp_path: Path) -> None:
    module = _module()
    source = tmp_path / "thin.json"
    source.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "thin-001",
                        "name": "thin assay",
                        "prompt": "Create assay review.",
                        "required_terms": ("assay", "review"),
                        "leakage_terms": ("assay review",),
                        "stressors": ("scientific-casing",),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = module.generate_case_file(
        source_case_files=(source,),
        output_json=tmp_path / "generated.json",
        target_count=1,
        required_stressors=("scientific-casing",),
        min_variance_score=0,
        min_stressor_density=0.0,
    )

    assert payload["status"] == "warning"
    assert "declares deep stressors" in " ".join(payload["evaluation"]["warnings"])
    try:
        module.generate_case_file(
            source_case_files=(source,),
            output_json=tmp_path / "strict.json",
            target_count=1,
            required_stressors=("scientific-casing",),
            min_variance_score=0,
            min_stressor_density=0.0,
            fail_on_warnings=True,
        )
    except RuntimeError as exc:
        assert "declares deep stressors" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected strict warnings to fail")


def test_case_generator_selects_rare_required_stressor_before_common_cases(tmp_path: Path) -> None:
    module = _module()
    source = tmp_path / "rare.json"
    rows = [
        {
            "case_id": f"common-{index}",
            "name": f"common alpha {index}",
            "prompt": f"Create alpha review {index} with accountable proof and governed records.",
            "required_terms": ("alpha", "review"),
            "leakage_terms": ("alpha review",),
            "stressors": ("modal-expert-lens",),
        }
        for index in range(5)
    ]
    rows.append(
        {
            "case_id": "rare-001",
            "name": "rare atlas",
            "prompt": "Create rare atlas review with accountable proof and governed records.",
            "required_terms": ("rare", "atlas"),
            "leakage_terms": ("rare atlas",),
            "stressors": ("atlas-label-pressure",),
        }
    )
    source.write_text(json.dumps({"cases": rows}), encoding="utf-8")

    payload = module.generate_case_file(
        source_case_files=(source,),
        output_json=tmp_path / "generated.json",
        target_count=2,
        required_stressors=("atlas-label-pressure",),
        min_variance_score=0,
        min_stressor_density=0.0,
    )
    selected_names = [case["name"] for case in json.loads(Path(payload["output_json"]).read_text())["cases"]]

    assert "rare atlas" in selected_names


def test_case_generator_requires_explicit_input_styles_and_complete_metamorphic_pairs(tmp_path: Path) -> None:
    module = _module()
    case_file = _case_file_module()
    source = tmp_path / "axis-cases.json"
    source.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "intake-direct",
                        "name": "intake review direct request",
                        "prompt": (
                            "Create a greenfield proposal for an intake review workspace that records source "
                            "evidence and publishes a review proof."
                        ),
                        "required_terms": ("intake", "evidence"),
                        "leakage_terms": ("intake review",),
                        "input_style": "direct_request",
                        "metamorphic_group": "intake_review",
                        "metamorphic_transform": "direct_prompt",
                    },
                    {
                        "case_id": "intake-brief",
                        "name": "intake review pasted brief",
                        "prompt": (
                            "Product brief: create an intake review workspace that records source evidence "
                            "and publishes a review proof."
                        ),
                        "required_terms": ("intake", "evidence"),
                        "leakage_terms": ("intake review",),
                        "input_style": "pasted_brief",
                        "metamorphic_group": "intake_review",
                        "metamorphic_transform": "brief_format",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = module.generate_case_file(
        source_case_files=(source,),
        output_json=tmp_path / "generated.json",
        target_count=2,
        required_input_styles=("direct_request", "pasted_brief"),
        min_cases_per_input_style=1,
        min_metamorphic_groups=1,
        min_variance_score=0,
        min_stressor_density=0.0,
    )
    loaded = case_file.load_case_file(Path(payload["output_json"]))

    assert payload["evaluation"]["input_style_counts"] == {
        "direct_request": 1,
        "pasted_brief": 1,
    }
    assert payload["evaluation"]["metamorphic_group_transforms"] == {
        "intake_review": ["brief_format", "direct_prompt"]
    }
    assert all(case.input_style_declared for case in loaded)
    assert {case.metamorphic_transform for case in loaded} == {"brief_format", "direct_prompt"}


def test_case_generator_rejects_implicit_default_style_for_required_axis(tmp_path: Path) -> None:
    module = _module()
    source = tmp_path / "legacy-cases.json"
    _write_pool(source)

    try:
        module.generate_case_file(
            source_case_files=(source,),
            output_json=tmp_path / "generated.json",
            target_count=4,
            required_input_styles=("direct_request",),
            min_variance_score=0,
            min_stressor_density=0.0,
        )
    except RuntimeError as exc:
        assert "input styles" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected implicit input style to fail the required axis")


def test_case_loader_rejects_invalid_or_incomplete_axis_metadata(tmp_path: Path) -> None:
    case_file = _case_file_module()
    source = tmp_path / "invalid-axis-cases.json"
    source.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "invalid axis case",
                        "prompt": "Create an invalid axis evidence review.",
                        "required_terms": ("axis", "evidence"),
                        "leakage_terms": ("axis evidence",),
                        "input_style": "freeform_chat",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    try:
        case_file.load_case_file(source)
    except RuntimeError as exc:
        assert "invalid matrix axis metadata" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected invalid input_style to fail")

    source.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "incomplete pair case",
                        "prompt": "Create an incomplete pair evidence review.",
                        "required_terms": ("pair", "evidence"),
                        "leakage_terms": ("pair evidence",),
                        "metamorphic_group": "incomplete_pair",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    try:
        case_file.load_case_file(source)
    except RuntimeError as exc:
        assert "both metamorphic_group and metamorphic_transform" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected incomplete metamorphic pair to fail")
