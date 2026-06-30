"""Typed review findings for greenfield post-confirm custody."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from odylith.runtime.common.value_coercion import dedupe_by_key
from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.common.value_coercion import normalize_token


POST_CONFIRM_REVIEW_REPORT_VERSION = "odylith.greenfield.post_confirm.review_report.v1"

_SEVERITIES = {"critical", "high", "medium", "low"}
_REPAIRABILITIES = {
    "unrepairable",
    "semantic_patch",
    "plan_patch",
    "projection_rerender",
}


@dataclass(frozen=True)
class GreenfieldReviewFinding:
    """Machine-routable quality finding emitted before governed writes."""

    code: str
    surface: str
    target_path: str
    projection_id: str
    semantic_node_id: str
    severity: str
    repairability: str
    owner: str
    source: str
    message: str
    lens: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class GreenfieldReviewReport:
    """Typed post-confirm review report used as the repair-routing contract."""

    version: str
    status: str
    findings: tuple[GreenfieldReviewFinding, ...]

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "status": self.status,
            "finding_count": len(self.findings),
            "findings": [finding.to_dict() for finding in self.findings],
        }


def review_finding(
    *,
    code: str,
    surface: str,
    message: Any,
    target_path: str = "",
    projection_id: str = "",
    semantic_node_id: str = "",
    severity: str = "medium",
    repairability: str = "unrepairable",
    owner: str = "post_confirm_engine",
    source: str = "post_confirm",
    lens: str = "",
) -> GreenfieldReviewFinding:
    """Build a normalized typed finding without deriving semantics from prose."""

    normalized_severity = normalize_token(severity)
    normalized_repairability = normalize_token(repairability)
    return GreenfieldReviewFinding(
        code=normalize_token(code) or "post_confirm_contract",
        surface=normalize_string(surface) or "post_confirm",
        target_path=normalize_string(target_path),
        projection_id=normalize_string(projection_id),
        semantic_node_id=normalize_string(semantic_node_id),
        severity=normalized_severity if normalized_severity in _SEVERITIES else "medium",
        repairability=normalized_repairability if normalized_repairability in _REPAIRABILITIES else "unrepairable",
        owner=normalize_token(owner) or "post_confirm_engine",
        source=normalize_token(source) or "post_confirm",
        message=normalize_string(message),
        lens=normalize_token(lens),
    )


def review_findings_from_messages(
    messages: Iterable[Any],
    *,
    code: str,
    surface: str,
    target_path: str = "",
    projection_id: str = "",
    semantic_node_id: str = "",
    severity: str = "medium",
    repairability: str = "unrepairable",
    owner: str = "post_confirm_engine",
    source: str = "post_confirm",
    lens: str = "",
) -> tuple[GreenfieldReviewFinding, ...]:
    findings = [
        review_finding(
            code=code,
            surface=surface,
            target_path=target_path,
            projection_id=projection_id,
            semantic_node_id=semantic_node_id,
            severity=severity,
            repairability=repairability,
            owner=owner,
            source=source,
            message=message,
            lens=lens,
        )
        for message in messages
        if normalize_string(message)
    ]
    return tuple(dedupe_review_findings(findings))


def dedupe_review_findings(
    findings: Sequence[GreenfieldReviewFinding],
) -> tuple[GreenfieldReviewFinding, ...]:
    return tuple(
        dedupe_by_key(
            findings,
            key=lambda finding: (
                finding.code,
                finding.surface.casefold(),
                finding.target_path,
                finding.projection_id,
                finding.semantic_node_id,
                finding.source,
                finding.message.casefold(),
            ),
        )
    )


def review_report_from_findings(
    findings: Sequence[GreenfieldReviewFinding],
) -> GreenfieldReviewReport:
    deduped = dedupe_review_findings(findings)
    return GreenfieldReviewReport(
        version=POST_CONFIRM_REVIEW_REPORT_VERSION,
        status="failed" if deduped else "passed",
        findings=deduped,
    )


def review_findings_from_dicts(values: Iterable[Mapping[str, Any]]) -> tuple[GreenfieldReviewFinding, ...]:
    return tuple(
        review_finding(
            code=value.get("code", ""),
            surface=value.get("surface", ""),
            target_path=value.get("target_path", value.get("path", "")),
            projection_id=value.get("projection_id", ""),
            semantic_node_id=value.get("semantic_node_id", ""),
            severity=value.get("severity", ""),
            repairability=value.get("repairability", ""),
            owner=value.get("owner", ""),
            source=value.get("source", ""),
            message=value.get("message", ""),
            lens=value.get("lens", ""),
        )
        for value in values
        if isinstance(value, Mapping)
    )


__all__ = [
    "GreenfieldReviewFinding",
    "GreenfieldReviewReport",
    "POST_CONFIRM_REVIEW_REPORT_VERSION",
    "dedupe_review_findings",
    "review_finding",
    "review_findings_from_dicts",
    "review_findings_from_messages",
    "review_report_from_findings",
]
