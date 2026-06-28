"""Installed greenfield auto-rescue release proof helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_post_confirm_rescue_probe import (
    rescue_probe_env,
)


POST_CONFIRM_RESCUE_BUDGET_SECONDS = 90.0


def rescue_cli_issues(
    *,
    manifest: Mapping[str, Any],
    package: Any,
    counts: Any,
    count_minimums: Mapping[str, int],
    count_key: Callable[[str], str],
    write_committed: Callable[[Mapping[str, Any]], bool],
    as_mapping: Callable[[Any], Mapping[str, Any]],
    package_quality_issues: Callable[[Any], Sequence[str]],
    create_returncode: int,
    create_seconds: float,
    detail: str,
    expected_requested_tier: str = "auto",
) -> tuple[str, ...]:
    """Return release-blocking issues for an installed CLI auto-rescue create."""

    issues: list[str] = []
    if create_returncode != 0:
        issues.append(f"auto-rescue create exited with code {create_returncode}: {str(detail or '').strip()[:800]}")
    if create_seconds >= POST_CONFIRM_RESCUE_BUDGET_SECONDS:
        issues.append(f"auto-rescue create exceeded {POST_CONFIRM_RESCUE_BUDGET_SECONDS:.0f}s: {create_seconds:.3f}s")
    if not manifest:
        issues.append("auto-rescue post-confirm quality manifest missing")
    else:
        issues.extend(
            _manifest_issues(
                manifest,
                write_committed=write_committed,
                as_mapping=as_mapping,
                expected_requested_tier=expected_requested_tier,
            )
        )
    issues.extend(_count_floor_issues(counts, minimums=count_minimums, count_key=count_key))
    required_domain_terms = max(3, int(getattr(counts, "required_domain_terms", 0) or 0))
    if int(getattr(counts, "domain_term_hits", 0) or 0) < required_domain_terms:
        issues.append(
            "auto-rescue domain term coverage too low: "
            f"expected at least {required_domain_terms}, found {getattr(counts, 'domain_term_hits', 0)}"
        )
    if create_returncode == 0:
        issues.extend(package_quality_issues(package))
    return tuple(issues)


def installed_auto_rescue_env(env: Mapping[str, str]) -> dict[str, str]:
    """Return the environment used by installed CLI rescue proof."""

    return rescue_probe_env(env)


def _manifest_issues(
    manifest: Mapping[str, Any],
    *,
    write_committed: Callable[[Mapping[str, Any]], bool],
    as_mapping: Callable[[Any], Mapping[str, Any]],
    expected_requested_tier: str,
) -> tuple[str, ...]:
    issues: list[str] = []
    if str(manifest.get("status", "")).strip() != "passed":
        issues.append(f"auto-rescue manifest status is {manifest.get('status')!r}")
    if str(manifest.get("validation_status", "")).strip() != "passed":
        issues.append(f"auto-rescue validation status is {manifest.get('validation_status')!r}")
    if str(manifest.get("requested_repair_tier", "")).strip() != expected_requested_tier:
        issues.append(f"auto-rescue manifest requested tier is {manifest.get('requested_repair_tier')!r}")
    if str(manifest.get("repair_tier", "")).strip() != "rescue":
        issues.append(f"auto-rescue manifest active tier is {manifest.get('repair_tier')!r}")
    if bool(manifest.get("rescue_activated")) is not True:
        issues.append("auto-rescue manifest did not mark rescue_activated")
    if float(manifest.get("budget_seconds") or 0.0) != POST_CONFIRM_RESCUE_BUDGET_SECONDS:
        issues.append(f"auto-rescue manifest budget is {manifest.get('budget_seconds')!r}")
    if int(manifest.get("passes") or 0) < 2:
        issues.append("auto-rescue manifest did not record a repair pass after the injected typed failure")
    if int(manifest.get("issue_count") or 0) != 0:
        issues.append(f"auto-rescue manifest has {manifest.get('issue_count')} issue(s)")
    if "post_confirm_rescue_probe" not in set(manifest.get("repaired_issue_codes") or ()):
        issues.append("auto-rescue manifest did not record the typed rescue probe repair")
    if not write_committed(manifest):
        issues.append("auto-rescue write transaction was not committed")
    if float(manifest.get("whole_project_elapsed_seconds") or 0.0) >= POST_CONFIRM_RESCUE_BUDGET_SECONDS:
        issues.append("auto-rescue manifest reports elapsed time outside the rescue budget")
    if str(as_mapping(manifest.get("quality_lenses")).get("status", "")).strip() != "passed":
        issues.append("auto-rescue quality lens report did not pass")
    return tuple(issues)


def _count_floor_issues(
    counts: Any,
    *,
    minimums: Mapping[str, int],
    count_key: Callable[[str], str],
) -> tuple[str, ...]:
    rows = counts.to_dict() if hasattr(counts, "to_dict") else {}
    issues: list[str] = []
    for label, minimum in minimums.items():
        value = int(rows.get(count_key(label), rows.get(label, 0)) or 0)
        if value < minimum:
            issues.append(f"auto-rescue {label} incomplete: expected at least {minimum}, found {value}")
    return tuple(issues)


__all__ = [
    "POST_CONFIRM_RESCUE_BUDGET_SECONDS",
    "installed_auto_rescue_env",
    "rescue_cli_issues",
]
