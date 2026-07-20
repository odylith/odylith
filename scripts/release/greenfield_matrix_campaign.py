"""Campaign telemetry and clustering for greenfield matrix discovery runs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
from typing import Any

from greenfield_matrix_stressors import DEFAULT_HIGH_VARIANCE_STRESSORS
from greenfield_matrix_stressors import case_stressors
from greenfield_matrix_stressors import missing_required_stressors
from greenfield_matrix_stressors import normalize_stressors
from greenfield_matrix_stressors import required_stressors_from_values
from greenfield_matrix_stressors import stressor_coverage
from greenfield_matrix_stressors import variance_evaluation
from greenfield_matrix_metamorphic import evaluate_metamorphic_outputs
from greenfield_matrix_types import GreenfieldMatrixResult


CAMPAIGN_TELEMETRY_VERSION = "odylith.greenfield.matrix.telemetry.v1"
CAMPAIGN_SUMMARY_VERSION = "odylith.greenfield.matrix.campaign.v1"


@dataclass(frozen=True)
class MatrixCampaignConfig:
    phase: str = "single-matrix"
    proof_tier: str = "discovery"
    telemetry_jsonl: Path | None = None
    stop_after_failures: int = 0
    stop_after_cluster_failures: int = 0
    required_stressors: tuple[str, ...] = ()

    @property
    def telemetry_enabled(self) -> bool:
        return self.telemetry_jsonl is not None


class MatrixTelemetryWriter:
    """Append-only JSONL telemetry for long-running matrix campaigns."""

    def __init__(self, path: Path | None) -> None:
        self._path = Path(path).expanduser().resolve() if path else None
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def enabled(self) -> bool:
        return self._path is not None

    def emit(self, event: str, payload: Mapping[str, Any]) -> None:
        if self._path is None:
            return
        row = {
            "version": CAMPAIGN_TELEMETRY_VERSION,
            "event": str(event),
            "emitted_at_epoch": round(time.time(), 3),
            **dict(payload),
        }
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def proof_tier_from_value(value: str) -> str:
    token = str(value or "").strip().casefold()
    return token if token in {"discovery", "release"} else "release"


def campaign_phase_from_value(value: str) -> str:
    token = "-".join(str(value or "").strip().casefold().replace("_", "-").split())
    return token or "single-matrix"


def positive_int(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, number)


def case_started_event(*, case: Any, index: int, total: int) -> Mapping[str, Any]:
    return {
        "index": int(index),
        "total": int(total),
        "case": _case_identity(case),
    }


def case_completed_event(*, result: GreenfieldMatrixResult, index: int, total: int) -> Mapping[str, Any]:
    return {
        "index": int(index),
        "total": int(total),
        "result": _compact_result(result),
        "failure_cluster": failure_cluster_key(result),
    }


def failure_cluster_key(result: GreenfieldMatrixResult) -> str:
    if result.status == "passed" and result.quality.passed:
        return ""
    manifest_cluster = _manifest_issue_cluster_key(result)
    if manifest_cluster:
        return manifest_cluster
    text = _failure_text(result)
    text_cluster = _canonical_failure_text(text) if text else ""
    if text_cluster and text_cluster != "failure.unclassified":
        return text_cluster
    score_cluster = _score_cluster_key(result)
    if score_cluster:
        return score_cluster
    return f"status.{_slug(result.status or 'failed')}"


def failure_clusters(results: Sequence[GreenfieldMatrixResult]) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    grouped: dict[str, list[GreenfieldMatrixResult]] = {}
    for result in results:
        key = failure_cluster_key(result)
        if key:
            grouped.setdefault(key, []).append(result)
    for key, items in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        rows.append(
            {
                "cluster": key,
                "count": len(items),
                "cases": [item.name for item in items],
                "case_ids": _failed_case_ids(items),
                "case_fingerprints": _failed_case_fingerprints(items),
                "stressors": _failed_stressors(items),
                "example_issue": _failure_text(items[0])[:500],
            }
        )
    return rows


def stop_reason(results: Sequence[GreenfieldMatrixResult], config: MatrixCampaignConfig) -> str:
    failed = [result for result in results if result.status != "passed" or not result.quality.passed]
    if config.stop_after_failures and len(failed) >= config.stop_after_failures:
        return f"failure-threshold:{config.stop_after_failures}"
    if config.stop_after_cluster_failures:
        counts = Counter(failure_cluster_key(result) for result in failed)
        counts.pop("", None)
        if counts and max(counts.values()) >= config.stop_after_cluster_failures:
            cluster, count = counts.most_common(1)[0]
            return f"cluster-threshold:{cluster}:{count}"
    return ""


def campaign_summary(
    *,
    cases: Sequence[Any],
    results: Sequence[GreenfieldMatrixResult],
    config: MatrixCampaignConfig,
    stopped_reason: str,
) -> Mapping[str, Any]:
    completed = len(results)
    failures = sum(1 for result in results if result.status != "passed" or not result.quality.passed)
    return {
        "version": CAMPAIGN_SUMMARY_VERSION,
        "phase": config.phase,
        "proof_tier": config.proof_tier,
        "selected_case_count": len(cases),
        "completed_case_count": completed,
        "passed_case_count": completed - failures,
        "failed_case_count": failures,
        "stopped_early": completed < len(cases),
        "stop_reason": stopped_reason,
        "stop_after_failures": config.stop_after_failures,
        "stop_after_cluster_failures": config.stop_after_cluster_failures,
        "telemetry_jsonl": str(config.telemetry_jsonl or ""),
        "failure_clusters": failure_clusters(results),
        "stressor_coverage": stressor_coverage(cases, config.required_stressors),
        "stressor_variance": variance_evaluation(cases, config.required_stressors),
        "stressor_outcomes": stressor_outcomes(cases=cases, results=results),
        "metamorphic_output": evaluate_metamorphic_outputs(cases=cases, results=results),
        "release_readiness_boundary": _release_readiness_boundary(config),
    }


def stressor_outcomes(
    *,
    cases: Sequence[Any],
    results: Sequence[GreenfieldMatrixResult],
) -> Mapping[str, Any]:
    selected_counts: Counter[str] = Counter()
    for case in cases:
        for stressor in case_stressors(case):
            selected_counts[stressor] += 1
    rows: dict[str, dict[str, Any]] = {
        key: {
            "stressor": key,
            "selected_case_count": int(count),
            "completed_case_count": 0,
            "passed_case_count": 0,
            "failed_case_count": 0,
            "failure_clusters": {},
            "example_cases": [],
        }
        for key, count in selected_counts.items()
    }
    for result in results:
        stressors = _result_case_stressors(result)
        if not stressors:
            continue
        failed = result.status != "passed" or not result.quality.passed
        cluster = failure_cluster_key(result) if failed else ""
        for stressor in stressors:
            row = rows.setdefault(
                stressor,
                {
                    "stressor": stressor,
                    "selected_case_count": 0,
                    "completed_case_count": 0,
                    "passed_case_count": 0,
                    "failed_case_count": 0,
                    "failure_clusters": {},
                    "example_cases": [],
                },
            )
            row["completed_case_count"] = int(row.get("completed_case_count") or 0) + 1
            outcome_key = "failed_case_count" if failed else "passed_case_count"
            row[outcome_key] = int(row.get(outcome_key) or 0) + 1
            if failed and cluster:
                current_clusters = row.get("failure_clusters")
                clusters = Counter(dict(current_clusters) if isinstance(current_clusters, Mapping) else {})
                clusters[cluster] += 1
                row["failure_clusters"] = dict(sorted(clusters.items()))
            examples = list(row.get("example_cases") or [])
            name = str(result.name or "").strip()
            if name and name not in examples and len(examples) < 5:
                examples.append(name)
                row["example_cases"] = examples
    ordered = sorted(
        rows.values(),
        key=lambda row: (-int(row.get("failed_case_count") or 0), str(row.get("stressor") or "")),
    )
    return {
        "status": "passed" if not any(int(row.get("failed_case_count") or 0) for row in ordered) else "failed",
        "failed_stressors": [
            str(row.get("stressor"))
            for row in ordered
            if int(row.get("failed_case_count") or 0) > 0
        ],
        "by_stressor": ordered,
    }


def _compact_result(result: GreenfieldMatrixResult) -> Mapping[str, Any]:
    return {
        "name": result.name,
        "case": _result_case_identity(result),
        "status": result.status,
        "quality_passed": result.quality.passed,
        "score": result.quality.score,
        "create_seconds": result.create_seconds,
        "create_returncode": result.create_returncode,
        "issue_count": len(result.quality.issues),
        "first_issue": _failure_text(result)[:500],
        "stressors": list(_result_case_stressors(result)),
    }


def _result_case_identity(result: GreenfieldMatrixResult) -> Mapping[str, Any]:
    evidence = result.evidence if isinstance(result.evidence, Mapping) else {}
    case = evidence.get("case") if isinstance(evidence.get("case"), Mapping) else {}
    return {
        "id": str(case.get("id") or ""),
        "name": str(case.get("name") or result.name),
        "slug": str(case.get("slug") or ""),
        "prompt_sha256": str(case.get("prompt_sha256") or ""),
        "confirmed_intent_sha256": str(case.get("confirmed_intent_sha256") or ""),
    }


def _failed_case_ids(results: Sequence[GreenfieldMatrixResult]) -> list[str]:
    return list(
        dict.fromkeys(
            str(_result_case_identity(result).get("id") or "").strip()
            for result in results
            if str(_result_case_identity(result).get("id") or "").strip()
        )
    )


def _failed_case_fingerprints(results: Sequence[GreenfieldMatrixResult]) -> list[str]:
    fingerprints: list[str] = []
    for result in results:
        case = _result_case_identity(result)
        for key in ("prompt_sha256", "confirmed_intent_sha256"):
            value = str(case.get(key) or "").strip()
            if value:
                fingerprints.append(value)
    return list(dict.fromkeys(fingerprints))


def _failed_stressors(results: Sequence[GreenfieldMatrixResult]) -> list[str]:
    stressors: list[str] = []
    for result in results:
        stressors.extend(_result_case_stressors(result))
    return list(dict.fromkeys(stressors))


def _result_case_stressors(result: GreenfieldMatrixResult) -> tuple[str, ...]:
    evidence = result.evidence if isinstance(result.evidence, Mapping) else {}
    case = evidence.get("case") if isinstance(evidence.get("case"), Mapping) else {}
    return normalize_stressors(tuple(str(item) for item in case.get("stressors", ()) or ()))


def _score_cluster_key(result: GreenfieldMatrixResult) -> str:
    low_scores: list[str] = []
    for dimension, score in result.quality.scores.items():
        try:
            numeric_score = int(score)
        except (TypeError, ValueError):
            numeric_score = 0
        if numeric_score < 10:
            low_scores.append(_slug(dimension))
    if not low_scores:
        return ""
    if result.status not in {"passed", "failed"}:
        return f"status.{_slug(result.status)}"
    return "scores." + ".".join(low_scores[:4])


def _case_identity(case: Any) -> Mapping[str, Any]:
    return {
        "id": str(getattr(case, "case_id", "") or getattr(case, "slug", "")),
        "name": str(getattr(case, "name", "")),
        "slug": str(getattr(case, "slug", "")),
        "tags": list(getattr(case, "tags", ()) or ()),
        "stressors": list(getattr(case, "stressors", ()) or ()),
    }


def _failure_text(result: GreenfieldMatrixResult) -> str:
    for value in (result.failure_detail, result.create_stderr_excerpt, result.create_stdout_excerpt):
        text = _extract_issue(str(value or ""))
        if text:
            return text
    for issue in result.quality.issues:
        text = _extract_issue(str(issue))
        if text:
            return text
    for value in (result.status,):
        text = _extract_issue(str(value or ""))
        if text:
            return text
    return ""


def _extract_issue(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = _extract_embedded_json_issue(text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, Mapping):
        text = str(parsed.get("error") or parsed.get("message") or parsed.get("detail") or text)
    for raw_line in text.replace("\\n", "\n").splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue
        if line.startswith("- "):
            return line[2:].strip()
        if " issue(s):" in line or line.lower().startswith(("remediation:", "auto-enrichment:")):
            continue
    return " ".join(text.split())


def _extract_embedded_json_issue(value: str) -> str:
    text = str(value or "").strip()
    if not text or text.startswith("{"):
        return text
    start = text.find("{")
    if start < 0:
        return text
    candidate = text[start:]
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return text
    if isinstance(parsed, Mapping):
        return str(parsed.get("error") or parsed.get("message") or parsed.get("detail") or text)
    return text


def _manifest_issue_cluster_key(result: GreenfieldMatrixResult) -> str:
    summary = result.commit_manifest_summary
    if not isinstance(summary, Mapping):
        return ""
    signatures = _string_rows(summary.get("issue_signatures"))
    if signatures:
        return "manifest." + signatures[0]
    codes = _string_rows(summary.get("issue_codes"))
    owners = _string_rows(summary.get("issue_owners"))
    surfaces = _string_rows(summary.get("issue_surfaces"))
    parts = [*(_slug(item) for item in codes[:2]), *(_slug(item) for item in owners[:2]), *(_slug(item) for item in surfaces[:2])]
    parts = [part for part in parts if part]
    return "manifest." + ".".join(parts[:6]) if parts else ""


def _canonical_failure_text(value: str) -> str:
    value = _remove_backtick_spans(value)
    words = [
        token
        for token in _alnum_tokens(value)
        if not _ignore_failure_token(token)
    ]
    if not words:
        return "failure.unclassified"
    return ".".join(words[:10])


def _string_rows(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _ignore_failure_token(token: str) -> bool:
    return (
        not token
        or token.isdigit()
        or len(token) > 32
        or token in {"a", "an", "and", "at", "by", "for", "in", "of", "or", "the", "to", "with"}
    )


def _remove_backtick_spans(value: str) -> str:
    text = str(value or "")
    result: list[str] = []
    inside = False
    for char in text:
        if char == "`":
            inside = not inside
            result.append(" ")
            continue
        if not inside:
            result.append(char)
    return "".join(result)


def _slug(value: Any) -> str:
    text = str(value or "").strip().casefold().replace("_", "-")
    parts: list[str] = []
    last_dash = False
    for char in text:
        if char.isalnum():
            parts.append(char)
            last_dash = False
        elif not last_dash:
            parts.append("-")
            last_dash = True
    return "".join(parts).strip("-")


def _alnum_tokens(value: str) -> tuple[str, ...]:
    tokens: list[str] = []
    current: list[str] = []
    for char in str(value or "").casefold():
        if char.isalnum():
            current.append(char)
            continue
        if current:
            tokens.append("".join(current))
            current.clear()
    if current:
        tokens.append("".join(current))
    return tuple(tokens)


def _release_readiness_boundary(config: MatrixCampaignConfig) -> str:
    if config.proof_tier == "release":
        return "release proof remains browser/rescue strict unless explicitly proven in this run"
    return (
        "discovery proof may skip browser and natural rescue for speed; it must not be used "
        "as release-readiness proof"
    )


__all__ = [
    "DEFAULT_HIGH_VARIANCE_STRESSORS",
    "MatrixCampaignConfig",
    "MatrixTelemetryWriter",
    "campaign_phase_from_value",
    "campaign_summary",
    "case_completed_event",
    "case_started_event",
    "failure_cluster_key",
    "failure_clusters",
    "missing_required_stressors",
    "positive_int",
    "proof_tier_from_value",
    "required_stressors_from_values",
    "stop_reason",
    "stressor_outcomes",
    "stressor_coverage",
    "variance_evaluation",
]
