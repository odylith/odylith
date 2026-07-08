"""Registry component previews for confirmed greenfield prewrite gates."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_component_registry_scope
from odylith.runtime.domain_intelligence import greenfield_experience
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.greenfield_apply_diagrams import allocated_diagram_ids
from odylith.runtime.domain_intelligence.greenfield_component_contract import ensure_component_contract
from odylith.runtime.domain_intelligence.greenfield_experience import row_text_tuple
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import active_release_components
from odylith.runtime.domain_intelligence.greenfield_text import join_sentence_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.governance import component_authoring
from odylith.runtime.governance.component_spec_rendering import build_component_spec


def render_prewrite_component_specs(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    backlog_result: Mapping[str, Any],
    program_result: Mapping[str, Any],
) -> dict[str, str]:
    """Render Registry specs in memory for the post-confirm completion gate."""

    specs: dict[str, str] = {}
    for row in component_authoring_prewrite_inputs(
        root=root,
        proposal=proposal,
        release_selector=release_selector,
        backlog_result=backlog_result,
        program_result=program_result,
    ):
        specs[str(row["label"])] = build_component_spec(
            component_id=str(row["component_id"]),
            label=str(row["label"]),
            path=str(row["path"]),
            kind=str(row["kind"]),
            status=str(row["status"]),
            qualification=str(row["qualification"]),
            sources=tuple(str(item) for item in row["sources"]),
            workstreams=tuple(str(item) for item in row["workstreams"]),
            diagrams=tuple(str(item) for item in row["diagrams"]),
            responsibility=str(row["responsibility"]),
            boundary=str(row["boundary"]),
            dependencies=tuple(str(item) for item in row["dependencies"]),
            interfaces=tuple(str(item) for item in row["interfaces"]),
            validation=tuple(str(item) for item in row["validation"]),
            risks=tuple(str(item) for item in row["risks"]),
            implementation_handoff=row["implementation_handoff"] if isinstance(row["implementation_handoff"], Mapping) else None,
            component_contract=row["component_contract"] if isinstance(row["component_contract"], Mapping) else None,
        )
    return specs


def preview_prewrite_components(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    backlog_result: Mapping[str, Any],
    program_result: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Run component authoring Tribunal checks before target writes begin."""

    preview_rows: list[dict[str, Any]] = []
    for row in component_authoring_prewrite_inputs(
        root=root,
        proposal=proposal,
        release_selector=release_selector,
        backlog_result=backlog_result,
        program_result=program_result,
    ):
        created = component_authoring.register_component(
            repo_root=root,
            component_id=str(row["component_id"]),
            label=str(row["label"]),
            path=str(row["path"]),
            kind=str(row["kind"]),
            category="application",
            qualification=str(row["qualification"]),
            owner="repo",
            status=str(row["status"]),
            product_layer="application",
            sources=tuple(str(item) for item in row["sources"]),
            workstreams=tuple(str(item) for item in row["workstreams"]),
            diagrams=tuple(str(item) for item in row["diagrams"]),
            responsibility=str(row["responsibility"]),
            boundary=str(row["boundary"]),
            dependencies=tuple(str(item) for item in row["dependencies"]),
            interfaces=tuple(str(item) for item in row["interfaces"]),
            validation=tuple(str(item) for item in row["validation"]),
            risks=tuple(str(item) for item in row["risks"]),
            implementation_handoff=row["implementation_handoff"] if isinstance(row["implementation_handoff"], Mapping) else None,
            component_contract=row["component_contract"] if isinstance(row["component_contract"], Mapping) else None,
            dry_run=True,
            update_existing=True,
            refresh=False,
        )
        created_payload = created.as_dict()
        if isinstance(row["implementation_handoff"], Mapping):
            created_payload["implementation_handoff"] = dict(row["implementation_handoff"])
        created_payload["authoring_input"] = dict(row)
        created_payload["what_it_is"] = component_authoring._public_what_it_is(  # noqa: SLF001 - prewrite mirrors component_authoring output.
            label=str(row["label"]),
            kind=str(row["kind"]),
            responsibility=str(row["responsibility"]),
        )
        preview_rows.append(created_payload)
    return tuple(preview_rows)


