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
_FIELD_TOKEN_RE = re.compile(r"[a-z0-9]+")


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
    if set(clarification) != {"question", "required_fields"}:
        issues.append("clarification payload must contain only question and required_fields")
    required_fields = tuple(str(field).strip() for field in expected_fields if str(field).strip())
    if not required_fields:
        issues.append("clarification release case lacks frozen expected material fields")
    observed_fields = tuple(
        str(field).strip()
        for field in (clarification.get("required_fields") or ())
        if str(field).strip()
    )
    if required_fields and not focused_material_question(
        clarification.get("question"), required_fields=required_fields
    ):
        issues.append("clarification payload must ask one focused question about the expected material fields")
    if required_fields and tuple(question_field_key(field) for field in observed_fields) != tuple(
        question_field_key(field) for field in required_fields
    ):
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
    """Require one concise question whose language covers each typed material field."""

    if not isinstance(value, str):
        return False
    question = " ".join(value.strip().split())
    if not question.endswith("?") or question.count("?") != 1 or len(question) > 280:
        return False
    lowered = question.casefold()
    anchors = {
        "display_audience": ("who", "audience", "public", "private", "allowed to see"),
        "visible_result": ("result", "see", "show", "display", "receive"),
        "dependency_source": ("source", "where", "supply", "from"),
        "state_transition": ("state", "status", "change", "transition"),
        "proof_boundary": ("proof", "claim", "boundary", "safety", "demonstrate"),
        "human_actors": ("who", "person", "people", "user"),
        "first_path": ("first complete", "complete task", "finish", "first path"),
    }
    return all(
        any(anchor in lowered for anchor in anchors.get(str(field), (str(field).replace("_", " "),)))
        for field in required_fields
    )


def question_field_key(value: Any) -> str:
    """Canonicalize one material field ID without changing its display label."""

    return "_".join(_FIELD_TOKEN_RE.findall(str(value or "").casefold()))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "CLARIFICATION_REQUIRED_EXPECTATION",
    "FOCUSED_FIRST_PATH_QUESTION",
    "ClarificationExecution",
    "clarification_contract_issues",
    "clarification_quality_verdict",
    "focused_material_question",
    "focused_first_path_question",
    "question_field_key",
    "run_expected_clarification",
]
