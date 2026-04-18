from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


CHECK_ID = "guidance_behavior_benchmark_family"


def _read_json_object(path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    if not path.is_file():
        return {}, [
            {
                "check_id": CHECK_ID,
                "message": f"required benchmark corpus is missing: {path}",
                "path": str(path),
            }
        ]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [
            {
                "check_id": CHECK_ID,
                "message": f"benchmark corpus is not valid JSON: {exc}",
                "path": str(path),
            }
        ]
    if not isinstance(payload, dict):
        return {}, [
            {
                "check_id": CHECK_ID,
                "message": "benchmark corpus must be a JSON object",
                "path": str(path),
            }
        ]
    return payload, []


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(token).strip() for token in value if str(token).strip()]


def _failure(message: str, *, path: Path, case_id: str = "") -> dict[str, str]:
    payload = {"check_id": CHECK_ID, "message": message, "path": str(path)}
    if case_id:
        payload["case_id"] = case_id
    return payload


def validate_benchmark_family_integration(
    *,
    repo_root: Path,
    cases: Sequence[Mapping[str, Any]],
    expected_family: str,
    corpus_relative_path: Path,
    benchmark_corpus_relative_path: Path,
    bundle_benchmark_corpus_relative_path: Path,
) -> dict[str, Any]:
    benchmark_path = repo_root / benchmark_corpus_relative_path
    benchmark_mirror_path = repo_root / bundle_benchmark_corpus_relative_path
    failures: list[dict[str, str]] = []
    benchmark, read_failures = _read_json_object(benchmark_path)
    failures.extend(read_failures)
    if failures:
        return {"id": CHECK_ID, "status": "failed", "evidence": [], "failures": failures}

    if not benchmark_mirror_path.is_file():
        failures.append(
            _failure(
                "benchmark corpus bundle mirror is missing",
                path=bundle_benchmark_corpus_relative_path,
            )
        )
    elif benchmark_path.read_text(encoding="utf-8") != benchmark_mirror_path.read_text(encoding="utf-8"):
        failures.append(
            _failure(
                "benchmark corpus bundle mirror is stale",
                path=bundle_benchmark_corpus_relative_path,
            )
        )

    scenarios = benchmark.get("scenarios", [])
    if not isinstance(scenarios, list):
        failures.append(_failure("benchmark corpus must contain a `scenarios` list", path=benchmark_corpus_relative_path))
        scenarios = []
    by_id = {
        str(scenario.get("case_id", "")).strip(): dict(scenario)
        for scenario in scenarios
        if isinstance(scenario, Mapping) and str(scenario.get("case_id", "")).strip()
    }
    for case in cases:
        case_id = str(case.get("id", "")).strip()
        scenario = by_id.get(case_id)
        if scenario is None:
            failures.append(
                _failure(
                    f"benchmark corpus is missing guidance behavior scenario `{case_id}`",
                    path=benchmark_corpus_relative_path,
                    case_id=case_id,
                )
            )
            continue
        if str(scenario.get("family", "")).strip() != expected_family:
            failures.append(
                _failure(
                    f"benchmark scenario `{case_id}` must use family `{expected_family}`",
                    path=benchmark_corpus_relative_path,
                    case_id=case_id,
                )
            )
        benchmark_spec = scenario.get("benchmark", {})
        benchmark_spec = dict(benchmark_spec) if isinstance(benchmark_spec, Mapping) else {}
        validation_commands = _string_list(benchmark_spec.get("validation_commands"))
        required_paths = _string_list(benchmark_spec.get("required_paths"))
        critical_paths = _string_list(benchmark_spec.get("critical_paths"))
        required_path_set = set(required_paths)
        if not validation_commands:
            failures.append(
                _failure(
                    f"benchmark scenario `{case_id}` must carry a validator command",
                    path=benchmark_corpus_relative_path,
                    case_id=case_id,
                )
            )
        elif not any(f"--case-id {case_id}" in command for command in validation_commands):
            failures.append(
                _failure(
                    f"benchmark scenario `{case_id}` validator command must stay case-scoped",
                    path=benchmark_corpus_relative_path,
                    case_id=case_id,
                )
            )
        if not required_paths:
            failures.append(
                _failure(
                    f"benchmark scenario `{case_id}` must carry required paths",
                    path=benchmark_corpus_relative_path,
                    case_id=case_id,
                )
            )
        if not critical_paths:
            failures.append(
                _failure(
                    f"benchmark scenario `{case_id}` must carry critical paths",
                    path=benchmark_corpus_relative_path,
                    case_id=case_id,
                )
            )
        missing_refs = [
            str(ref).strip()
            for ref in case.get("related_guidance_refs", [])
            if str(ref).strip() and str(ref).strip() not in required_path_set
        ]
        if missing_refs:
            failures.append(
                _failure(
                    f"benchmark scenario `{case_id}` is missing related guidance path(s): {', '.join(missing_refs)}",
                    path=benchmark_corpus_relative_path,
                    case_id=case_id,
                )
            )
        if str(corpus_relative_path) not in required_path_set:
            failures.append(
                _failure(
                    f"benchmark scenario `{case_id}` must include the guidance behavior corpus as required evidence",
                    path=benchmark_corpus_relative_path,
                    case_id=case_id,
                )
            )
    return {
        "id": CHECK_ID,
        "status": "passed" if not failures else "failed",
        "evidence": [str(benchmark_corpus_relative_path)] if not failures else [],
        "failures": failures,
    }


__all__ = ["CHECK_ID", "validate_benchmark_family_integration"]