def component_authoring_prewrite_inputs(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    backlog_result: Mapping[str, Any],
    program_result: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Build component-authoring inputs for first-release Registry previews."""

    first_release_workstreams = greenfield_programs.first_release_workstream_ids(
        proposal=proposal,
        created_backlog=backlog_result["created"],
        program_result=program_result,
    )
    diagram_rows = [row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)]
    diagram_ids = allocated_diagram_ids(root, len(diagram_rows), rows=diagram_rows)
    traceability_plan = greenfield_traceability.build_traceability_plan(
        proposal=proposal,
        created_backlog=backlog_result["created"],
        diagram_ids=diagram_ids,
    )
    component_handoffs = greenfield_experience.build_component_handoffs(
        proposal=proposal,
        backlog_result=backlog_result,
        first_release_workstreams=first_release_workstreams,
        program_result=program_result,
        traceability_plan=traceability_plan,
        release_selector=release_selector,
    )
    component_diagram_scope = greenfield_component_registry_scope.build_component_diagram_scope(
        rows=diagram_rows,
        diagram_ids=diagram_ids,
    )
    component_rows = first_release_component_rows(proposal)
    component_dependency_lookup = component_dependency_lookup_for(component_rows)
    inputs: list[dict[str, Any]] = []
    for index, row in enumerate(component_rows):
        key = greenfield_traceability.component_key(row)
        handoff = component_handoffs.get(key, {})
        label = str(row.get("label", "") or row.get("component_id", "")).strip()
        if not label:
            continue
        previous_label = str(component_rows[index - 1].get("label", "")).strip() if index else ""
        next_label = str(component_rows[index + 1].get("label", "")).strip() if index + 1 < len(component_rows) else ""
        contract = ensure_component_contract(
            row,
            proposal=proposal,
            previous_label=previous_label,
            next_label=next_label,
            workstream_title=str(handoff.get("workstream_title", "") or handoff.get("title", "")).strip(),
        )
        responsibility = component_authoring_responsibility(row)
        inputs.append(
            {
                "component_id": str(row.get("component_id", "")).strip(),
                "label": label,
                "path": str(row.get("intended_path", "")).strip(),
                "kind": str(row.get("kind", "service")).strip() or "service",
                "category": "application",
                "status": str(row.get("status", "planned")).strip() or "planned",
                "qualification": str(row.get("qualification", "candidate")).strip() or "candidate",
                "owner": "repo",
                "product_layer": "application",
                "sources": ("user_intent",),
                "workstreams": greenfield_component_registry_scope.registry_component_workstreams(
                    handoff=handoff,
                    fallback=traceability_plan.component_workstreams.get(key, ()),
                ),
                "diagrams": greenfield_component_registry_scope.registry_component_diagrams(
                    row=row,
                    diagram_scope=component_diagram_scope,
                    fallback=traceability_plan.component_diagrams.get(key, ()),
                ),
                "responsibility": responsibility,
                "boundary": str(row.get("boundary", "")).strip(),
                "dependencies": component_dependency_lines(
                    row_text_tuple(row, "dependencies", "depends_on"),
                    lookup=component_dependency_lookup,
                ),
                "interfaces": row_text_tuple(row, "interfaces", "interface_changes"),
                "validation": row_text_tuple(row, "validation", "test_strategy"),
                "risks": component_risk_lines(row, proposal),
                "implementation_handoff": handoff,
                "component_contract": contract,
            }
        )
    return tuple(inputs)


def component_authoring_responsibility(row: Mapping[str, Any]) -> str:
    """Prefer the accepted-intent sentence over normalized contract prose for greenfield specs."""

    for key in ("source_system_description", "responsibility", "boundary"):
        value = _readable_component_sentence(row.get(key))
        if value:
            return value
    return ""


def first_release_component_rows(proposal: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return the component rows eligible for first-release rendering."""

    raw_rows = [row for row in proposal.get("components", []) if isinstance(row, Mapping)]
    rows = [row for row in raw_rows if is_first_release_component(row)]
    return rows or [row for row in active_release_components(raw_rows)]


def is_first_release_component(row: Mapping[str, Any]) -> bool:
    return str(row.get("release_scope", "")).strip().casefold() not in {"deferred", "out_of_scope", "external"}


def component_dependency_lookup_for(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    lookup: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        for value in (row.get("component_id"), row.get("id"), row.get("label"), row.get("name")):
            key = slugify(str(value or ""))
            if key:
                lookup.setdefault(key, row)
    return lookup


def component_dependency_lines(
    values: Sequence[str],
    *,
    lookup: Mapping[str, Mapping[str, Any]],
) -> tuple[str, ...]:
    rows: list[str] = []
    for value in values:
        text = " ".join(str(value or "").split()).strip()
        if not text:
            continue
        dependency = lookup.get(slugify(text))
        if not dependency:
            rows.append(text)
            continue
        label = str(dependency.get("label") or dependency.get("name") or text).strip()
        responsibility = str(dependency.get("responsibility") or dependency.get("boundary") or "").strip()
        if responsibility:
            rows.append(f"Depends on {label} for {_dependency_responsibility_phrase(responsibility)}")
        else:
            rows.append(f"Depends on {label} for the state, behavior, or proof owned by that boundary")
    return unique_text(rows)


def component_risk_lines(row: Mapping[str, Any], _proposal: Mapping[str, Any]) -> tuple[str, ...]:
    local = unique_text(
        [
            *_posture_lines(row, "risks", "domain_risk", "risk_posture"),
            *_posture_lines(row, "security_posture", "security_compliance", "compliance_posture"),
            *_posture_lines(row, "dependency_expectations"),
        ]
    )
    label = str(row.get("label", "") or row.get("component_id", "") or "Component").strip()
    values = list(local)
    posture_text = _component_posture_text(row=row, risk_lines=values)
    if not _has_component_posture(posture_text, _COMPONENT_RISK_TOKENS):
        values.append(_component_operational_risk(row=row, label=label))
    posture_text = _component_posture_text(row=row, risk_lines=values)
    if not _has_component_posture(posture_text, _COMPONENT_SECURITY_TOKENS):
        values.append(_component_security_posture(row=row, label=label))
    posture_text = _component_posture_text(row=row, risk_lines=values)
    if not _has_component_posture(posture_text, _COMPONENT_POLICY_TOKENS):
        values.append(_component_policy_posture(row=row, label=label))
    return unique_text(values)


def _readable_component_sentence(value: Any) -> str:
    text = join_sentence_text(text_values(value, split_scalar=False, split_commas=False, strip_bullets=True))
    text = re.sub(r"\s+", " ", text).strip(" .")
    if len(text.split()) < 4:
        return ""
    lowered = text.casefold()
    if re.search(
        r"\b(?:component planning record|runtime ownership boundary|structured contract below|"
        r"responsibility and keeps it tied|refused domain responsibilities|forbidden runtime authorities)\b",
        lowered,
    ):
        return ""
    if re.match(r"^(?:and|or|their|they|them|it|this|that|who|which|where)\b", lowered):
        return ""
    return text


def _component_posture_text(*, row: Mapping[str, Any], risk_lines: Sequence[str]) -> str:
    values = [
        *risk_lines,
        *row_text_tuple(row, "responsibility"),
        *row_text_tuple(row, "boundary"),
        *row_text_tuple(row, "dependencies", "depends_on"),
        *row_text_tuple(row, "interfaces", "interface_changes"),
        *row_text_tuple(row, "validation", "test_strategy"),
    ]
    return " ".join(values).casefold()


def _has_component_posture(text: str, tokens: Sequence[str]) -> bool:
    return any(token in text for token in tokens)


def _component_operational_risk(*, row: Mapping[str, Any], label: str) -> str:
    boundary = str(row.get("boundary", "") or row.get("responsibility", "")).strip()
    boundary_hint = f" its stated boundary ({boundary})" if boundary else " its stated component boundary"
    return f"Operational risk: {label} must not expand beyond{boundary_hint} without owner review and source-backed proof."


def _component_security_posture(*, row: Mapping[str, Any], label: str) -> str:
    kind = str(row.get("kind", "")).strip().casefold()
    if kind in {"tooling", "test", "harness"}:
        return (
            f"Security posture: {label} uses secret-free fixtures, rejects production credentials, "
            "and keeps live network access outside its proof boundary."
        )
    if kind in {"application", "ui", "frontend", "web"}:
        return (
            f"Security posture: {label} gates operator access and audit identity at its own visible action boundary."
        )
    return (
        f"Security posture: {label} keeps authorization, data access, and ownership checks at its API or module boundary."
    )


def _component_policy_posture(*, row: Mapping[str, Any], label: str) -> str:
    kind = str(row.get("kind", "")).strip().casefold()
    if kind in {"tooling", "test", "harness"}:
        return (
            f"Compliance policy: {label} records deterministic audit evidence and rejects private production data in fixtures."
        )
    if kind in {"application", "ui", "frontend", "web"}:
        return (
            f"Policy posture: {label} preserves accessibility, privacy, audit, and safety semantics for the visible states it owns."
        )
    return (
        f"Compliance policy: {label} keeps audit, privacy, retention, and safety assumptions explicit in its contract tests."
    )


def _dependency_responsibility_phrase(value: str) -> str:
    text = " ".join(str(value or "").split()).strip().rstrip(".")
    if not text:
        return "the state, behavior, or proof owned by that boundary"
    parts = [
        _dependency_clause_phrase(part)
        for part in re.split(r"\s*;\s*", text)
        if part.strip()
    ]
    parts = [part for part in parts if part]
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return f"{', '.join(parts[:-1])}, and {parts[-1]}"


def _dependency_clause_phrase(value: str) -> str:
    text = " ".join(str(value or "").split()).strip().rstrip(".")
    if not text:
        return ""
    head, separator, tail = text.partition(" ")
    verb = head.strip(",:;").casefold()
    gerunds = {
        "assemble": "assembling",
        "assembles": "assembling",
        "bind": "binding",
        "binds": "binding",
        "capture": "capturing",
        "captures": "capturing",
        "compute": "computing",
        "computes": "computing",
        "connect": "connecting",
        "connects": "connecting",
        "derive": "deriving",
        "derives": "deriving",
        "enforce": "enforcing",
        "enforces": "enforcing",
        "fetch": "fetching",
        "fetches": "fetching",
        "hold": "holding",
        "holds": "holding",
        "manage": "managing",
        "manages": "managing",
        "own": "owning",
        "owns": "owning",
        "produce": "producing",
        "produces": "producing",
        "provide": "providing",
        "provides": "providing",
        "record": "recording",
        "records": "recording",
        "render": "rendering",
        "renders": "rendering",
        "serve": "serving",
        "serves": "serving",
        "track": "tracking",
        "tracks": "tracking",
        "validate": "validating",
        "validates": "validating",
    }
    if verb in gerunds and separator:
        return f"{gerunds[verb]} {_gerund_joined_verbs(tail.strip(), gerunds)}"
    return text[:1].lower() + text[1:]


def _gerund_joined_verbs(value: str, gerunds: Mapping[str, str]) -> str:
    pattern = re.compile(
        r"\b(?P<join>and|or)\s+(?P<verb>"
        + "|".join(re.escape(verb) for verb in sorted(gerunds, key=len, reverse=True))
        + r")\b",
        flags=re.IGNORECASE,
    )

    def replace(match: re.Match[str]) -> str:
        joiner = match.group("join")
        verb = match.group("verb").casefold()
        return f"{joiner} {gerunds[verb]}"

    return pattern.sub(replace, value)


def _posture_lines(row: Mapping[str, Any], *keys: str) -> tuple[str, ...]:
    lines: list[str] = []
    for key in keys:
        lines.extend(_posture_value_lines(row.get(key)))
    return unique_text(lines)


def _posture_value_lines(value: Any) -> tuple[str, ...]:
    if isinstance(value, Mapping):
        if "statement" not in value and "mitigation" not in value:
            ignored = {"id", "evidence_tier", "kind"}
            return unique_text(
                line
                for nested_key, nested_value in value.items()
                if str(nested_key) not in ignored
                for line in _posture_value_lines(nested_value)
            )
        statement = join_sentence_text(
            value.get("statement")
            or value.get("risk")
            or value.get("detail")
            or value.get("domain")
            or value.get("security")
            or value.get("policy")
            or value.get("compliance")
        )
        mitigation = join_sentence_text(value.get("mitigation"))
        if statement and mitigation:
            return (f"{statement} Mitigation: {mitigation}",)
        if statement:
            return (statement,)
        ignored = {"id", "evidence_tier", "kind"}
        return unique_text(
            line
            for nested_key, nested_value in value.items()
            if str(nested_key) not in ignored
            for line in _posture_value_lines(nested_value)
        )
    if isinstance(value, (list, tuple, set)):
        return unique_text(line for nested in value for line in _posture_value_lines(nested))
    return text_values(value)


_COMPONENT_RISK_TOKENS = ("risk", "failure", "fallback", "mitigation", "recovery", "degraded", "operational")
_COMPONENT_SECURITY_TOKENS = (
    "security",
    "auth",
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
    "pii",
    "data risk",
)
_COMPONENT_POLICY_TOKENS = (
    "compliance",
    "policy",
    "privacy",
    "retention",
    "audit",
    "regulated",
    "accessibility",
    "public",
    "private",
    "safety",
)


__all__ = [
    "component_authoring_prewrite_inputs",
    "component_authoring_responsibility",
    "component_dependency_lines",
    "component_dependency_lookup_for",
    "component_risk_lines",
    "first_release_component_rows",
    "is_first_release_component",
    "preview_prewrite_components",
    "render_prewrite_component_specs",
]
