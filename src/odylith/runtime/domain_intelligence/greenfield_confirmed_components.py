"""Component and project-brief helpers for confirmed greenfield proposals."""

from __future__ import annotations

import re
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.common import display_text
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
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

_GENERIC_COMPONENT_ROLE_PREFIXES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^primary\s+user\b", re.IGNORECASE), "User"),
    (re.compile(r"^end[-\s]*user\s+advocate\b", re.IGNORECASE), "User Advocacy"),
    (re.compile(r"^project\s+operator\b", re.IGNORECASE), "Product Operations"),
    (re.compile(r"^workflow\s+operator\b", re.IGNORECASE), "Workflow Operations"),
    (re.compile(r"^operator\b", re.IGNORECASE), "Operations"),
    (re.compile(r"^maintainer\b", re.IGNORECASE), "Maintenance"),
    (re.compile(r"^domain\s+reviewer\b", re.IGNORECASE), "Domain Review"),
    (re.compile(r"^risk\s+reviewer\b", re.IGNORECASE), "Risk Review"),
    (re.compile(r"^proof\s+reviewer\b", re.IGNORECASE), "Proof Review"),
    (re.compile(r"^reviewer\b", re.IGNORECASE), "Review"),
    (re.compile(r"^implementation\s+owner\b", re.IGNORECASE), "Implementation Ownership"),
    (re.compile(r"^evidence\s+owner\b", re.IGNORECASE), "Evidence Ownership"),
    (re.compile(r"^build\s+owner\b", re.IGNORECASE), "Build Ownership"),
)


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
    problem: str = "",
    human_actors: list[str] | None = None,
    internal_systems: list[str] | None = None,
    external_systems: list[str] | None = None,
    assumptions: list[str] | None = None,
    ambiguities: list[str] | None = None,
    non_goals: list[str] | None = None,
) -> dict[str, Any]:
    label_lower = label.lower()
    state_label = _state_object_label(state_object, fallback=f"{label} state")
    evidence_label = _state_object_label(evidence_record, fallback=evidence_record)
    actor_summary = _join_domain_items(human_actors) or f"the first {label_lower} operator and reviewer"
    internal_summary = _join_system_names(internal_systems) or f"{state_label.lower()} ownership and {evidence_label.lower()} review"
    external_summary = _join_domain_items(external_systems) or "explicitly deferred external systems"
    story = product_story or (
        f"{label} turns the confirmed request into one usable product path with named users, owned state, and reviewable proof."
    )
    story_brief = _brief_clause(story, limit=420)
    first = _brief_clause(
        first_path or f"The first release proves one {label_lower} path from intake through state update and evidence review.",
        limit=300,
    )
    proof = _brief_clause(
        proof_boundary or f"Release {release} succeeds only when {state_label.lower()} and {evidence_label.lower()} can be reviewed together.",
        limit=300,
    )
    non_goal_summary = _join_domain_items(non_goals) or "wider automation, live irreversible integrations, and production scaling"
    return {
        "schema_version": "odylith.greenfield.project_brief.v1",
        "purpose": _purpose_text(story=story, problem=problem, first=first),
        "operating_principle": (
            f"Every release {release} claim must stay attached to the user capability, domain state, source evidence, "
            "and proof boundary accepted in the product direction."
        ),
        "project_outcome": proof,
        "blueprint_sections": [
            {
                "section": "Product story",
                "must_capture": story_brief,
                "why_it_matters": f"Readers need to understand the product, user, problem, and real-world outcome before {label_lower} implementation boundaries appear.",
            },
            {
                "section": "First path",
                "must_capture": first,
                "why_it_matters": "A narrow first path keeps the first release testable and prevents broad platform drift.",
            },
            {
                "section": "State and ownership",
                "must_capture": f"{state_label} changes through the first journey; {internal_summary} own the domain records needed to trust it.",
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
            _brief_option("D1", "First user", f"Confirm the first human actors: {actor_summary}.", "Changes path steps and permission expectations."),
            _brief_option("D2", "State object", f"Confirm this as the versioned state object: {state_label}.", "Changes storage ownership and replay proof."),
            _brief_option("D3", "Evidence level", f"Confirm the proof boundary: {proof}", "Changes security posture and release confidence."),
            _brief_option("D4", "External systems", f"Confirm whether release {release} needs {external_summary}.", "Changes adapters, credentials, and failure modes."),
            _brief_option("D5", "Release ambition", f"Keep {release} to the accepted first path and non-goals: {non_goal_summary}.", "Changes planning depth and validation cost."),
        ],
        "customization_prompts": [
            f"Revise the {label_lower} story if the first user, first path, or state object is wrong.",
            "Decide whether the first release needs a live external source, a simulated source, or an explicitly deferred integration.",
            f"Tighten the {label_lower} proof bar so release readiness depends on the accepted proof boundary.",
        ],
        "pre_coding_checkpoints": [
            _checkpoint("Product story accepted", f"Does the {label_lower} story name the user, problem, first path, and non-goals?"),
            _checkpoint("State ownership accepted", f"Does one component own {state_label.lower()} and its version history?"),
            _checkpoint("Evidence path accepted", f"Can reviewers inspect {evidence_label.lower()} without trusting implementation prose?"),
            _checkpoint("Release proof accepted", f"Do the {release} gates block promotion when {label_lower} proof is missing?"),
        ],
        "coding_readiness_gates": [
            f"The accepted product story is present before implementation planning: {story_brief}",
            f"The first path is accepted in domain language: {first}",
            f"The {label_lower} components come from product systems named in the accepted product direction: {internal_summary}.",
            f"Release {release} has validation gates for success, failure, replay, access, and review evidence.",
            f"External dependencies for {label_lower} are simulated, sandboxed, source-backed, or explicitly deferred.",
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
                "use_when": "Use after writing the already-shown confirmation to the intent file so the records build from the accepted narrative.",
            },
            {
                "path": "Explicit file review",
                "command": f"odylith greenfield propose --repo-root . --prompt {shell_quote(prompt)} --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm-intent --format json",
                "works_in": "shell, Codex, Claude Code",
                "use_when": "Use only when a reviewer explicitly asks for a governed proposal audit artifact.",
            },
        ],
}


