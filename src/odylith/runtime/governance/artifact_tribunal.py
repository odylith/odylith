"""Deterministic Tribunal gate for single governed artifact writes."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence


_PLACEHOLDER_TOKENS = {"", "-", "n/a", "na", "none", "tbd", "todo", "details"}
_RISK_TOKENS = (
    "risk",
    "failure",
    "fallback",
    "rollback",
    "mitigation",
    "blast radius",
    "slo",
    "sla",
    "recovery",
    "degraded",
    "scope",
    "operational",
)
_SECURITY_TOKENS = (
    "security",
    "auth",
    "authentication",
    "authorization",
    "credential",
    "permission",
    "session",
    "secret",
    "token",
    "access",
    "ownership",
    "private",
    "abuse",
    "threat",
    "payment",
    "pii",
    "data risk",
)
_POLICY_TOKENS = (
    "compliance",
    "policy",
    "privacy",
    "retention",
    "audit",
    "regulated",
    "gdpr",
    "hipaa",
    "pci",
    "soc2",
    "moderation",
    "accessibility",
    "public",
    "private",
    "safety",
)


@dataclass(frozen=True)
class GovernedArtifactTribunalDecision:
    artifact_kind: str
    status: str
    version: str
    summary: str
    dimensions: dict[str, str]
    issues: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_kind": self.artifact_kind,
            "status": self.status,
            "version": self.version,
            "summary": self.summary,
            "dimensions": dict(self.dimensions),
            "issues": list(self.issues),
            "warnings": list(self.warnings),
        }


def run_governed_artifact_tribunal(
    *,
    artifact_kind: str,
    payload: Mapping[str, Any],
) -> GovernedArtifactTribunalDecision:
    """Run a zero-provider Tribunal check before a governed artifact write."""

    kind = _normalize_kind(artifact_kind)
    issues: list[str] = []
    warnings: list[str] = []
    dimensions = {
        "latency": "local deterministic gate; no provider, no subagent, no broad scan",
        "human_readability": "bounded fields must be concrete enough for review without oversized prose",
    }

    if kind == "backlog":
        _check_required_text(
            payload,
            owner="backlog workstream",
            fields=("title", "problem", "customer", "opportunity", "product_view", "success_metrics"),
            issues=issues,
        )
        _check_domain_security_policy_posture(payload, owner="backlog workstream", issues=issues)
        dimensions["radar"] = "problem, customer, opportunity, product view, success metrics, and posture adjudicated"
    elif kind == "component":
        _check_required_text(
            payload,
            owner="registry component",
            fields=("component_id", "label", "kind", "path", "responsibility", "boundary"),
            issues=issues,
        )
        _check_required_sequence(
            payload,
            owner="registry component",
            fields=("interfaces", "dependencies", "validation", "risks"),
            issues=issues,
        )
        _check_domain_security_policy_posture(payload, owner="registry component", issues=issues)
        dimensions["registry"] = "ownership, boundary, interface, dependency, proof, and risk posture adjudicated"
    elif kind == "atlas_diagram":
        _check_required_text(
            payload,
            owner="atlas diagram",
            fields=("diagram_id", "slug", "title", "kind", "owner", "summary"),
            issues=issues,
        )
        _check_required_sequence(payload, owner="atlas diagram", fields=("components", "watch_paths"), issues=issues)
        if not _has_any_sequence(payload, ("related_backlog", "related_plans", "related_docs", "related_code")):
            warnings.append("atlas diagram is atlas_first_draft until linked to Radar, plans, docs, or code")
        dimensions["atlas"] = "diagram identity, owner, components, watch paths, and draft/link posture adjudicated"
    elif kind == "casebook_bug":
        _check_required_text(
            payload,
            owner="casebook bug",
            fields=(
                "title",
                "component",
                "severity",
                "reproducibility",
                "impact",
                "environment",
                "failure_signature",
                "trigger_path",
                "ownership",
                "blast_radius",
                "slo_sla_impact",
                "data_risk",
                "security_compliance",
                "invariant_violated",
            ),
            issues=issues,
        )
        _check_domain_security_policy_posture(payload, owner="casebook bug", issues=issues)
        dimensions["casebook"] = "bug evidence, blast radius, data risk, security/compliance, and invariant adjudicated"
    else:
        issues.append(f"unknown governed artifact kind `{artifact_kind}`")

    _check_size(payload, warnings=warnings)
    status = "failed" if issues else "passed"
    summary = (
        f"{kind} artifact is admissible for governed source-truth write."
        if not issues
        else f"{kind} artifact is not admissible for governed source-truth write."
    )
    return GovernedArtifactTribunalDecision(
        artifact_kind=kind,
        status=status,
        version="governed-artifact-tribunal-v1",
        summary=summary,
        dimensions=dimensions,
        issues=tuple(issues),
        warnings=tuple(warnings),
    )


def raise_for_failed_artifact_tribunal(decision: GovernedArtifactTribunalDecision) -> None:
    if decision.passed:
        return
    detail = "; ".join(decision.issues[:5])
    raise ValueError(f"governed artifact Tribunal rejected: {detail}")


def _normalize_kind(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().casefold()).strip("_")
    aliases = {
        "atlas": "atlas_diagram",
        "diagram": "atlas_diagram",
        "bug": "casebook_bug",
        "casebook": "casebook_bug",
    }
    return aliases.get(token, token)


def _check_required_text(
    payload: Mapping[str, Any],
    *,
    owner: str,
    fields: Sequence[str],
    issues: list[str],
) -> None:
    for field in fields:
        values = _text_items(payload.get(field))
        if not values:
            issues.append(f"{owner} must include `{field}`")
            continue
        if all(_placeholder_like(value) for value in values):
            issues.append(f"{owner} `{field}` must not be placeholder text")


def _check_required_sequence(
    payload: Mapping[str, Any],
    *,
    owner: str,
    fields: Sequence[str],
    issues: list[str],
) -> None:
    for field in fields:
        values = [value for value in _text_items(payload.get(field)) if not _placeholder_like(value)]
        if not values:
            issues.append(f"{owner} must include concrete `{field}`")


def _check_domain_security_policy_posture(
    payload: Mapping[str, Any],
    *,
    owner: str,
    issues: list[str],
) -> None:
    text = _joined_text(payload)
    if not _contains_any(text, _RISK_TOKENS):
        issues.append(f"{owner} must assess domain, delivery, or operational risk")
    if not _contains_any(text, _SECURITY_TOKENS):
        issues.append(f"{owner} must assess security posture")
    if not _contains_any(text, _POLICY_TOKENS):
        issues.append(f"{owner} must assess compliance, policy, privacy, accessibility, or safety posture")


def _check_size(payload: Mapping[str, Any], *, warnings: list[str]) -> None:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", _joined_text(payload))
    if len(words) > 1800:
        warnings.append("artifact text is large for one governed record; consider splitting child records")


def _has_any_sequence(payload: Mapping[str, Any], fields: Sequence[str]) -> bool:
    return any(_text_items(payload.get(field)) for field in fields)


def _text_items(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        items: list[str] = []
        for nested in value.values():
            items.extend(_text_items(nested))
        return items
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        for nested in value:
            items.extend(_text_items(nested))
        return items
    token = " ".join(str(value).split()).strip()
    return [token] if token else []


def _joined_text(payload: Mapping[str, Any]) -> str:
    return " ".join(_text_items(payload)).casefold()


def _contains_any(text: str, tokens: Sequence[str]) -> bool:
    return any(token in text for token in tokens)


def _placeholder_like(value: str) -> bool:
    return str(value or "").strip().casefold().rstrip(".") in _PLACEHOLDER_TOKENS


__all__ = [
    "GovernedArtifactTribunalDecision",
    "raise_for_failed_artifact_tribunal",
    "run_governed_artifact_tribunal",
]
