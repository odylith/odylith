"""Source-grounded case generation for high-variance Greenfield matrix runs."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from greenfield_matrix_case_file import load_case_file  # noqa: E402
from greenfield_matrix_stressors import DEFAULT_HIGH_VARIANCE_STRESSORS  # noqa: E402
from greenfield_matrix_stressors import case_stratification  # noqa: E402
from greenfield_matrix_stressors import case_stressors  # noqa: E402
from greenfield_matrix_stressors import missing_required_stressors  # noqa: E402
from greenfield_matrix_stressors import required_stressors_from_values  # noqa: E402
from greenfield_matrix_stressors import stressor_coverage  # noqa: E402
from greenfield_matrix_stressors import variance_evaluation  # noqa: E402
from greenfield_post_confirm_matrix_cases import GreenfieldMatrixCase  # noqa: E402


CASE_GENERATOR_VERSION = "odylith.greenfield.matrix.case-generator.v1"
CASE_FILE_VERSION = "odylith.greenfield.matrix.case-file.v1"
DEFAULT_TARGET_COUNT = 60
DEFAULT_VOLUME_TARGET_COUNT = 120
DEFAULT_DEEP_VOLUME_TARGET_COUNT = 240
DEFAULT_MIN_STRESSOR_DENSITY = 2.0
DEPTH_PRESSURE_STRESSORS = frozenset(
    {
        "domain-depth-obligations",
        "scientific-casing",
        "multi-role-tribunal",
        "long-first-path",
    }
)


@dataclass(frozen=True)
class CasePoolEvaluation:
    status: str
    score: int
    selected_case_count: int
    source_case_count: int
    required_stressors: tuple[str, ...]
    coverage: Mapping[str, Any]
    variance: Mapping[str, Any]
    stratification: Mapping[str, Any]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "score": self.score,
            "selected_case_count": self.selected_case_count,
            "source_case_count": self.source_case_count,
            "required_stressors": list(self.required_stressors),
            "coverage": dict(self.coverage),
            "variance": dict(self.variance),
            "stratification": dict(self.stratification),
            "warnings": list(self.warnings),
        }


def generate_case_file(
    *,
    source_case_files: Sequence[Path],
    output_json: Path,
    target_count: int = DEFAULT_TARGET_COUNT,
    required_stressors: Sequence[str] = (),
    min_variance_score: int = 10,
    min_stressor_density: float = DEFAULT_MIN_STRESSOR_DENSITY,
    fail_on_warnings: bool = False,
) -> dict[str, Any]:
    """Write a stratified external case file for campaign shards.

    The generator intentionally has no built-in domains. It selects from
    host-authored or external seed files and preserves their declared intent.
    """

    source_cases = _dedupe_cases(_load_cases(source_case_files))
    if not source_cases:
        raise RuntimeError("greenfield case generator requires at least one external source case")
    required = required_stressors_from_values(required_stressors)
    selected = _balanced_select(
        source_cases,
        target_count=_bounded_target(target_count, len(source_cases)),
        required_stressors=required,
    )
    evaluation = evaluate_case_pool(
        source_cases=source_cases,
        selected_cases=selected,
        required_stressors=required,
        min_variance_score=min_variance_score,
        min_stressor_density=min_stressor_density,
    )
    if evaluation.status == "failed" or (fail_on_warnings and evaluation.status == "warning"):
        raise RuntimeError(_evaluation_error(evaluation))
    output_path = Path(output_json).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": CASE_FILE_VERSION,
        "generator_version": CASE_GENERATOR_VERSION,
        "source_case_files": [str(Path(path).expanduser().resolve()) for path in source_case_files],
        "target_count": int(_bounded_target(target_count, len(source_cases))),
        "case_count": len(selected),
        "required_stressors": list(required),
        "selection_strategy": "balanced-missing-rare-stressor-max-coverage",
        "source_stratification": case_stratification(source_cases),
        "evaluation": evaluation.to_dict(),
        "cases": [_case_to_dict(case) for case in selected],
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "version": CASE_GENERATOR_VERSION,
        "status": evaluation.status,
        "output_json": str(output_path),
        "source_case_count": len(source_cases),
        "selected_case_count": len(selected),
        "required_stressors": list(required),
        "evaluation": evaluation.to_dict(),
        "campaign_next_steps": [
            "Build failed-subset, 60-case, 120-case, 240-case, and release shards from output_json.",
            "Run discovery tiers with stop-after-cluster thresholds before release proof.",
            "Run release proof separately with full install, browser proof, and natural rescue proof.",
        ],
    }


def evaluate_case_pool(
    *,
    source_cases: Sequence[GreenfieldMatrixCase],
    selected_cases: Sequence[GreenfieldMatrixCase],
    required_stressors: Sequence[str],
    min_variance_score: int,
    min_stressor_density: float,
) -> CasePoolEvaluation:
    coverage = stressor_coverage(selected_cases, required_stressors)
    variance = variance_evaluation(selected_cases, required_stressors)
    stratification = case_stratification(selected_cases)
    warnings = _case_pool_warnings(
        source_cases=source_cases,
        selected_cases=selected_cases,
        coverage=coverage,
        variance=variance,
        min_variance_score=max(0, int(min_variance_score)),
        min_stressor_density=max(0.0, float(min_stressor_density)),
    )
    blocking = missing_required_stressors(selected_cases, required_stressors)
    status = "failed" if blocking else "warning" if warnings else "passed"
    return CasePoolEvaluation(
        status=status,
        score=int(variance.get("score") or 0),
        selected_case_count=len(selected_cases),
        source_case_count=len(source_cases),
        required_stressors=tuple(required_stressors),
        coverage=coverage,
        variance=variance,
        stratification=stratification,
        warnings=warnings,
    )


def _balanced_select(
    cases: Sequence[GreenfieldMatrixCase],
    *,
    target_count: int,
    required_stressors: Sequence[str],
) -> tuple[GreenfieldMatrixCase, ...]:
    target = max(0, min(int(target_count), len(cases)))
    if target <= 0:
        return ()
    required = tuple(required_stressors)
    remaining = sorted(cases, key=_case_identity)
    selected: list[GreenfieldMatrixCase] = []
    selected_keys: set[str] = set()
    stressor_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()

    while len(selected) < target and remaining:
        case = max(
            remaining,
            key=lambda candidate: _selection_score(
                candidate,
                required_stressors=required,
                stressor_counts=stressor_counts,
                tag_counts=tag_counts,
                source_counts=source_counts,
                selected_count=len(selected),
            ),
        )
        key = _case_identity(case)
        remaining = [candidate for candidate in remaining if _case_identity(candidate) != key]
        if key in selected_keys:
            continue
        selected.append(case)
        selected_keys.add(key)
        for stressor in case_stressors(case):
            stressor_counts[stressor] += 1
        for tag in _case_tags(case):
            tag_counts[tag] += 1
        source = str(getattr(case, "source_file", "") or "")
        if source:
            source_counts[source] += 1
    return tuple(selected)


def _selection_score(
    case: GreenfieldMatrixCase,
    *,
    required_stressors: Sequence[str],
    stressor_counts: Counter[str],
    tag_counts: Counter[str],
    source_counts: Counter[str],
    selected_count: int,
) -> tuple[float, int, str]:
    stressors = case_stressors(case)
    required_missing = sum(1 for stressor in stressors if stressor in required_stressors and stressor_counts[stressor] <= 0)
    rare_stressor_gain = sum(1.0 / float(stressor_counts[stressor] + 1) for stressor in stressors)
    tag_gain = sum(1.0 / float(tag_counts[tag] + 1) for tag in _case_tags(case))
    source = str(getattr(case, "source_file", "") or "")
    source_gain = 1.0 / float(source_counts[source] + 1) if source else 0.0
    depth_gain = min(len(stressors), 5) / 5.0
    if selected_count == 0:
        required_missing += 1 if any(stressor in required_stressors for stressor in stressors) else 0
    score = (required_missing * 8.0) + (rare_stressor_gain * 3.0) + tag_gain + source_gain + depth_gain
    return (score, len(stressors), _case_identity(case))


def _case_pool_warnings(
    *,
    source_cases: Sequence[GreenfieldMatrixCase],
    selected_cases: Sequence[GreenfieldMatrixCase],
    coverage: Mapping[str, Any],
    variance: Mapping[str, Any],
    min_variance_score: int,
    min_stressor_density: float,
) -> tuple[str, ...]:
    warnings: list[str] = []
    if not selected_cases:
        warnings.append("no cases were selected")
    missing = tuple(str(item) for item in coverage.get("missing_required", ()) if str(item).strip())
    if missing:
        warnings.append("selected case set is missing required stressors: " + ", ".join(missing))
    if int(variance.get("score") or 0) < min_variance_score:
        warnings.append(
            f"selected case variance score {int(variance.get('score') or 0)}/10 is below required {min_variance_score}/10"
        )
    if float(variance.get("stressor_density") or 0.0) < min_stressor_density:
        warnings.append(
            "selected case stressor density "
            f"{float(variance.get('stressor_density') or 0.0):.3f} is below required {min_stressor_density:.3f}"
        )
    depth_warnings = _depth_pressure_warnings(selected_cases)
    warnings.extend(depth_warnings)
    if len(source_cases) < DEFAULT_TARGET_COUNT:
        warnings.append(
            f"source pool has only {len(source_cases)} case(s); high-volume discovery needs a larger external seed pool"
        )
    if len(source_cases) < DEFAULT_VOLUME_TARGET_COUNT:
        warnings.append(
            f"source pool has only {len(source_cases)} case(s); 120-case discovery proof needs at least {DEFAULT_VOLUME_TARGET_COUNT}"
        )
    if len(source_cases) < DEFAULT_DEEP_VOLUME_TARGET_COUNT:
        warnings.append(
            f"source pool has only {len(source_cases)} case(s); 240-case discovery proof needs at least {DEFAULT_DEEP_VOLUME_TARGET_COUNT}"
        )
    return tuple(dict.fromkeys(warnings))


def _depth_pressure_warnings(cases: Sequence[GreenfieldMatrixCase]) -> tuple[str, ...]:
    warnings: list[str] = []
    for case in cases:
        stressors = set(case_stressors(case))
        if not stressors & DEPTH_PRESSURE_STRESSORS:
            continue
        words = _word_count(" ".join((case.prompt, case.confirmed_intent_markdown)))
        if words < 28:
            warnings.append(
                f"{case.name} declares deep stressors but has only {words} source word(s); "
                "add a richer host-authored intent before using it for premium variance proof"
            )
    return tuple(warnings[:20])


def _has_blocking_evaluation(evaluation: CasePoolEvaluation) -> bool:
    return bool(tuple(evaluation.coverage.get("missing_required", ()) or ())) or evaluation.selected_case_count <= 0


def _evaluation_error(evaluation: CasePoolEvaluation) -> str:
    warnings = "; ".join(evaluation.warnings[:8])
    return "greenfield generated case set failed evaluation" + (f": {warnings}" if warnings else "")


def _load_cases(source_case_files: Sequence[Path]) -> tuple[GreenfieldMatrixCase, ...]:
    cases: list[GreenfieldMatrixCase] = []
    for source in source_case_files:
        token = str(source or "").strip()
        if token:
            cases.extend(load_case_file(Path(token)))
    return tuple(cases)


def _dedupe_cases(cases: Sequence[GreenfieldMatrixCase]) -> tuple[GreenfieldMatrixCase, ...]:
    deduped: list[GreenfieldMatrixCase] = []
    seen: set[str] = set()
    for case in cases:
        key = _case_identity(case)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(case)
    return tuple(deduped)


def _case_to_dict(case: GreenfieldMatrixCase) -> dict[str, Any]:
    row: dict[str, Any] = {
        "name": case.name,
        "prompt": case.prompt,
        "required_terms": list(case.required_terms),
        "leakage_terms": list(case.leakage_terms),
        "tags": list(case.tags),
        "stressors": list(case.stressors),
    }
    if case.case_id:
        row["case_id"] = case.case_id
    if case.confirmed_intent_markdown:
        row["confirmed_intent_markdown"] = case.confirmed_intent_markdown
    return row


def _case_identity(case: GreenfieldMatrixCase) -> str:
    if case.case_id:
        return "case-id:" + _slug(case.case_id)
    prompt_hash = hashlib.sha256(case.prompt.encode("utf-8")).hexdigest() if case.prompt else ""
    return "prompt:" + prompt_hash if prompt_hash else "slug:" + _slug(case.slug or case.name)


def _case_tags(case: GreenfieldMatrixCase) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_slug(tag) for tag in getattr(case, "tags", ()) or () if str(tag).strip()))


def _bounded_target(target_count: int, source_count: int) -> int:
    target = int(target_count or DEFAULT_TARGET_COUNT)
    return max(1, min(target, source_count))


def _word_count(text: str) -> int:
    count = 0
    in_word = False
    for char in str(text or ""):
        if char.isalnum():
            if not in_word:
                count += 1
                in_word = True
        else:
            in_word = False
    return count


def _slug(value: Any) -> str:
    parts: list[str] = []
    last_dash = False
    for char in str(value or "").strip().casefold().replace("_", "-"):
        if char.isalnum():
            parts.append(char)
            last_dash = False
        elif not last_dash:
            parts.append("-")
            last_dash = True
    return "".join(parts).strip("-")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a stratified external greenfield matrix case file.")
    parser.add_argument("--source-case-file", action="append", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--target-count", type=int, default=DEFAULT_TARGET_COUNT)
    parser.add_argument("--min-variance-score", type=int, default=10)
    parser.add_argument("--min-stressor-density", type=float, default=DEFAULT_MIN_STRESSOR_DENSITY)
    parser.add_argument("--require-high-variance-stressors", action="store_true")
    parser.add_argument("--required-stressor", action="append", default=None)
    parser.add_argument("--fail-on-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    required = required_stressors_from_values(
        args.required_stressor or (),
        use_default=bool(args.require_high_variance_stressors),
    )
    payload = generate_case_file(
        source_case_files=tuple(Path(path) for path in args.source_case_file),
        output_json=Path(args.output_json),
        target_count=max(1, int(args.target_count)),
        required_stressors=required,
        min_variance_score=max(0, int(args.min_variance_score)),
        min_stressor_density=max(0.0, float(args.min_stressor_density)),
        fail_on_warnings=bool(args.fail_on_warnings),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if payload["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
