"""Summarize per-case generated browser surface proof without overclaiming."""

from __future__ import annotations

from typing import Any, Sequence

from greenfield_browser_surface_proof import BROWSER_SURFACE_PROOF_SCOPE


def browser_proof_summary(
    results: Sequence[Any],
    *,
    include_browser_proof: bool,
) -> dict[str, Any]:
    if not include_browser_proof:
        return {"status": "skipped", "issues": ["browser proof was not requested"], "cases": []}
    cases = [_case_summary(result) for result in results]
    issues = [f"{case['name']}: {issue}" for case in cases for issue in case["issues"]]
    return {
        "status": "failed" if issues else "passed",
        "proof_scope": BROWSER_SURFACE_PROOF_SCOPE,
        "case_count": len(cases),
        "cases": cases,
        "issues": issues,
    }


def _case_summary(result: Any) -> dict[str, Any]:
    issues = list(getattr(result, "browser_surface_issues", ()) or ())
    attempted = bool(getattr(result, "browser_surface_proof_attempted", False))
    if not attempted:
        issues.append("browser proof skipped because post-confirm create did not pass")
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


__all__ = ["browser_proof_summary"]
