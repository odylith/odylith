"""Verify that expected Greenfield clarification outcomes leave no staged or governed writes."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
from pathlib import Path
import time
from typing import Any

from greenfield_matrix_quality_scoring import QUALITY_SCORE_DIMENSIONS
from greenfield_matrix_types import GreenfieldQualityVerdict


CLARIFICATION_REQUIRED_EXPECTATION = "clarification_required"
_NO_WRITE_ROOTS = (Path(".odylith/runtime/greenfield"), Path("odylith"))
_STAGED_TRANSACTION_PATH = Path(".odylith/runtime/greenfield/product-create-transaction.v1.json")


@dataclass(frozen=True)
class ClarificationExecution:
    payload: Mapping[str, Any]
    returncode: int
    seconds: float
    before_record_count: int
    after_record_count: int
    changed_records: tuple[str, ...]
    staged_transaction_present: bool


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
        staged_transaction_present=_STAGED_TRANSACTION_PATH.as_posix() in after_records,
    )


def clarification_contract_issues(execution: ClarificationExecution) -> tuple[str, ...]:
    """Require exactly the small, host-neutral clarification payload and no writes."""

    issues: list[str] = []
    payload = execution.payload
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
    if not _plain_language_question(clarification.get("question")):
        issues.append("clarification payload must contain exactly one plain-language question")
    if clarification.get("required_fields") != ["first_path"]:
        issues.append("clarification payload must require only first_path")
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


def _plain_language_question(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    question = value.strip()
    words = tuple(token for token in question.replace("?", " ").split() if any(char.isalpha() for char in token))
    return "\n" not in question and len(words) >= 3 and question.endswith("?") and question.count("?") == 1


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
