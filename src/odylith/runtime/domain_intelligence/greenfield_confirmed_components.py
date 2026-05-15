"""Component and project-brief helpers for confirmed greenfield proposals."""

from __future__ import annotations

import re
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import (
    confirmed_system_description,
    confirmed_system_name,
)


_STOPWORDS = {
    "a",
    "an",
    "and",
    "app",
    "application",
    "build",
    "create",
    "for",
    "from",
    "in",
    "me",
    "of",
    "on",
    "platform",
    "product",
    "project",
    "repo",
    "system",
    "the",
    "to",
    "tool",
    "with",
}


def domain_label(title: str, prompt: str) -> str:
    source = title or prompt or "Greenfield Project"
    words = []
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", source):
        token = raw.strip("-_")
        if not token or token.casefold() in _STOPWORDS:
            continue
        words.append(token)
    if not words:
        words = ["Greenfield", "Workflow"]
    selected = words[:4] if len(words) <= 4 else words[:3]
    return " ".join(_title_word(word) for word in selected)


def shell_quote(value: str) -> str:
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def confirmed_components(
    *,
    label: str,
    label_slug: str,
    internal_systems: list[str] | None = None,
    first_path: str = "",
) -> list[dict[str, Any]]:
    if not internal_systems:
        raise ValueError(
            "confirmed greenfield components require internal product systems from the accepted Product Intent Confirmation; "
            "generic component fallback is disabled."
        )
    return _confirmed_system_components(
        label=label,
        label_slug=label_slug,
        internal_systems=internal_systems,
        first_path=first_path,
    )


def confirmed_project_brief(
    *,
    label: str,
    prompt: str,
    release: str,
    state_object: str,
    evidence_record: str,
    product_story: str = "",
    first_path: str = "",
    proof_boundary: str = "",
    human_actors: list[str] | None = None,
    internal_systems: list[str] | None = None,
    external_systems: list[str] | None = None,
    assumptions: list[str] | None = None,
    ambiguities: list[str] | None = None,
    non_goals: list[str] | None = None,
) -> dict[str, Any]:
    label_lower = label.lower()
    actor_summary = _join_domain_items(human_actors) or f"the first {label_lower} operator and reviewer"
    internal_summary = _join_domain_items(internal_systems) or f"{state_object.lower()} ownership and {evidence_record.lower()} review"
    external_summary = _join_domain_items(external_systems) or "fixture-backed or deferred external systems"
    story = product_story or (
        f"{label} turns the confirmed request into one usable workflow with named users, owned state, and reviewable proof."
    )
    first = first_path or f"The first release proves one {label_lower} workflow from intake through state update and evidence review."
    proof = proof_boundary or f"Release {release} succeeds only when {state_object.lower()} and {evidence_record.lower()} can be reviewed together."
    non_goal_summary = _join_domain_items(non_goals) or "wider automation, live irreversible integrations, and production scaling"
    return {
        "schema_version": "odylith.greenfield.project_brief.v1",
        "purpose": story,
        "operating_principle": (
            f"Every release {release} claim must stay attached to the user capability, domain state, source evidence, "
            "and proof boundary accepted in the Product Intent Confirmation."
        ),
        "project_outcome": proof,
        "blueprint_sections": [
            {
                "section": "Product story",
                "must_capture": story,
                "why_it_matters": f"Readers need to understand the product, user, problem, and real-world outcome before {label_lower} implementation boundaries appear.",
            },
            {
                "section": "First workflow",
                "must_capture": first,
                "why_it_matters": "A narrow workflow keeps the first release testable and prevents broad platform drift.",
            },
            {
                "section": "State and ownership",
                "must_capture": f"{state_object} changes through the first journey; {internal_summary} own the domain records needed to trust it.",
                "why_it_matters": "Clear ownership prevents silent state changes and unclear accountability.",
            },
            {
                "section": "Proof obligations",
                "must_capture": proof,
                "why_it_matters": "Release readiness depends on evidence rather than persuasive prose.",
            },
            {
                "section": "Actors and systems",
                "must_capture": f"Human actors: {actor_summary}. External systems: {external_summary}.",
                "why_it_matters": "Actor and system boundaries keep user value separate from implementation mechanics.",
            },
        ],
        "customization_options": [
            _brief_option("D1", "First user", f"Confirm the first human actors: {actor_summary}.", "Changes workflow steps and permission expectations."),
            _brief_option("D2", "State object", f"Confirm whether {state_object.lower()} is the right object to version.", "Changes storage ownership and replay proof."),
            _brief_option("D3", "Evidence level", f"Confirm the proof boundary: {proof}", "Changes security posture and release confidence."),
            _brief_option("D4", "External systems", f"Confirm whether release {release} needs {external_summary}.", "Changes adapters, credentials, and failure modes."),
            _brief_option("D5", "Release ambition", f"Keep {release} to the accepted first workflow and non-goals: {non_goal_summary}.", "Changes workstream depth and validation cost."),
        ],
        "customization_prompts": [
            f"Revise the {label_lower} story if the first user, workflow, or state object is wrong.",
            f"Add or remove an external source only if the first workflow cannot be trusted without it: {external_summary}.",
            f"Tighten the {label_lower} proof bar so release readiness depends on the accepted proof boundary.",
        ],
        "pre_coding_checkpoints": [
            _checkpoint("Product story accepted", f"Does the {label_lower} story name the user, problem, workflow, and non-goals?"),
            _checkpoint("State ownership accepted", f"Does one component own {state_object.lower()} and its version history?"),
            _checkpoint("Evidence path accepted", f"Can reviewers inspect {evidence_record.lower()} without trusting implementation prose?"),
            _checkpoint("Release proof accepted", f"Do the {release} gates block promotion when {label_lower} proof is missing?"),
        ],
        "coding_readiness_gates": [
            f"The accepted product story is present before implementation planning: {story}",
            f"The first workflow is accepted in domain language: {first}",
            f"The {label_lower} components come from internal product systems named in the Product Intent Confirmation: {internal_summary}.",
            f"Release {release} has validation gates for success, failure, replay, access, and review evidence.",
            f"External dependencies for {label_lower} are fixture-backed, sandboxed, source-backed, or explicitly deferred.",
        ],
        "host_independent_paths": [
            {
                "path": "Confirm product intent",
                "command": f"odylith greenfield propose --repo-root . --prompt {shell_quote(prompt)}",
                "works_in": "shell, Codex, Claude Code",
                "use_when": "Use before records are written so the operator can confirm or edit the interpretation.",
            },
            {
                "path": "Create confirmed records",
                "command": f"odylith greenfield create --repo-root . --prompt {shell_quote(prompt)} --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release {release}",
                "works_in": "shell, Codex, Claude Code",
                "use_when": "Use after writing the already-shown Product Intent Confirmation to the intent file so Odylith builds from the confirmed narrative.",
            },
            {
                "path": "Explicit file review",
                "command": f"odylith greenfield propose --repo-root . --prompt {shell_quote(prompt)} --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm-intent --format json",
                "works_in": "shell, Codex, Claude Code",
                "use_when": "Use only when a reviewer explicitly asks to inspect the apply-ready JSON before apply.",
            },
        ],
}


