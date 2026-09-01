"""Verify that expected Greenfield clarification outcomes leave no staged or governed writes."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import time
from typing import Any

from greenfield_matrix_quality_scoring import QUALITY_SCORE_DIMENSIONS
from greenfield_matrix_types import GreenfieldQualityVerdict


CLARIFICATION_REQUIRED_EXPECTATION = "clarification_required"
FOCUSED_FIRST_PATH_QUESTION = (
    "What is the first complete task the product should help a person finish, and what result should they see?"
)
_NO_WRITE_ROOTS = (Path(".odylith/runtime/greenfield"), Path("odylith"))
_STAGED_TRANSACTION_ROOT = Path(".odylith/runtime/greenfield/pending")
_FIELD_ID_RE = re.compile(r"[a-z][a-z0-9_]*")
MATERIAL_QUESTION_FIELDS = frozenset(
    {
        "first_path",
        "human_actors",
        "external_systems",
        "non_goals",
        "operational_constraints",
        "product_boundary",
        "proof_boundary",
        "visible_result",
    }
)


@dataclass(frozen=True)
class ClarificationExecution:
    payload: Mapping[str, Any]
    returncode: int
    seconds: float
    before_record_count: int
    after_record_count: int
    changed_records: tuple[str, ...]
    staged_transaction_present: bool
    write_audit_active: bool | None = None
    write_attempts: tuple[str, ...] = ()
    subprocess_attempts: tuple[str, ...] = ()
    write_audit_error: str = ""


def run_expected_clarification(
    *,
    repo_root: Path,
    invoke: Callable[[], Any],
    parse_payload: Callable[[str], Mapping[str, Any]],
) -> ClarificationExecution:
    """Run one proposal and retain only the evidence needed to prove its no-write contract."""

    before_records = _snapshot_no_write_roots(repo_root)
    started = time.perf_counter()
    proposed = invoke()
    seconds = round(time.perf_counter() - started, 3)
    payload = parse_payload(str(getattr(proposed, "stdout", "")))
    after_records = _snapshot_no_write_roots(repo_root)
    changed_records = tuple(
        path
        for path in sorted(set(before_records) | set(after_records))
        if before_records.get(path) != after_records.get(path)
    )
    return ClarificationExecution(
        payload=payload,
        returncode=int(getattr(proposed, "returncode", 1)),
        seconds=seconds,
        before_record_count=len(before_records),
        after_record_count=len(after_records),
        changed_records=changed_records,
        staged_transaction_present=any(
            path.startswith(_STAGED_TRANSACTION_ROOT.as_posix() + "/")
            for path in after_records
        ),
    )


def clarification_contract_issues(
    execution: ClarificationExecution,
    *,
    expected_fields: Sequence[str] = (),
    expected_question: str = "",
    expected_model_profile_id: str = "",
) -> tuple[str, ...]:
    """Require exactly the small, host-neutral clarification payload and no writes."""

    issues: list[str] = []
    payload = execution.payload
    if execution.write_audit_active is not True:
        issues.append("clarification proposal did not activate the installed write audit")
    if execution.write_audit_error:
        issues.append("clarification proposal could not complete the installed write audit")
    if execution.write_attempts:
        issues.append("clarification proposal attempted repository writes: " + ", ".join(execution.write_attempts))
    if execution.subprocess_attempts:
        issues.append("clarification proposal attempted a child process: " + ", ".join(execution.subprocess_attempts))
    if execution.returncode != 0:
        issues.append(f"clarification proposal exited with code {execution.returncode}")
    if str(payload.get("mode") or "").strip() != CLARIFICATION_REQUIRED_EXPECTATION:
        issues.append(f"clarification proposal mode must be `{CLARIFICATION_REQUIRED_EXPECTATION}`")
    if set(payload) != {"mode", "clarification"}:
        issues.append("clarification proposal must contain only mode and clarification")
    if "transaction_file" in payload:
        issues.append("clarification proposal must not include transaction_file")
    if "product_create_transaction" in payload:
        issues.append("clarification proposal must not include ProductCreateTransaction")
    clarification = payload.get("clarification") if isinstance(payload.get("clarification"), Mapping) else {}
    if set(clarification) != {
        "question",
        "required_fields",
        "model_profile",
        "consistency_assessment",
    }:
        issues.append(
            "clarification payload must contain only question, required_fields, model_profile, "
            "and consistency_assessment"
        )
    model_profile = clarification.get("model_profile")
    model_profile = model_profile if isinstance(model_profile, Mapping) else {}
    if set(model_profile) != {
        "profile_id",
        "provider",
        "model",
        "reasoning_effort",
        "effective_timeout_seconds",
        "authoring_tier",
    }:
        issues.append("clarification model_profile must contain the stable six-field request observation")
    if expected_model_profile_id and str(model_profile.get("profile_id") or "").strip() != expected_model_profile_id:
        issues.append("clarification model_profile must match the selected pre-call profile")
    consistency = clarification.get("consistency_assessment")
    consistency = consistency if isinstance(consistency, Mapping) else {}
    if set(consistency) != {"status", "source_spans"}:
        issues.append("clarification consistency_assessment must contain only status and source_spans")
    consistency_status = str(consistency.get("status") or "").strip()
    raw_consistency_spans = consistency.get("source_spans")
    consistency_spans = (
        tuple(raw_consistency_spans)
        if isinstance(raw_consistency_spans, Sequence)
        and not isinstance(raw_consistency_spans, (str, bytes, bytearray))
        else ()
    )
    if consistency_status == "consistent" and consistency_spans:
        issues.append("consistent clarification must not claim conflicting source spans")
    elif consistency_status == "material_contradiction" and (
        len(consistency_spans) < 2
        or any(not isinstance(span, Mapping) for span in consistency_spans)
    ):
        issues.append("material contradiction clarification requires at least two source-bound spans")
    elif consistency_status not in {"consistent", "material_contradiction"}:
        issues.append("clarification consistency_assessment has an unsupported status")
    required_fields = tuple(str(field).strip() for field in expected_fields if str(field).strip())
    if not required_fields:
        issues.append("clarification release case lacks frozen expected material fields")
    elif len(required_fields) != 1:
        issues.append("clarification release case must freeze exactly one typed material field")
    observed_fields = tuple(
        str(field).strip()
        for field in (clarification.get("required_fields") or ())
        if str(field).strip()
    )
    question = clarification.get("question")
    if required_fields and not focused_material_question(question, required_fields=required_fields):
        issues.append("clarification payload must contain one bounded question for typed material fields")
    if expected_question and question != expected_question:
        issues.append("clarification payload question must match the frozen typed clarification")
    if required_fields and observed_fields != required_fields:
        issues.append(
            "clarification payload required_fields must match the expected material fields: "
            + ", ".join(required_fields)
        )
    if execution.staged_transaction_present:
        issues.append("clarification proposal created a staged transaction record")
    if execution.changed_records:
        issues.append(
            "clarification proposal created or changed governed or staged records: "
            + ", ".join(execution.changed_records)
        )
    return tuple(issues)


def clarification_quality_verdict(issues: Sequence[str]) -> GreenfieldQualityVerdict:
    passed = not issues
    score = 10 if passed else 0
    return GreenfieldQualityVerdict(
        passed=passed,
        issues=tuple(issues),
        lenses={lens: passed for lens in ("product_manager", "architect", "engineer", "domain_expert")},
        scores={dimension: score for dimension in QUALITY_SCORE_DIMENSIONS},
        score=score,
        score_explanation=(
            "clarification-required pre-confirm contract verified without a transaction or governed write"
            if passed
            else "clarification-required pre-confirm contract failed",
        ),
        score_basis="clarification_required_no_write_contract",
    )


def _snapshot_no_write_roots(repo_root: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    for relative_root in _NO_WRITE_ROOTS:
        root = repo_root / relative_root
        if not root.exists():
            continue
        paths = (root,) if root.is_file() else (path for path in root.rglob("*") if path.is_file())
        for path in paths:
            records[path.relative_to(repo_root).as_posix()] = _sha256_file(path)
    return records


def focused_first_path_question(value: Any) -> bool:
    return isinstance(value, str) and value.strip() == FOCUSED_FIRST_PATH_QUESTION


def focused_material_question(value: Any, *, required_fields: Sequence[str]) -> bool:
    """Require one bounded question paired with closed typed material fields."""

    if not isinstance(value, str):
        return False
    question = value.strip()
    if not question.endswith("?") or question.count("?") != 1 or len(question) > 280:
        return False
    fields = tuple(question_field_key(field) for field in required_fields)
    return len(fields) == 1 and fields[0] in MATERIAL_QUESTION_FIELDS


def material_question_field_issues(
    fields: Sequence[str],
    *,
    source_texts: Sequence[str],
) -> tuple[str, ...]:
    """Reject evaluator question fields outside the product-owned typed contract."""

    del source_texts
    issues: list[str] = []
    seen: set[str] = set()
    for raw in fields:
        field = question_field_key(raw)
        if not field or field in seen:
            issues.append(f"duplicate or empty material question field `{raw}`")
            continue
        seen.add(field)
        if field not in MATERIAL_QUESTION_FIELDS:
            issues.append(f"unsupported material question field `{raw}`")
    return tuple(issues)


def question_field_key(value: Any) -> str:
    """Return one already-canonical typed material-field ID."""

    field = str(value or "").strip()
    return field if _FIELD_ID_RE.fullmatch(field) else ""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "CLARIFICATION_REQUIRED_EXPECTATION",
    "FOCUSED_FIRST_PATH_QUESTION",
    "MATERIAL_QUESTION_FIELDS",
    "ClarificationExecution",
    "clarification_contract_issues",
    "clarification_quality_verdict",
    "focused_material_question",
    "focused_first_path_question",
    "material_question_field_issues",
    "question_field_key",
    "run_expected_clarification",
]
