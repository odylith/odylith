"""Typed multi-lens evidence rows for Tribunal-style adjudication."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.common.value_coercion import normalize_token

TRIBUNAL_LENS_REPORT_VERSION = "odylith.tribunal.lens_report.v1"

_SEVERITIES = {"critical", "high", "medium", "low"}
_REPAIRABILITIES = {"unrepairable", "proposal_repair", "semantic_patch", "plan_patch", "safe_package_repair"}


@dataclass(frozen=True)
class TribunalLensCheck:
    """One reviewer-lens judgment with enough custody metadata to drive repair."""

    lens: str
    role: str
    name: str
    status: str
    evidence: str
    issue: str
    surface: str
    target_path: str
    projection_id: str
    semantic_node_id: str
    severity: str
    repairability: str
    owner: str

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def tribunal_lens_check(
    *,
    lens: str,
    role: str,
    name: str,
    passed: bool,
    evidence: Any,
    issue: Any,
    surface: str,
    target_path: str,
    projection_id: str,
    semantic_node_id: str,
    severity: str = "high",
    repairability: str = "semantic_patch",
    owner: str = "tribunal_lens",
) -> TribunalLensCheck:
    """Build a normalized Tribunal lens row without deriving routing from prose."""

    normalized_severity = normalize_token(severity)
    normalized_repairability = normalize_token(repairability)
    return TribunalLensCheck(
        lens=normalize_token(lens) or "tribunal",
        role=normalize_string(role) or normalize_string(lens) or "Tribunal reviewer",
        name=normalize_token(name) or "review_check",
        status="passed" if passed else "failed",
        evidence=normalize_string(evidence),
        issue="" if passed else normalize_string(issue),
        surface=normalize_token(surface) or "review_report",
        target_path=normalize_string(target_path),
        projection_id=normalize_token(projection_id) or "review_report",
        semantic_node_id=normalize_string(semantic_node_id),
        severity=normalized_severity if normalized_severity in _SEVERITIES else "high",
        repairability=(
            normalized_repairability if normalized_repairability in _REPAIRABILITIES else "semantic_patch"
        ),
        owner=normalize_token(owner) or "tribunal_lens",
    )


def tribunal_lens_report(
    checks_by_lens: Mapping[str, Sequence[Mapping[str, Any] | TribunalLensCheck]],
    *,
    version: str = TRIBUNAL_LENS_REPORT_VERSION,
) -> dict[str, Any]:
    """Aggregate typed lens checks into the shared pass/fail report shape."""

    lenses: dict[str, Any] = {}
    issues: list[str] = []
    for lens_name, checks in checks_by_lens.items():
        rows = [_check_dict(check) for check in checks]
        lens_issues = [row["issue"] for row in rows if row.get("status") != "passed" and row.get("issue")]
        issues.extend(lens_issues)
        role = next((row.get("role", "") for row in rows if row.get("role")), "")
        lenses[str(lens_name)] = {
            "status": "failed" if lens_issues else "passed",
            "role": role,
            "checks": rows,
            "issues": lens_issues,
        }
    issues = _unique_text(issues)
    return {
        "version": normalize_string(version) or TRIBUNAL_LENS_REPORT_VERSION,
        "status": "failed" if issues else "passed",
        "lenses": lenses,
        "issues": issues,
    }


def _check_dict(value: Mapping[str, Any] | TribunalLensCheck) -> dict[str, str]:
    if isinstance(value, TribunalLensCheck):
        return value.to_dict()
    return {
        "lens": normalize_token(value.get("lens")),
        "role": normalize_string(value.get("role")),
        "name": normalize_token(value.get("name")),
        "status": "passed" if normalize_token(value.get("status")) == "passed" else "failed",
        "evidence": normalize_string(value.get("evidence")),
        "issue": normalize_string(value.get("issue")),
        "surface": normalize_token(value.get("surface")),
        "target_path": normalize_string(value.get("target_path")),
        "projection_id": normalize_token(value.get("projection_id")),
        "semantic_node_id": normalize_string(value.get("semantic_node_id")),
        "severity": normalize_token(value.get("severity")),
        "repairability": normalize_token(value.get("repairability")),
        "owner": normalize_token(value.get("owner")),
    }


def _unique_text(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = normalize_string(value)
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        rows.append(text)
    return rows


__all__ = [
    "TRIBUNAL_LENS_REPORT_VERSION",
    "TribunalLensCheck",
    "tribunal_lens_check",
    "tribunal_lens_report",
]