def _purpose_text(*, story: str, problem: str, first: str) -> str:
    story_text = _plain_text(story).strip(" .")
    problem_text = _brief_clause(problem, limit=260)
    if problem_text:
        return f"{story_text}. Problem to solve: {problem_text}."
    first_text = _brief_clause(first, limit=240)
    if first_text:
        return f"{story_text}. Without this first path, users cannot trust the product result: {first_text}."
    return story_text


def _confirmed_system_components(
    *,
    label: str,
    label_slug: str,
    internal_systems: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    path_slug = _path_slug(label_slug)
    for index, system in enumerate(internal_systems, start=1):
        name = system_component_name(confirmed_system_name(system))
        description = confirmed_system_description(system)
        component_slug = slugify(name) or f"{label_slug}-component-{index}"
        if not component_slug.startswith(label_slug) and len(component_slug.split("-")) <= 2:
            component_id = _component_id(label_slug, component_slug)
        else:
            component_id = component_slug
        kind = _system_kind(name, description)
        responsibility = _responsibility(name=name, description=description)
        rows.append(
            {
                "component_id": _unique_component_id(component_id, rows, index),
                "label": _component_label(name, kind),
                "kind": kind,
                "intended_path": f"src/{path_slug}/{_path_slug(component_slug)}",
                "responsibility": responsibility,
                "boundary": _boundary(name=name, description=description, kind=kind),
                "dependencies": _dependencies(name=name, description=description, prior=rows),
                "interfaces": _interfaces(name=name, description=description, kind=kind),
                "validation": _validation(name=name, description=description, kind=kind),
                "status": "planned",
                "qualification": "candidate",
                "evidence_tier": "user_intent",
            }
        )
    return rows


def system_component_name(value: str) -> str:
    """Convert actor-placeholder prefixes into capability names for component records."""

    name = _plain_text(value).strip(" .:-")
    if not name:
        return ""
    for pattern, replacement in _GENERIC_COMPONENT_ROLE_PREFIXES:
        match = pattern.match(name)
        if not match:
            continue
        rest = name[match.end() :].strip(" .:-")
        if not rest:
            return replacement
        if rest.casefold().startswith(replacement.casefold()):
            return _sentence_case(rest)
        return f"{replacement} {rest}"
    return name


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
    raw_words = str(value or "").split()
    for index, word in enumerate(raw_words):
        words.append(_title_word(word, first=index == 0, previous=raw_words[index - 1] if index else ""))
    return " ".join(words)


def _responsibility(*, name: str, description: str) -> str:
    action, _rationale = _system_action(description)
    if action:
        if looks_like_finite_action(action):
            if re.match(r"^\s*owns?\b", action, flags=re.IGNORECASE):
                owned = _strip_ownership_verb(action).strip(" .")
                if owned and owned.casefold() != action.casefold():
                    return _ensure_responsibility_depth(f"Owns {owned}")
            return _ensure_responsibility_depth(_sentence_case(action))
        detail = _strip_ownership_verb(action).strip(" .")
        if detail:
            return _ensure_responsibility_depth(_sentence_case(detail))
    detail, _rationale = _system_detail(description)
    if detail:
        return _ensure_responsibility_depth(_sentence_case(detail))
    return (
        f"Owns the {name.lower()} responsibility named by the accepted product direction; "
        "the first implementation plan must name its inputs, outputs, state changes, and review evidence."
    )


def _ensure_responsibility_depth(value: str) -> str:
    text = _sentence_case(value)
    if len(re.findall(r"[A-Za-z0-9]+", text)) >= 6:
        return text
    if text.casefold().startswith("owns "):
        return f"{text} and its reviewable evidence."
    return f"{text} and records review evidence."


def _boundary(*, name: str, description: str, kind: str) -> str:
    action, rationale = _system_action(description)
    topic, rationale = _system_detail(description)
    topic = topic or action or f"the {name.lower()} responsibility"
    responsibility = _responsibility_reference(action=action, fallback=topic)
    if kind == "client":
        return (
            f"{name} owns the user-facing actions and visible states for {responsibility}. "
            "Domain derivation, persistence, and external-provider truth stay with the product systems it calls."
        )
    if kind == "adapter":
        return (
            f"{name} owns translation, normalization, and provenance for {responsibility}. "
            "The upstream provider, imported file, or external system remains outside this boundary."
        )
    rationale_text = f" {_evidence_sentence(rationale)}" if rationale else ""
    return (
        f"{name} owns state, rules, and handoff for {responsibility}. It produces the records, decisions, or handoffs other components depend on."
        f"{rationale_text} Presentation, external-provider truth, and adjacent product decisions stay outside unless explicitly assigned."
    )


def _dependencies(*, name: str, description: str, prior: list[dict[str, Any]]) -> list[str]:
    action, _action_rationale = _system_action(description)
    topic, rationale = _system_detail(description)
    responsibility = _responsibility_reference(action=action, fallback=topic or f"the {name.lower()} responsibility")
    deps: list[str] = []
    if prior:
        previous = prior[-1]
        previous_label = str(previous.get("label") or previous.get("component_id") or "the previous component").strip()
        deps.append(
            f"Coordinates with {previous_label} so upstream state, evidence, or decisions are available before this component can {_can_clause(action, responsibility)}."
        )
    if rationale:
        deps.append(_evidence_sentence(rationale))
    if not deps:
        deps.append(
            f"The first implementation plan must name the exact data, event, or call boundary this component uses to {_can_clause(action, responsibility)}."
        )
    return deps


def _interfaces(*, name: str, description: str, kind: str) -> list[str]:
    action, _action_rationale = _system_action(description)
    detail, _rationale = _system_detail(description)
    detail = detail or action or f"the {name.lower()} responsibility"
    responsibility = _responsibility_reference(action=action, fallback=detail)
    if kind == "client":
        return [f"Visible action and state contract for {responsibility}, including normal, empty, blocked, and recovery states."]
    if kind == "adapter":
        return [f"Input and output contract for {responsibility}, including source identity, payload shape, normalized result, and error state."]
    return [f"Command, query, or event contract for {responsibility}; includes accepted input, produced state, failure state, and ownership handoff."]


def _validation(*, name: str, description: str, kind: str) -> list[str]:
    action, _action_rationale = _system_action(description)
    detail, _rationale = _system_detail(description)
    detail = detail or action or name
    responsibility = _responsibility_reference(action=action, fallback=detail)
    if kind == "client":
        return [f"Normal path, blocked path, and recovery state are visible for {responsibility}."]
    if kind == "adapter":
        return [f"Accepted input, rejected input, provenance preservation, and repeatable normalized output are proven while this component {_does_clause(action, responsibility)}."]
    return [f"Valid transition, invalid input rejection, and traceable output are proven while this component {_does_clause(action, responsibility)}."]


def _unique_component_id(component_id: str, existing: list[dict[str, Any]], index: int) -> str:
    used = {str(row.get("component_id", "")) for row in existing}
    candidate = component_id
    while candidate in used:
        index += 1
        candidate = f"{component_id}-{index}"
    return candidate


def _strip_ownership_verb(value: str) -> str:
    text = str(value or "").strip()
    first, _, rest = text.partition(" ")
    lower = first.casefold().strip(".,:;")
    replacements = {
        "accepts": "acceptance of",
        "assembles": "assembly of",
        "binds": "binding of",
        "captures": "capture of",
        "computes": "computed result for",
        "derives": "derivation of",
        "estimates": "estimate of",
        "exports": "export of",
        "handles": "handling of",
        "imports": "import of",
        "links": "links between",
        "owns": "",
        "own": "",
        "performs": "",
        "preserves": "preservation of",
        "records": "record of",
        "renders": "rendering of",
        "resolves": "resolution of",
        "serves": "service for",
        "shows": "visibility into",
        "stores": "stored record of",
        "tracks": "tracking of",
        "validates": "validation of",
        "views": "view of",
        "writes": "written record of",
    }
    if lower not in replacements or not rest:
        return text
    prefix = replacements[lower]
    return rest.strip() if not prefix else f"{prefix} {rest.strip()}"


def _system_detail(value: str) -> tuple[str, str]:
    text = _strip_ownership_verb(value).strip(" .")
    if not text:
        return "", ""
    parts = re.split(r"\brationale\s*:\s*", text, maxsplit=1, flags=re.IGNORECASE)
    detail = parts[0].strip(" .")
    rationale = parts[1].strip(" .") if len(parts) > 1 else ""
    evidence_parts = re.split(r"\brelevant\s+behavior\s*:\s*", detail, maxsplit=1, flags=re.IGNORECASE)
    if len(evidence_parts) > 1:
        detail = evidence_parts[0].strip(" .")
        evidence = evidence_parts[1].strip(" .")
        rationale = ". ".join(part for part in (f"Relevant behavior: {evidence}" if evidence else "", rationale) if part)
    detail = re.sub(r"^(?:the\s+)?accepted\s+", "", detail, flags=re.IGNORECASE).strip(" .")
    return detail, rationale


def _system_action(value: str) -> tuple[str, str]:
    text = str(value or "").strip(" .")
    if not text:
        return "", ""
    parts = re.split(r"\brationale\s*:\s*", text, maxsplit=1, flags=re.IGNORECASE)
    action = parts[0].strip(" .")
    rationale = parts[1].strip(" .") if len(parts) > 1 else ""
    evidence_parts = re.split(r"\brelevant\s+behavior\s*:\s*", action, maxsplit=1, flags=re.IGNORECASE)
    if len(evidence_parts) > 1:
        action = evidence_parts[0].strip(" .")
        evidence = evidence_parts[1].strip(" .")
        rationale = ". ".join(part for part in (f"Relevant behavior: {evidence}" if evidence else "", rationale) if part)
    action = re.sub(r"^(?:the\s+)?accepted\s+", "", action, flags=re.IGNORECASE).strip(" .")
    return action, rationale


def _responsibility_reference(*, action: str, fallback: str) -> str:
    action = str(action or "").strip(" .")
    fallback = str(fallback or "").strip(" .")
    if action:
        return f"this responsibility: {action[:1].lower() + action[1:]}"
    if fallback:
        return fallback[:1].lower() + fallback[1:]
    return "this component responsibility"


def _does_clause(action: str, fallback: str) -> str:
    action = str(action or "").strip(" .")
    if looks_like_finite_action(action):
        return action[:1].lower() + action[1:]
    fallback = str(fallback or "").strip(" .")
    return f"handles {fallback[:1].lower() + fallback[1:]}" if fallback else "handles its assigned responsibility"


def _can_clause(action: str, fallback: str) -> str:
    action = str(action or "").strip(" .")
    if looks_like_finite_action(action):
        return base_action_clause(action)
    fallback = str(fallback or "").strip(" .")
    return f"complete {fallback[:1].lower() + fallback[1:]}" if fallback else "complete its assigned responsibility"


def _evidence_sentence(value: str) -> str:
    text = str(value or "").strip(" .")
    if not text:
        return ""
    if re.match(r"^relevant\s+behavior\s*:", text, flags=re.IGNORECASE):
        evidence = re.sub(r"^relevant\s+behavior\s*:\s*", "", text, flags=re.IGNORECASE).strip(" .")
        domain, _separator, pressure = evidence.partition(". ")
        result = f"Domain evidence: {domain.strip(' .')}."
        if pressure.strip():
            result += f" Design pressure: {_sentence_case(pressure)}."
        return result
    return f"Design pressure: {text}."


def _sentence_case(value: str) -> str:
    text = str(value or "").strip(" .")
    if not text:
        return ""
    return text[:1].upper() + text[1:]


def _join_domain_items(items: list[str] | None, *, limit: int = 4) -> str:
    values = [str(item).strip().rstrip(".") for item in (items or []) if str(item).strip()]
    if not values:
        return ""
    selected = values[:limit]
    suffix = "" if len(values) <= limit else f", plus {len(values) - limit} more"
    return "; ".join(selected) + suffix


def _join_system_names(items: list[str] | None, *, limit: int = 4) -> str:
    values = [confirmed_system_name(str(item or "")).strip().rstrip(".") for item in (items or [])]
    values = [value for value in values if value]
    if not values:
        return ""
    selected = values[:limit]
    suffix = "" if len(values) <= limit else f", plus {len(values) - limit} more"
    return ", ".join(selected) + suffix


def _brief_clause(value: str, *, limit: int = 180) -> str:
    text = _plain_text(value).strip(" .")
    text = re.sub(r"^the first complete path to prove should be\s*:?\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^first complete path to prove should be\s*:?\s+", "", text, flags=re.IGNORECASE)
    if ". " in text:
        text = text.split(". ", 1)[0].strip(" .")
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _state_object_label(value: str, *, fallback: str) -> str:
    text = _plain_text(value).strip(" .:-")
    if not text:
        return fallback
    first_clause = re.split(r"[.;\n]", text, maxsplit=1)[0].strip(" .:-")
    dash_head = re.split(r"\s+[—-]\s+", first_clause, maxsplit=1)[0].strip(" .:-")
    patterns = (
        r"\b(?:the\s+)?(?:primary\s+)?state\s+object\s+is\s+(?:the\s+)?(?P<label>[^.;:]+)$",
        r"\b(?:the\s+)?(?:domain\s+)?object\s+is\s+(?:the\s+)?(?P<label>[^.;:]+)$",
        r"\b(?:the\s+)?proof\s+record\s+is\s+(?:the\s+)?(?P<label>[^.;:]+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, dash_head, flags=re.IGNORECASE)
        if match:
            return _title_phrase(match.group("label").strip(" .:-")) or fallback
    if dash_head and len(dash_head.split()) <= 7 and not re.search(
        r"\b(is|are|starts?|moves?|changes?|tracks?|records?|captures?|produces?)\b",
        dash_head,
        re.IGNORECASE,
    ):
        return _title_phrase(dash_head) or fallback
    return fallback


def _title_phrase(value: str) -> str:
    return " ".join(_title_word(word, first=index == 0) for index, word in enumerate(_plain_text(value).split()))


def _plain_text(value: object) -> str:
    text = display_text.strip_inline_markdown_emphasis_tokens(value).replace("`", "").strip()
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return " ".join(text.split())


def _title_word(value: str, *, first: bool = True, previous: str = "") -> str:
    lower = value.casefold()
    if lower in {"ai", "api", "crm", "gis", "iot", "llm", "ml", "pwa", "ui", "ux"}:
        return lower.upper()
    if any(char.islower() for char in value) and any(char.isupper() for char in value[1:]):
        return value
    if not first and not str(previous or "").endswith(":") and lower in {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}:
        return lower
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
    "system_component_name",
]
