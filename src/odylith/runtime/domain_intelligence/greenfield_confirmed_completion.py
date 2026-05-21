"""Completion gate for confirmed greenfield project artifacts."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common import display_text
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_component_contract import (
    boundary_from_contract,
    component_contract_issues,
    dependencies_from_contract,
    ensure_component_contract,
    interfaces_from_contract,
    responsibility_from_contract,
    risks_from_contract,
    validation_from_contract,
)
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.domain_intelligence.proposal_validation import collect_host_reasoned_proposal_issues
from odylith.runtime.domain_intelligence.proposal_validation import format_proposal_issue_report
from odylith.runtime.governance import artifact_tribunal


_MAX_COMPLETION_PASSES = 6


def complete_confirmed_proposal(
    proposal: Mapping[str, Any],
    *,
    release_selector: str = "",
) -> dict[str, Any]:
    """Fill deterministic omissions in a confirmed proposal before writes."""

    payload = copy.deepcopy(dict(proposal))
    if not _is_confirmed_greenfield(payload):
        return payload
    last_issues: tuple[str, ...] = ()
    for _pass in range(_MAX_COMPLETION_PASSES):
        changed = False
        changed |= _complete_project_posture(payload)
        changed |= _complete_backlog(payload)
        changed |= _complete_components(payload)
        changed |= _complete_diagrams(payload)
        issues = _preflight_issues(payload, release_selector=release_selector)
        if not issues:
            return payload
        if tuple(issues) == last_issues and not changed:
            break
        last_issues = tuple(issues)
    raise ValueError(format_proposal_issue_report("confirmed completion", list(last_issues)))


def _is_confirmed_greenfield(proposal: Mapping[str, Any]) -> bool:
    intent = proposal.get("intent")
    if not isinstance(intent, Mapping):
        return False
    return (
        str(intent.get("reasoning_mode", "")).strip() == "odylith_confirmed_governed_proposal"
        and str(proposal.get("write_policy", "")).strip() == "confirmed_intent_before_confirmed_create"
    )


def _complete_project_posture(proposal: dict[str, Any]) -> bool:
    changed = False
    risks = proposal.get("risks")
    if not isinstance(risks, list) or not risks:
        proposal["risks"] = [
            _risk_row(
                "RISK-001",
                _title(proposal, "first-path proof can be too weak"),
                (
                    f"If the accepted first path is not proven with visible evidence, {_project_title(proposal)} "
                    f"can produce records that look ready while the product outcome remains untrusted: {_first_path(proposal)}"
                ),
                "Keep release proof tied to the accepted first path, state object, validation output, and reviewer decision.",
            ),
            _risk_row(
                "RISK-002",
                _title(proposal, "safety, privacy, or policy posture can be under-modeled"),
                (
                    f"If access, private data handling, audit, retention, accessibility, safety, and abuse controls "
                    f"are not explicit, {_project_title(proposal)} can cross its accepted proof boundary: {_proof_boundary(proposal)}"
                ),
                "Make domain risk, security posture, and compliance policy visible before any governed record writes.",
            ),
        ]
        changed = True
    posture = proposal.get("security_compliance")
    if not isinstance(posture, Mapping) or not text_values(posture):
        label = _project_title(proposal)
        proposal["security_compliance"] = {
            "domain": (
                f"{label} carries domain risk around the accepted state object, first path, proof boundary, "
                "failure handling, and user decisions made from incomplete evidence."
            ),
            "security": (
                f"Security posture for {label} covers authorization, ownership checks, access control, private data handling, "
                "credential isolation, abuse prevention, and clear recovery behavior."
            ),
            "policy": (
                f"Compliance policy for {label} keeps privacy, audit, retention, accessibility, safety, and review obligations "
                "visible before production claims are made."
            ),
        }
        changed = True
    validation = proposal.get("validation_strategy")
    if not isinstance(validation, list) or len(text_values(validation)) < 3:
        proposal["validation_strategy"] = list(
            unique_text(
                [
                    *(validation if isinstance(validation, list) else []),
                    f"The accepted first path passes end to end: {_first_path(proposal)}",
                    f"The state object can be reconstructed with actor, source, timestamp, and evidence references: {_state_object(proposal)}",
                    f"The proof boundary blocks release readiness when validation, replay, access, privacy, safety, or reviewer evidence is missing: {_proof_boundary(proposal)}",
                ]
            )
        )
        changed = True
    return changed


def _complete_backlog(proposal: dict[str, Any]) -> bool:
    rows = proposal.get("backlog")
    if not isinstance(rows, list):
        return False
    changed = False
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        title = _clean(row.get("title")) or f"{_project_title(proposal)} Workstream {index}"
        if not _clean(row.get("problem")):
            row["problem"] = (
                f"{title} is required because the accepted product cannot be trusted unless the first path, "
                f"state object, evidence, and proof boundary stay connected: {_first_path(proposal)}"
            )
            changed = True
        if not _clean(row.get("customer")):
            row["customer"] = _actor_summary(proposal)
            changed = True
        if not _clean(row.get("opportunity")):
            row["opportunity"] = (
                f"Build the smallest useful product slice for {title}: {_first_path(proposal)}"
            )
            changed = True
        if not _clean(row.get("product_view")):
            row["product_view"] = (
                f"{title} is useful when the user can complete the first path and inspect the resulting state, blockers, and evidence."
            )
            changed = True
        metrics = list(text_values(row.get("success_metrics")))
        if len(metrics) < 3:
            row["success_metrics"] = list(
                unique_text(
                    [
                        *metrics,
                        f"The accepted first path can be exercised end to end: {_first_path(proposal)}",
                        f"{_state_object(proposal)} records success, blocked, stale, and review-needed states.",
                        f"Proof evidence blocks promotion unless it matches the accepted boundary: {_proof_boundary(proposal)}",
                    ]
                )
            )
            changed = True
        if not _clean(row.get("domain_risk")):
            row["domain_risk"] = (
                f"Domain risk: {title} can mislead operators if it loses the accepted product context, state object, "
                f"reviewer evidence, or release proof: {_proof_boundary(proposal)}"
            )
            changed = True
        if not _clean(row.get("security_posture")):
            row["security_posture"] = (
                f"Security posture: {title} keeps authorization, ownership, access control, private data handling, "
                "audit, privacy, retention, accessibility, and safety obligations explicit before promotion."
            )
            changed = True
        if not text_values(row.get("risks")):
            row["risks"] = [
                row["domain_risk"],
                row["security_posture"],
            ]
            changed = True
    return changed


def _complete_components(proposal: dict[str, Any]) -> bool:
    rows = proposal.get("components")
    if not isinstance(rows, list):
        return False
    changed = False
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        label = _component_label(row, index)
        previous_label = _component_label(rows[index - 2], index - 1) if index > 1 and isinstance(rows[index - 2], Mapping) else ""
        next_label = _component_label(rows[index], index + 1) if index < len(rows) and isinstance(rows[index], Mapping) else ""
        contract = ensure_component_contract(
            row,
            proposal=proposal,
            previous_label=previous_label,
            next_label=next_label,
        )
        if row.get("component_contract") != contract:
            row["component_contract"] = contract
            changed = True
        if _component_field_is_weak(row.get("responsibility")):
            row["responsibility"] = responsibility_from_contract(label, contract)
            changed = True
        if _component_field_is_weak(row.get("boundary")):
            row["boundary"] = boundary_from_contract(label, contract)
            changed = True
        if _component_sequence_is_weak(row.get("interfaces")):
            row["interfaces"] = interfaces_from_contract(contract)
            changed = True
        else:
            changed |= _ensure_list(row, "interfaces", _component_interfaces(row, label, contract))
        if _component_sequence_is_weak(row.get("dependencies")):
            row["dependencies"] = dependencies_from_contract(contract)
            changed = True
        else:
            changed |= _ensure_list(row, "dependencies", _component_dependencies(row, label, proposal, contract))
        if _component_sequence_is_weak(row.get("validation")):
            row["validation"] = validation_from_contract(contract)
            changed = True
        else:
            changed |= _ensure_list(row, "validation", _component_validation(row, label, proposal, contract))
        if _component_sequence_is_weak(row.get("risks")):
            row["risks"] = risks_from_contract(label, contract)
            changed = True
        else:
            changed |= _ensure_list(row, "risks", _component_risks(row, label, proposal, contract))
        changed |= _ensure_text(row, "status", "planned")
        changed |= _ensure_text(row, "qualification", "candidate")
        changed |= _ensure_text(row, "evidence_tier", "user_intent")
    return changed


def _complete_diagrams(proposal: dict[str, Any]) -> bool:
    rows = proposal.get("diagrams")
    if not isinstance(rows, list):
        return False
    changed = False
    component_ids = [
        _clean(row.get("component_id"))
        for row in proposal.get("components", [])
        if isinstance(row, Mapping) and _clean(row.get("component_id"))
    ]
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        slug = _clean(row.get("slug")) or f"{_slug_title(proposal)}-diagram-{index}"
        changed |= _ensure_text(row, "slug", slug)
        changed |= _ensure_text(row, "title", f"{_project_title(proposal)} Diagram {index}")
        changed |= _ensure_text(row, "kind", "flowchart")
        changed |= _ensure_text(row, "summary", f"Shows how {_project_title(proposal)} preserves first-path state, evidence, and proof.")
        changed |= _ensure_text(row, "owner", "repo")
        changed |= _ensure_text(row, "link_state", "atlas_first_draft")
        if not text_values(row.get("watch_paths")):
            row["watch_paths"] = [
                "odylith/radar/source",
                "odylith/registry/source",
            ]
            changed = True
        if not text_values(row.get("related_components")) and component_ids:
            row["related_components"] = component_ids[:4]
            changed = True
    return changed


def _preflight_issues(proposal: Mapping[str, Any], *, release_selector: str) -> list[str]:
    issues: list[str] = []
    issues.extend(collect_host_reasoned_proposal_issues(proposal))
    issues.extend(component_contract_issues(proposal))
    selector = greenfield_programs.proposal_release_selector(proposal, release_selector)
    tribunal = run_greenfield_tribunal(proposal, release_selector=selector)
    issues.extend(tribunal.issues)
    issues.extend(_artifact_issues(proposal))
    return list(unique_text(issues))


def _artifact_issues(proposal: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    for index, row in enumerate(_mapping_rows(proposal.get("backlog")), start=1):
        decision = artifact_tribunal.run_governed_artifact_tribunal(
            artifact_kind="backlog",
            payload={
                "title": row.get("title", ""),
                "problem": row.get("problem", ""),
                "customer": row.get("customer", ""),
                "opportunity": row.get("opportunity", ""),
                "product_view": row.get("product_view", ""),
                "success_metrics": row.get("success_metrics", ""),
                "risks": [row.get("domain_risk", ""), row.get("security_posture", ""), row.get("risks", "")],
                "validation": row.get("validation", ""),
            },
        )
        issues.extend(f"backlog row {index}: {issue}" for issue in decision.issues)
    for index, row in enumerate(_mapping_rows(proposal.get("components")), start=1):
        decision = artifact_tribunal.run_governed_artifact_tribunal(
            artifact_kind="component",
            payload={
                "component_id": row.get("component_id", ""),
                "label": row.get("label", ""),
                "path": row.get("intended_path", "") or row.get("path", ""),
                "kind": row.get("kind", ""),
                "responsibility": row.get("responsibility", ""),
                "boundary": row.get("boundary", ""),
                "interfaces": row.get("interfaces", ""),
                "dependencies": row.get("dependencies", ""),
                "validation": row.get("validation", ""),
                "risks": row.get("risks", ""),
            },
        )
        issues.extend(f"component row {index}: {issue}" for issue in decision.issues)
    for index, row in enumerate(_mapping_rows(proposal.get("diagrams")), start=1):
        decision = artifact_tribunal.run_governed_artifact_tribunal(
            artifact_kind="atlas_diagram",
            payload={
                "diagram_id": row.get("diagram_id", "") or f"DRAFT-{index:03d}",
                "slug": row.get("slug", ""),
                "title": row.get("title", ""),
                "kind": row.get("kind", ""),
                "owner": row.get("owner", "repo"),
                "summary": row.get("summary", ""),
                "components": row.get("components", "") or row.get("related_components", ""),
                "watch_paths": row.get("watch_paths", ""),
                "related_backlog": row.get("related_backlog", "") or row.get("related_diagrams", ""),
                "related_code": row.get("related_code", ""),
            },
        )
        issues.extend(f"diagram row {index}: {issue}" for issue in decision.issues)
    return issues


def _component_interfaces(row: Mapping[str, Any], label: str, contract: Mapping[str, Any]) -> list[str]:
    return interfaces_from_contract(contract)


def _component_dependencies(
    row: Mapping[str, Any],
    label: str,
    proposal: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> list[str]:
    return dependencies_from_contract(contract)


def _component_validation(
    row: Mapping[str, Any],
    label: str,
    proposal: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> list[str]:
    return validation_from_contract(contract)


def _component_risks(
    row: Mapping[str, Any],
    label: str,
    proposal: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> list[str]:
    values = risks_from_contract(label, contract)
    proof = _proof_boundary(proposal)
    first_path = _first_path(proposal)
    state_object = _state_object(proposal)
    context = _best_context_line(row=row, proposal=proposal)
    values.append(
        f"Operational mitigation: {label} must expose local blockers and recovery evidence before release readiness can trust {state_object}: {first_path}"
    )
    if context:
        values.append(f"Accepted-intent constraint: {label} must preserve this risk or policy condition: {context}")
    return list(unique_text(values))


def _best_context_line(*, row: Mapping[str, Any], proposal: Mapping[str, Any]) -> str:
    component_words = _keywords([row.get("label", ""), row.get("responsibility", ""), row.get("boundary", "")])
    candidates = _context_candidates(proposal)
    scored: list[tuple[int, str]] = []
    for candidate in candidates:
        words = _keywords([candidate])
        overlap = len(component_words & words)
        risk_bonus = 3 if _riskish(candidate) else 0
        scored.append((overlap + risk_bonus, candidate))
    scored.sort(key=lambda item: (-item[0], len(item[1])))
    return scored[0][1] if scored and scored[0][0] > 0 else ""


def _context_candidates(proposal: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    values.extend(text_values(proposal.get("assumptions")))
    values.extend(text_values(proposal.get("open_questions")))
    values.extend(text_values(proposal.get("risks")))
    values.extend(text_values(proposal.get("security_compliance")))
    values.extend(text_values(proposal.get("validation_strategy")))
    intelligence = proposal.get("project_intelligence")
    if isinstance(intelligence, Mapping):
        for key in ("constraints", "risks", "validation_obligations", "change_model", "invalidation_rules"):
            values.extend(text_values(intelligence.get(key)))
    return [_sentence(value, limit=260) for value in unique_text(values) if _clean(value)]


def _riskish(value: str) -> bool:
    text = value.casefold()
    return any(
        token in text
        for token in (
            "risk",
            "privacy",
            "safety",
            "consent",
            "access",
            "retention",
            "audit",
            "confidence",
            "blocked",
            "failure",
            "security",
            "compliance",
            "policy",
            "uncertainty",
            "claim",
        )
    )


def _keywords(values: Sequence[Any]) -> set[str]:
    words: set[str] = set()
    for value in values:
        for raw in str(value or "").replace("_", " ").replace("-", " ").split():
            word = "".join(char for char in raw.casefold() if char.isalnum())
            if len(word) >= 4:
                words.add(word)
    return words


def _component_field_is_weak(value: Any) -> bool:
    text = _clean(value).casefold()
    if not text:
        return True
    generic_markers = (
        "responsibility and keeps it tied",
        "accepted first path",
        "assigned state, command, evidence",
        "records review evidence",
        "this component boundary",
        "first implementation plan must name",
    )
    return any(marker in text for marker in generic_markers) or len(text.split()) < 6


def _component_sequence_is_weak(value: Any) -> bool:
    rows = list(text_values(value))
    if not rows:
        return True
    text = " ".join(_clean(row).casefold() for row in rows)
    generic_markers = (
        "command, query, event, or visible-state contract",
        "normal path, blocked path",
        "accepted input, produced state",
        "first implementation plan must name",
        "release proof checks this component",
    )
    return any(marker in text for marker in generic_markers)


def _ensure_list(row: dict[str, Any], key: str, defaults: Sequence[str]) -> bool:
    existing = list(text_values(row.get(key)))
    merged = list(unique_text([*existing, *defaults]))
    if existing == merged and existing:
        return False
    row[key] = merged
    return True


def _ensure_text(row: dict[str, Any], key: str, default: str) -> bool:
    if _clean(row.get(key)):
        return False
    row[key] = default
    return True


def _mapping_rows(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, Mapping)]


def _risk_row(identifier: str, title: str, statement: str, mitigation: str) -> dict[str, str]:
    return {
        "id": identifier,
        "title": title,
        "statement": statement,
        "severity": "high",
        "mitigation": mitigation,
    }


def _component_label(row: Mapping[str, Any], index: int) -> str:
    return _clean(row.get("label")) or _clean(row.get("component_id")) or f"Component {index}"


def _title(proposal: Mapping[str, Any], suffix: str) -> str:
    return f"{_project_title(proposal)} {suffix}"


def _project_title(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return _clean(intent.get("title")) if isinstance(intent, Mapping) else "Confirmed Project"


def _slug_title(proposal: Mapping[str, Any]) -> str:
    return "-".join(word for word in _project_title(proposal).casefold().replace("_", " ").split() if word) or "confirmed-project"


def _first_path(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return _sentence(intent.get("first_path") if isinstance(intent, Mapping) else "", fallback="the accepted first path")


def _proof_boundary(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return _sentence(intent.get("proof_boundary") if isinstance(intent, Mapping) else "", fallback="the accepted proof boundary")


def _state_object(proposal: Mapping[str, Any]) -> str:
    intelligence = proposal.get("project_intelligence")
    if isinstance(intelligence, Mapping):
        for value in text_values(intelligence.get("ontology")):
            if "state object:" in value.casefold():
                return _sentence(value.split(":", 1)[1], fallback="the accepted state object")
    return "the accepted state object"


def _actor_summary(proposal: Mapping[str, Any]) -> str:
    intelligence = proposal.get("project_intelligence")
    if isinstance(intelligence, Mapping):
        actors = list(text_values(intelligence.get("operators")))[:2]
        if actors:
            return _sentence("; ".join(actors), limit=280)
    return f"{_project_title(proposal)} users, reviewers, owners, and release decision makers"


def _fragment(value: Any, *, fallback: str, limit: int = 180) -> str:
    return _sentence(value, fallback=fallback, limit=limit).rstrip(".")


def _sentence(value: Any, *, fallback: str = "", limit: int = 320) -> str:
    text = _clean(value) or fallback
    if not text:
        return ""
    text = display_text.strip_inline_markdown_emphasis_tokens(text).replace("`", "")
    text = " ".join(text.split()).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
        text = _trim_incomplete_tail(text)
        text = text.rstrip(" ,;:")
    if text and text[-1] not in ".!?":
        text += "."
    return text


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _trim_incomplete_tail(value: str) -> str:
    words = value.split()
    while words and words[-1].casefold().strip(".,;:") in {"and", "or", "to", "with", "for", "from", "of", "the", "a", "an"}:
        words.pop()
    return " ".join(words)


__all__ = ["complete_confirmed_proposal"]