def _confirmed_system_components(
    *,
    label: str,
    label_slug: str,
    internal_systems: list[str],
    first_path: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    path_slug = _path_slug(label_slug)
    for index, system in enumerate(internal_systems, start=1):
        name = confirmed_system_name(system)
        description = confirmed_system_description(system)
        component_slug = slugify(name) or f"{label_slug}-component-{index}"
        if not component_slug.startswith(label_slug) and len(component_slug.split("-")) <= 2:
            component_id = _component_id(label_slug, component_slug)
        else:
            component_id = component_slug
        kind = _system_kind(name, description)
        responsibility = _responsibility(name=name, description=description, label=label)
        rows.append(
            {
                "component_id": _unique_component_id(component_id, rows, index),
                "label": _component_label(name, kind),
                "kind": kind,
                "intended_path": f"src/{path_slug}/{_path_slug(component_slug)}",
                "responsibility": responsibility,
                "boundary": _boundary(name=name, description=description, label=label, kind=kind),
                "dependencies": _dependencies(name=name, description=description, label=label, prior=rows),
                "interfaces": _interfaces(name=name, description=description, first_path=first_path),
                "validation": _validation(name=name, description=description, first_path=first_path),
                "status": "planned",
                "qualification": "candidate",
                "evidence_tier": "user_intent",
            }
        )
    return rows


def _system_kind(name: str, description: str) -> str:
    text = f"{name} {description}".casefold()
    if any(token in text for token in ("web", "ui", "surface", "mobile", "portal", "client", "dashboard")):
        return "client"
    if any(token in text for token in ("adapter", "provider", "integration", "connector", "source", "import")):
        return "adapter"
    return "service"


def _component_label(name: str, kind: str) -> str:
    name = _title_phrase(name)
    if kind == "client" and not re.search(r"\b(surface|client|ui|portal|dashboard|app)\b", name, re.IGNORECASE):
        return f"{name} Surface"
    if kind == "adapter" and "adapter" not in name.casefold():
        return f"{name} Adapter"
    if kind == "service" and not re.search(r"\b(service|ledger|registry|store|trail|linker|engine|core|review|tracker|planner|evaluator)\b", name, re.IGNORECASE):
        return f"{name} Service"
    return name


def _title_phrase(value: str) -> str:
    words = []
    for word in str(value or "").split():
        words.append(_title_word(word))
    return " ".join(words)


def _responsibility(*, name: str, description: str, label: str) -> str:
    detail = _strip_ownership_verb(description) or f"the {name.lower()} role in the accepted {label} first release"
    return f"{name} owns {detail[:1].lower() + detail[1:] if detail else detail}."


def _boundary(*, name: str, description: str, label: str, kind: str) -> str:
    if kind == "client":
        return f"{name} owns user interaction and visible state for {label}; domain rules stay with the product systems it calls."
    if kind == "adapter":
        return f"{name} owns external-system translation and provenance for {label}; it does not own the external source of truth."
    detail = _strip_ownership_verb(description) or f"the {label} domain responsibility named by the confirmed intent"
    return f"{name} owns {detail}; it does not own unrelated product decisions or external-provider truth."


def _dependencies(*, name: str, description: str, label: str, prior: list[dict[str, Any]]) -> list[str]:
    deps = [f"Depends on the accepted {label} Product Intent Confirmation for user, problem, first workflow, and proof boundary."]
    if prior:
        deps.append(f"Coordinates with {prior[0]['label']} where the first workflow crosses component boundaries.")
    if description:
        deps.append(f"Receives or produces domain information described as: {_strip_ownership_verb(description)}.")
    return deps


def _interfaces(*, name: str, description: str, first_path: str) -> list[str]:
    path = first_path or "the accepted first workflow"
    detail = _strip_ownership_verb(description) or f"the {name.lower()} responsibility"
    return [f"Expose operations for {detail} required by: {path}"]


def _validation(*, name: str, description: str, first_path: str) -> list[str]:
    detail = _strip_ownership_verb(description) or name
    path = first_path or "the accepted first workflow"
    return [f"Contract proof shows {detail} supports {path} with traceable inputs, outputs, and failure behavior."]


def _unique_component_id(component_id: str, existing: list[dict[str, Any]], index: int) -> str:
    used = {str(row.get("component_id", "")) for row in existing}
    candidate = component_id
    while candidate in used:
        index += 1
        candidate = f"{component_id}-{index}"
    return candidate


def _strip_ownership_verb(value: str) -> str:
    return re.sub(r"^(?:owns?|records?|stores?|tracks?|links?|assembles?|evaluates?|derives?|serves?)\s+", "", str(value or "").strip(), flags=re.IGNORECASE)


def _join_domain_items(items: list[str] | None, *, limit: int = 4) -> str:
    values = [str(item).strip().rstrip(".") for item in (items or []) if str(item).strip()]
    if not values:
        return ""
    selected = values[:limit]
    suffix = "" if len(values) <= limit else f", plus {len(values) - limit} more"
    return "; ".join(selected) + suffix


def _title_word(value: str) -> str:
    lower = value.casefold()
    if lower in {"ai", "api", "crm", "gis", "iot", "llm", "ml", "pwa", "ui", "ux"}:
        return lower.upper()
    return value[:1].upper() + value[1:]


def _component_id(label_slug: str, suffix: str) -> str:
    return slugify(f"{label_slug}-{suffix}")


def _path_slug(label_slug: str) -> str:
    return slugify(label_slug).replace("-", "_") or "greenfield"


def _brief_option(identifier: str, decision: str, recommended: str, impact: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "decision": decision,
        "recommended": recommended,
        "choices": ["accept default", "revise before apply", "defer from first release"],
        "impact": impact,
    }


def _checkpoint(name: str, question: str) -> dict[str, str]:
    return {
        "checkpoint": name,
        "operator_question": question,
        "done_when": "The answer is visible in the accepted proposal and reflected in validation gates.",
    }


__all__ = [
    "confirmed_components",
    "confirmed_project_brief",
    "domain_label",
    "shell_quote",
]
