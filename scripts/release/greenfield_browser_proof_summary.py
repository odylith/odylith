"""Summarize per-case generated browser surface proof without overclaiming."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Sequence

from greenfield_browser_surface_proof import BROWSER_SURFACE_PROOF_SCOPE
from greenfield_preconfirm_matrix_cases import CLARIFICATION_REQUIRED_EXPECTATION


def browser_proof_summary(
    results: Sequence[Any],
    *,
    include_browser_proof: bool,
) -> dict[str, Any]:
    if not include_browser_proof:
        return {"status": "skipped", "issues": ["browser proof was not requested"], "cases": []}
    cases = [_case_summary(result) for result in results]
    issues = [f"{case['name']}: {issue}" for case in cases for issue in case["issues"]]
    applicable_case_count = sum(case["status"] != "not_applicable" for case in cases)
    return {
        "status": "failed" if issues else "passed",
        "proof_scope": BROWSER_SURFACE_PROOF_SCOPE,
        "case_count": len(cases),
        "applicable_case_count": applicable_case_count,
        "not_applicable_case_count": len(cases) - applicable_case_count,
        "cases": cases,
        "issues": issues,
    }


def _case_summary(result: Any) -> dict[str, Any]:
    issues = list(getattr(result, "browser_surface_issues", ()) or ())
    attempted = bool(getattr(result, "browser_surface_proof_attempted", False))
    if _case_expectation(result) == CLARIFICATION_REQUIRED_EXPECTATION and not _clarification_contract_passed(result):
        issues.append("clarification-required no-write contract did not pass")
        return {
            "name": str(getattr(result, "name", "") or ""),
            "status": "failed",
            "attempted": attempted,
            "issues": list(dict.fromkeys(issues)),
        }
    if _case_expectation(result) == CLARIFICATION_REQUIRED_EXPECTATION and not attempted and not issues:
        return {
            "name": str(getattr(result, "name", "") or ""),
            "status": "not_applicable",
            "attempted": False,
            "issues": [],
            "reason": "clarification-required flow verified without a committed governed surface",
        }
    if _case_expectation(result) == CLARIFICATION_REQUIRED_EXPECTATION:
        if attempted:
            issues.append("browser proof ran for a clarification-required no-write case")
        return {
            "name": str(getattr(result, "name", "") or ""),
            "status": "failed",
            "attempted": attempted,
            "issues": list(dict.fromkeys(issues)),
        }
    if not attempted:
        issues.append("browser proof skipped because commit-only create did not pass")
    return {
        "name": str(getattr(result, "name", "") or ""),
        "status": _case_status(attempted=attempted, issues=issues),
        "attempted": attempted,
        "issues": issues,
    }


def _case_status(*, attempted: bool, issues: Sequence[str]) -> str:
    if not attempted:
        return "skipped"
    return "failed" if issues else "passed"


def _case_expectation(result: Any) -> str:
    evidence = getattr(result, "evidence", None)
    if not isinstance(evidence, Mapping):
        return ""
    case = evidence.get("case")
    if not isinstance(case, Mapping):
        return ""
    return str(case.get("expectation") or "").strip()


def _clarification_contract_passed(result: Any) -> bool:
    quality = getattr(result, "quality", None)
    return bool(getattr(quality, "passed", False))


__all__ = ["browser_proof_summary"]
