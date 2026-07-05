"""Structured preflight failures for Greenfield matrix runs."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from greenfield_matrix_campaign import missing_required_stressors  # noqa: E402
from greenfield_matrix_case_file import ungrounded_required_terms  # noqa: E402
from greenfield_matrix_leakage import case_preflight_leakage_terms  # noqa: E402
from greenfield_post_confirm_matrix_cases import GreenfieldMatrixCase  # noqa: E402
import platform_domain_leakage_check as platform_domain_leakage  # noqa: E402


@dataclass(frozen=True)
class MatrixPreflightFailure:
    case: GreenfieldMatrixCase
    detail: str


def matrix_preflight_failures(
    *,
    repo_root: Path,
    release_dir: Path,
    cases: Sequence[GreenfieldMatrixCase],
    required_stressors: Sequence[str],
    enforce_required_stressors: bool = True,
) -> tuple[MatrixPreflightFailure, ...]:
    issues_by_case: dict[GreenfieldMatrixCase, list[str]] = {}
    for case in cases:
        missing_terms = ungrounded_required_terms(
            prompt=case.prompt,
            confirmed_intent_markdown=str(getattr(case, "confirmed_intent_markdown", "") or ""),
            required_terms=tuple(getattr(case, "required_terms", ()) or ()),
        )
        if missing_terms:
            _add_issue(
                issues_by_case,
                case,
                "required terms are not grounded in the prompt or confirmed intent: "
                + ", ".join(missing_terms),
            )
        if not case_preflight_leakage_terms(case):
            _add_issue(
                issues_by_case,
                case,
                "leakage_terms are required before platform domain leakage proof can run",
            )
    missing_stressors = missing_required_stressors(cases, required_stressors) if enforce_required_stressors else ()
    if missing_stressors:
        detail = "selected case set is missing required stressor classes: " + ", ".join(missing_stressors)
        for case in cases:
            _add_issue(issues_by_case, case, detail)
    for finding in _platform_domain_leakage_findings(
        repo_root=repo_root,
        release_dir=release_dir,
        cases=cases,
    ):
        term = str(finding.term).strip()
        detail = f"platform custody leaked selected case vocabulary `{term}` at {finding.location}:{finding.line}"
        matched = [case for case in cases if term in set(case_preflight_leakage_terms(case))]
        for case in matched or cases:
            _add_issue(issues_by_case, case, detail)
    return tuple(
        MatrixPreflightFailure(
            case=case,
            detail="greenfield matrix preflight failed: " + "; ".join(issues),
        )
        for case, issues in issues_by_case.items()
    )


def _add_issue(
    issues_by_case: dict[GreenfieldMatrixCase, list[str]],
    case: GreenfieldMatrixCase,
    issue: str,
) -> None:
    bucket = issues_by_case.setdefault(case, [])
    if issue not in bucket:
        bucket.append(issue)


def _platform_domain_leakage_findings(
    *,
    repo_root: Path,
    release_dir: Path,
    cases: Sequence[GreenfieldMatrixCase],
) -> tuple[Any, ...]:
    terms = tuple(
        sorted({term for case in cases for term in case_preflight_leakage_terms(case)})
    )
    if not terms:
        return ()
    return tuple(
        platform_domain_leakage.scan_platform_custody(
            repo_root=repo_root,
            dist_dir=release_dir,
            terms=terms,
        )
    )


__all__ = ["MatrixPreflightFailure", "matrix_preflight_failures"]
