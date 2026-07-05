"""Stressor taxonomy and variance scoring for Greenfield matrix campaigns."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MatrixStressorClass:
    key: str
    axis: str
    pressure: str

    def to_dict(self) -> dict[str, str]:
        return {"key": self.key, "axis": self.axis, "pressure": self.pressure}


MATRIX_STRESSOR_TAXONOMY = (
    MatrixStressorClass(
        "modal-expert-lens",
        "review semantics",
        "Different reviewers must approve different evidence without crossing artifact boundaries.",
    ),
    MatrixStressorClass(
        "path-grant",
        "permissioned flow",
        "The first path includes approval, readiness, exception, or grant-style state changes.",
    ),
    MatrixStressorClass(
        "noun-verb-homonym",
        "word-sense ambiguity",
        "Terms such as record, package, run, release, review, or model can act as nouns or verbs.",
    ),
    MatrixStressorClass(
        "scientific-casing",
        "technical casing",
        "Specialized symbols, protocols, acronyms, units, or scientific names must survive projection.",
    ),
    MatrixStressorClass(
        "multi-role-tribunal",
        "actor disagreement",
        "Multiple actors or institutions need separate responsibilities, approvals, or proof interests.",
    ),
    MatrixStressorClass(
        "long-first-path",
        "sequence pressure",
        "The first complete path is long enough to stress Atlas labels, Registry contracts, and briefs.",
    ),
    MatrixStressorClass(
        "domain-depth-obligations",
        "substance preservation",
        "Artifacts must preserve field-specific proof obligations rather than flattening to generic prose.",
    ),
    MatrixStressorClass(
        "final-memory-pressure",
        "post-confirm custody",
        "Accepted exclusions, assumptions, or proof boundaries must survive final write projection.",
    ),
    MatrixStressorClass(
        "atlas-label-pressure",
        "diagram copy",
        "Atlas labels must stay short, grammatical, non-repetitive, and semantically faithful.",
    ),
    MatrixStressorClass(
        "registry-contract-pressure",
        "component contract clarity",
        "Registry specs must describe ownership, state, events, and proof without clipped noun piles.",
    ),
    MatrixStressorClass(
        "latency-pressure",
        "runtime budget",
        "The case should still complete inside the standard or rescue time budget.",
    ),
)
DEFAULT_HIGH_VARIANCE_STRESSORS = tuple(item.key for item in MATRIX_STRESSOR_TAXONOMY)


def required_stressors_from_values(values: Sequence[str], *, use_default: bool = False) -> tuple[str, ...]:
    items = list(values)
    if use_default:
        items.extend(DEFAULT_HIGH_VARIANCE_STRESSORS)
    return normalize_stressors(items)


def missing_required_stressors(cases: Sequence[Any], required_stressors: Sequence[str]) -> tuple[str, ...]:
    coverage = stressor_coverage(cases, required_stressors)
    return tuple(str(item) for item in coverage.get("missing_required", ()) if str(item).strip())


def stressor_coverage(cases: Sequence[Any], required_stressors: Sequence[str] = ()) -> Mapping[str, Any]:
    required = normalize_stressors(required_stressors)
    counts: Counter[str] = Counter()
    rows: list[Mapping[str, Any]] = []
    for case in cases:
        stressors = case_stressors(case)
        for stressor in stressors:
            counts[stressor] += 1
        rows.append(
            {
                "name": str(getattr(case, "name", "")),
                "stressors": list(stressors),
                "taxonomy_stressors": [item for item in stressors if item in DEFAULT_HIGH_VARIANCE_STRESSORS],
                "custom_stressors": [item for item in stressors if item not in DEFAULT_HIGH_VARIANCE_STRESSORS],
            }
        )
    missing = [item for item in required if counts[item] <= 0]
    taxonomy_missing = [item for item in DEFAULT_HIGH_VARIANCE_STRESSORS if counts[item] <= 0]
    taxonomy_covered = len(DEFAULT_HIGH_VARIANCE_STRESSORS) - len(taxonomy_missing)
    return {
        "required": list(required),
        "missing_required": missing,
        "counts": dict(sorted(counts.items())),
        "case_count": len(cases),
        "cases_without_stressors": [row["name"] for row in rows if not row["stressors"]],
        "taxonomy_required": list(DEFAULT_HIGH_VARIANCE_STRESSORS),
        "taxonomy_missing": taxonomy_missing,
        "taxonomy_coverage_ratio": round(
            taxonomy_covered / float(len(DEFAULT_HIGH_VARIANCE_STRESSORS) or 1),
            3,
        ),
        "custom_stressors": sorted(key for key in counts if key not in DEFAULT_HIGH_VARIANCE_STRESSORS),
        "taxonomy": [item.to_dict() for item in MATRIX_STRESSOR_TAXONOMY],
    }


def case_stratification(cases: Sequence[Any]) -> Mapping[str, Any]:
    """Summarize the non-domain-specific variance shape of a matrix case pool."""

    tag_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    stressor_counts: Counter[str] = Counter()
    stressor_tag_counts: dict[str, Counter[str]] = {}
    cases_without_tags: list[str] = []
    cases_without_source_file: list[str] = []
    for case in cases:
        case_name = str(getattr(case, "name", "") or getattr(case, "slug", "") or "").strip()
        tags = tuple(_case_tags(case))
        stressors = case_stressors(case)
        source_file = str(getattr(case, "source_file", "") or "").strip()
        if not tags:
            cases_without_tags.append(case_name)
        if not source_file:
            cases_without_source_file.append(case_name)
        if source_file:
            source_counts[source_file] += 1
        for tag in tags:
            tag_counts[tag] += 1
        for stressor in stressors:
            stressor_counts[stressor] += 1
            bucket = stressor_tag_counts.setdefault(stressor, Counter())
            for tag in tags or ("untagged",):
                bucket[tag] += 1
    return {
        "case_count": len(cases),
        "tag_counts": dict(sorted(tag_counts.items())),
        "source_file_counts": dict(sorted(source_counts.items())),
        "stressor_counts": dict(sorted(stressor_counts.items())),
        "stressor_tag_counts": {
            stressor: dict(sorted(counts.items()))
            for stressor, counts in sorted(stressor_tag_counts.items())
        },
        "cases_without_tags": cases_without_tags[:20],
        "cases_without_source_file": cases_without_source_file[:20],
    }


def variance_evaluation(
    cases: Sequence[Any],
    required_stressors: Sequence[str] = (),
) -> dict[str, Any]:
    required = normalize_stressors(required_stressors)
    coverage = stressor_coverage(cases, required)
    counts = {
        str(key): int(value)
        for key, value in dict(coverage.get("counts", {})).items()
        if str(key).strip()
    }
    case_count = len(cases)
    missing = tuple(str(item) for item in coverage.get("missing_required", ()) if str(item).strip())
    cases_without = tuple(str(item) for item in coverage.get("cases_without_stressors", ()) if str(item).strip())
    multi_stressor_cases = sum(1 for case in cases if len(case_stressors(case)) >= 2)
    stressor_density = round(sum(counts.values()) / float(case_count or 1), 3)
    required_coverage_ratio = (
        round((len(required) - len(missing)) / float(len(required)), 3)
        if required
        else 1.0
    )
    taxonomy_ratio = float(coverage.get("taxonomy_coverage_ratio") or 0.0)
    score = _variance_score(
        case_count=case_count,
        required_coverage_ratio=required_coverage_ratio,
        taxonomy_coverage_ratio=taxonomy_ratio,
        stressor_density=stressor_density,
        multi_stressor_cases=multi_stressor_cases,
        cases_without_stressors=len(cases_without),
    )
    status = "skipped" if case_count <= 0 else "passed" if not missing and not cases_without else "failed"
    return {
        "status": status,
        "score": score,
        "case_count": case_count,
        "required_coverage_ratio": required_coverage_ratio,
        "taxonomy_coverage_ratio": taxonomy_ratio,
        "stressor_density": stressor_density,
        "multi_stressor_case_count": multi_stressor_cases,
        "missing_required_stressors": list(missing),
        "cases_without_stressors": list(cases_without),
        "low_depth_case_examples": [
            str(getattr(case, "name", "")).strip()
            for case in cases
            if len(case_stressors(case)) < 2
        ][:20],
        "dominant_stressors": [
            {"stressor": key, "count": value}
            for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]
        ],
        "score_explanation": _variance_score_explanation(
            required_coverage_ratio=required_coverage_ratio,
            taxonomy_coverage_ratio=taxonomy_ratio,
            stressor_density=stressor_density,
            multi_stressor_cases=multi_stressor_cases,
            case_count=case_count,
            cases_without_stressors=len(cases_without),
        ),
    }


def case_stressors(case: Any) -> tuple[str, ...]:
    return normalize_stressors(tuple(getattr(case, "stressors", ()) or ()))


def _case_tags(case: Any) -> tuple[str, ...]:
    return normalize_stressors(tuple(getattr(case, "tags", ()) or ()))


def normalize_stressors(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(slug(item) for item in values if str(item).strip()))


def slug(value: Any) -> str:
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


def _variance_score(
    *,
    case_count: int,
    required_coverage_ratio: float,
    taxonomy_coverage_ratio: float,
    stressor_density: float,
    multi_stressor_cases: int,
    cases_without_stressors: int,
) -> int:
    if case_count <= 0:
        return 0
    density_ratio = min(1.0, stressor_density / 2.0)
    multi_ratio = min(1.0, multi_stressor_cases / float(case_count))
    metadata_ratio = max(0.0, 1.0 - (cases_without_stressors / float(case_count)))
    raw = (
        (required_coverage_ratio * 4.0)
        + (taxonomy_coverage_ratio * 2.0)
        + (density_ratio * 2.0)
        + (multi_ratio * 1.0)
        + (metadata_ratio * 1.0)
    )
    return max(0, min(10, int(round(raw))))


def _variance_score_explanation(
    *,
    required_coverage_ratio: float,
    taxonomy_coverage_ratio: float,
    stressor_density: float,
    multi_stressor_cases: int,
    case_count: int,
    cases_without_stressors: int,
) -> tuple[str, ...]:
    return (
        f"required stressor coverage ratio: {required_coverage_ratio}",
        f"maintained taxonomy coverage ratio: {taxonomy_coverage_ratio}",
        f"average stressors per case: {stressor_density}",
        f"multi-stressor cases: {multi_stressor_cases}/{case_count}",
        f"cases without stressor metadata: {cases_without_stressors}",
    )


__all__ = [
    "DEFAULT_HIGH_VARIANCE_STRESSORS",
    "MATRIX_STRESSOR_TAXONOMY",
    "MatrixStressorClass",
    "case_stratification",
    "case_stressors",
    "missing_required_stressors",
    "normalize_stressors",
    "required_stressors_from_values",
    "slug",
    "stressor_coverage",
    "variance_evaluation",
]
