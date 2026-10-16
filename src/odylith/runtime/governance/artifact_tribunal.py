"""Deterministic Tribunal gate for single governed artifact writes."""

from __future__ import annotations

from collections.abc import Iterator
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
SOURCE_CUSTODY_CONTRACT_VERSION = "odylith.artifact-source-custody.v2"
_SOURCE_CUSTODY_ATTESTATION = object()
_SOURCE_CUSTODY_FIELDS = frozenset(
    {
        "contract_version",
        "projection_origin",
        "semantic_root",
        "semantic_version",
        "authored_relation_set_sha256",
    }
)


class _VerifiedSourceCustody(Mapping[str, str]):
    """Immutable in-process receipt issued only after upstream source verification."""

    __slots__ = ("_attestation", "_values")

    def __init__(self, values: Mapping[str, str], *, attestation: object) -> None:
        self._values = tuple(values.items())
        self._attestation = attestation

    def __getitem__(self, key: str) -> str:
        return dict(self._values)[key]

    def __iter__(self) -> Iterator[str]:
        return (key for key, _value in self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __deepcopy__(self, _memo: dict[int, Any]) -> _VerifiedSourceCustody:
        return self


def _bind_verified_source_custody(
    *,
    projection_origin: str,
    semantic_root: str,
    semantic_version: str,
    authored_relation_set_sha256: str,
) -> Mapping[str, str]:
    """Issue the Tribunal receipt after the semantic owner verifies its authority."""

    return _VerifiedSourceCustody(
        {
            "contract_version": SOURCE_CUSTODY_CONTRACT_VERSION,
            "projection_origin": projection_origin,
            "semantic_root": semantic_root,
            "semantic_version": semantic_version,
            "authored_relation_set_sha256": authored_relation_set_sha256,
        },
        attestation=_SOURCE_CUSTODY_ATTESTATION,
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
    source_custody: Mapping[str, Any] | None = None,
) -> GovernedArtifactTribunalDecision:
    """Run a zero-provider Tribunal check before a governed artifact write."""

    kind = _normalize_kind(artifact_kind)
    issues: list[str] = []
    warnings: list[str] = []
    dimensions = {
        "latency": "local deterministic gate; no provider, no subagent, no broad scan",
        "human_readability": "bounded fields must be concrete enough for review without oversized prose",
    }
    custody_valid = source_custody_valid(source_custody)
    if source_custody is not None and not custody_valid:
        issues.append("source-custodied artifact adjudication requires a complete typed semantic authority")
    if custody_valid:
        dimensions["typed_authority"] = (
            "issued relation-bound authority context; artifact fidelity remains owned by the authored projection gate"
        )

    if kind == "backlog":
        _check_required_text(
            payload,
            owner="backlog workstream",
            fields=("title", "problem", "customer", "opportunity", "product_view", "success_metrics"),
            issues=issues,
            linguistic_checks=not custody_valid,
        )
        if not custody_valid:
            _check_domain_security_policy_posture(payload, owner="backlog workstream", issues=issues)
        dimensions["radar"] = "problem, customer, opportunity, product view, success metrics, and posture adjudicated"
    elif kind == "component":
        if custody_valid:
            _check_required_text(
                payload,
                owner="registry component",
                fields=("component_id", "label", "kind", "path", "responsibility"),
                issues=issues,
                linguistic_checks=False,
            )
        else:
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
        dimensions["registry"] = (
            "source-custodied identity and owner-bound responsibility adjudicated"
            if custody_valid
            else "ownership, boundary, interface, dependency, proof, and risk posture adjudicated"
        )
    elif kind == "atlas_diagram":
        _check_required_text(
            payload,
            owner="atlas diagram",
            fields=("diagram_id", "slug", "title", "kind", "owner", "summary"),
            issues=issues,
            linguistic_checks=not custody_valid,
        )
        _check_required_sequence(
            payload,
            owner="atlas diagram",
            fields=("components",) if custody_valid else ("components", "watch_paths"),
            issues=issues,
            linguistic_checks=not custody_valid,
        )
        if not _has_any_sequence(payload, ("related_backlog", "related_plans", "related_docs", "related_code")):
            warnings.append("atlas diagram is atlas_first_draft until linked to Radar, plans, docs, or code")
        dimensions["atlas"] = (
            "source-custodied diagram identity, components, and draft posture adjudicated"
            if custody_valid
            else "diagram identity, owner, components, watch paths, and draft/link posture adjudicated"
        )
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
            linguistic_checks=not custody_valid,
        )
        if not custody_valid:
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
        version="governed-artifact-validation-v1",
        summary=summary,
        dimensions=dimensions,
        issues=tuple(issues),
        warnings=tuple(warnings),
    )


def raise_for_failed_artifact_tribunal(decision: GovernedArtifactTribunalDecision) -> None:
    if decision.passed:
        return
    detail = "; ".join(decision.issues[:5])
    raise ValueError(f"governed artifact validation rejected: {detail}")


def _normalize_kind(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().casefold()).strip("_")
    aliases = {
        "atlas": "atlas_diagram",
        "diagram": "atlas_diagram",
        "bug": "casebook_bug",
        "casebook": "casebook_bug",
    }
    return aliases.get(token, token)


def source_custody_valid(value: Mapping[str, Any] | None) -> bool:
    """Return whether a governed artifact carries an issued typed-authority receipt."""

    if (
        not isinstance(value, _VerifiedSourceCustody)
        or value._attestation is not _SOURCE_CUSTODY_ATTESTATION
        or set(value) != _SOURCE_CUSTODY_FIELDS
    ):
        return False
    return (
        value.get("contract_version") == SOURCE_CUSTODY_CONTRACT_VERSION
        and all(
            isinstance(value.get(key), str) and bool(value.get(key))
            for key in ("projection_origin", "semantic_root", "semantic_version")
        )
        and _is_sha256(value.get("authored_relation_set_sha256"))
    )


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _check_required_text(
    payload: Mapping[str, Any],
    *,
    owner: str,
    fields: Sequence[str],
    issues: list[str],
    linguistic_checks: bool = True,
) -> None:
    for field in fields:
        values = _text_items(payload.get(field))
        if not values:
            issues.append(f"{owner} must include `{field}`")
            continue
        if linguistic_checks and all(_placeholder_like(value) for value in values):
            issues.append(f"{owner} `{field}` must not be placeholder text")


def _check_required_sequence(
    payload: Mapping[str, Any],
    *,
    owner: str,
    fields: Sequence[str],
    issues: list[str],
    linguistic_checks: bool = True,
) -> None:
    for field in fields:
        values = _text_items(payload.get(field))
        if linguistic_checks:
            values = [value for value in values if not _placeholder_like(value)]
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
    if len(_joined_text(payload).encode("utf-8")) > 12000:
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
    "SOURCE_CUSTODY_CONTRACT_VERSION",
    "raise_for_failed_artifact_tribunal",
    "run_governed_artifact_tribunal",
    "source_custody_valid",
]
