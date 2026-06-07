"""Component helpers for confirmed greenfield proposals."""

from __future__ import annotations

import re
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import (
    confirmed_system_description,
    confirmed_system_name,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import release_scope_for_component
from odylith.runtime.domain_intelligence.greenfield_component_contract import (
    boundary_from_contract,
    dependencies_from_contract,
    ensure_component_contract,
    interfaces_from_contract,
    responsibility_from_contract,
    risks_from_contract,
    validation_from_contract,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_differentiation import (
    differentiate_component_contracts,
)
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text
from odylith.runtime.domain_intelligence.greenfield_text import visible_words


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
    brand = _brand_label(source)
    if brand:
        return brand
    words = label_terms(source, stopwords=_STOPWORDS)
    if not words:
        words = ["Greenfield", "Workflow"]
    selected = words[:4] if len(words) <= 4 else words[:3]
    return " ".join(_title_word(word) for word in selected)


def _brand_label(value: str) -> str:
    """Prefer an explicit short brand segment over subtitle fragments."""

    head = re.split(r"\s+(?:—|–|-)\s+|:\s+", _plain_text(value), maxsplit=1)[0].strip(" .")
    if not head:
        return ""
    words = label_terms(head, stopwords=_STOPWORDS)
    if not 1 <= len(words) <= 4:
        return ""
    if head.casefold() in {"greenfield project", "confirmed project"}:
        return ""
    return " ".join(_title_word(word, first=index == 0) for index, word in enumerate(words))


def confirmed_components(
    *,
    label: str,
    label_slug: str,
    internal_systems: list[str] | None = None,
    first_path: str = "",
    state_object: str = "",
    proof_boundary: str = "",
    external_systems: list[str] | None = None,
    non_goals: list[str] | None = None,
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
        state_object=state_object,
        proof_boundary=proof_boundary,
        external_systems=external_systems or [],
        non_goals=non_goals or [],
    )


def _confirmed_system_components(
    *,
    label: str,
    label_slug: str,
    internal_systems: list[str],
    first_path: str = "",
    state_object: str = "",
    proof_boundary: str = "",
    external_systems: list[str] | None = None,
    non_goals: list[str] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    path_slug = _path_slug(label_slug)
    for index, system in enumerate(internal_systems, start=1):
        name = system_component_name(confirmed_system_name(system))
        description = confirmed_system_description(system).replace("/", " and ")
        component_slug = slugify(name) or f"{label_slug}-component-{index}"
        if not component_slug.startswith(label_slug) and len(component_slug.split("-")) <= 2:
            component_id = _component_id(label_slug, component_slug)
        else:
            component_id = component_slug
        component_id = _dedupe_slug_tokens(component_id)
        kind = _system_kind(name, description)
        responsibility = _responsibility(name=name, description=description)
        row: dict[str, Any] = {
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
            "source_system_description": description,
        }
        row["release_scope"] = release_scope_for_component(
            row,
            first_path=first_path,
            proof_boundary=proof_boundary,
            non_goals=non_goals or (),
        )
        rows.append(row)
    proposal_context = {
        "intent": {
            "title": label,
            "first_path": first_path,
            "proof_boundary": proof_boundary,
            "external_systems": external_systems or [],
        },
        "state_object": state_object,
    }
    for index, row in enumerate(rows):
        previous_label = str(rows[index - 1].get("label", "")) if index else ""
        next_label = str(rows[index + 1].get("label", "")) if index + 1 < len(rows) else ""
        contract = ensure_component_contract(
            row,
            proposal=proposal_context,
            previous_label=previous_label,
            next_label=next_label,
        )
        row["component_contract"] = contract
        if _generated_or_weak(row.get("responsibility")):
            row["responsibility"] = responsibility_from_contract(str(row.get("label", "")), contract)
        if _generated_or_weak(row.get("boundary")):
            row["boundary"] = boundary_from_contract(str(row.get("label", "")), contract)
        if _generated_sequence(row.get("interfaces")):
            row["interfaces"] = interfaces_from_contract(contract)
        if _generated_sequence(row.get("dependencies")):
            row["dependencies"] = dependencies_from_contract(contract)
        if _generated_sequence(row.get("validation")):
            row["validation"] = validation_from_contract(contract)
        row["risks"] = risks_from_contract(str(row.get("label", "")), contract)
    proposal_context["components"] = rows
    differentiate_component_contracts(proposal_context)
    for row in rows:
        contract = row.get("component_contract")
        if not isinstance(contract, dict):
            continue
        label_text = str(row.get("label", "")).strip()
        if _generated_or_weak(row.get("responsibility")):
            row["responsibility"] = responsibility_from_contract(label_text, contract)
        if _generated_or_weak(row.get("boundary")):
            row["boundary"] = boundary_from_contract(label_text, contract)
        if _generated_sequence(row.get("interfaces")):
            row["interfaces"] = interfaces_from_contract(contract)
        if _generated_sequence(row.get("dependencies")):
            row["dependencies"] = dependencies_from_contract(contract)
        if _generated_sequence(row.get("validation")):
            row["validation"] = validation_from_contract(contract)
        row["risks"] = risks_from_contract(label_text, contract)
    return rows


def system_component_name(value: str) -> str:
    """Convert actor-placeholder prefixes into capability names for component records."""

    name = _flatten_parenthetical_descriptor(_plain_text(value)).replace("/", " and ").strip(" .:-")
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


def _flatten_parenthetical_descriptor(value: str) -> str:
    text = _plain_text(value)
    text = re.sub(r"\(([^)]{3,160})\)", _parenthetical_descriptor_replacement, text)
    return re.sub(r"\s+", " ", text).strip()


def _parenthetical_descriptor_replacement(match: re.Match[str]) -> str:
    body = _plain_text(match.group(1))
    if "," in body or word_count(body) > 4:
        return ""
    return f" {body}"


def _system_kind(name: str, description: str) -> str:
    name_text = name.casefold()
    description_text = description.casefold()
    if _contains_kind_token(f"{name_text} {description_text}", ("web", "ui", "surface", "mobile", "portal", "client", "dashboard")):
        return "client"
    if _contains_kind_token(name_text, ("adapter", "provider", "integration", "connector", "source", "import")):
        return "adapter"
    if _contains_kind_token(description_text, ("adapter", "provider", "integration", "connector", "external", "import")):
        return "adapter"
    return "service"


def _contains_kind_token(text: str, tokens: tuple[str, ...]) -> bool:
    words = [word.casefold() for word in visible_words(text)]
    for token in tokens:
        normalized = token.casefold()
        if normalized in {"ui", "web"}:
            if normalized in words:
                return True
            continue
        if any(word == normalized or word == f"{normalized}s" for word in words):
            return True
    return False


def _component_label(name: str, kind: str) -> str:
    name = _greenfield_component_label_text(_title_phrase(name))
    if kind == "client" and not re.search(r"\b(surface|client|ui|portal|dashboard|app)\b", name, re.IGNORECASE):
        return f"{name} Surface"
    if kind == "adapter" and "adapter" not in name.casefold():
        return f"{name} Adapter"
    if kind == "service" and not re.search(r"\b(service|ledger|registry|store|trail|linker|engine|core|review|tracker|planner|evaluator)\b", name, re.IGNORECASE):
        return f"{name} Service"
    return name


def _greenfield_component_label_text(value: str) -> str:
    text = re.sub(r"\bRegistry\b", "Record", str(value or ""), flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


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
        f"Owns {name.lower()} responsibility named by the accepted product direction; "
        "the first implementation plan must name its inputs, outputs, state changes, and review evidence."
    )


def _ensure_responsibility_depth(value: str) -> str:
    text = _sentence_case(value)
    if word_count(text) >= 6:
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
            f"{name} owns user-facing actions and visible states for {responsibility}. "
            "Domain derivation, persistence, and upstream source truth stay with the product systems it calls."
        )
    if kind == "adapter":
        return (
            f"{name} owns translation, normalization, and provenance for {responsibility}. "
            "The upstream provider, imported file, or external system remains outside this boundary."
        )
    rationale_text = f" {_evidence_sentence(rationale)}" if rationale else ""
    return (
        f"{name} owns state, rules, and handoff for {responsibility}. It produces the records, decisions, or handoffs other components depend on."
        f"{rationale_text} Presentation, upstream source truth, and adjacent product decisions stay outside unless explicitly assigned."
    )


def _dependencies(*, name: str, description: str, prior: list[dict[str, Any]]) -> list[str]:
    action, _action_rationale = _system_action(description)
    topic, rationale = _system_detail(description)
    responsibility = _responsibility_reference(action=action, fallback=topic or f"the {name.lower()} responsibility")
    focus = _dependency_focus(action=action, fallback=responsibility)
    deps: list[str] = []
    if prior:
        previous = prior[-1]
        previous_label = str(previous.get("label") or previous.get("component_id") or "the previous component").strip()
        deps.append(f"Uses {previous_label} output as upstream context for {focus}.")
    if rationale:
        deps.append(_evidence_sentence(rationale))
    if not deps:
        deps.append(f"The first implementation plan must name the exact data, event, or call boundary used for {focus}.")
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


def _generated_or_weak(value: Any) -> bool:
    text = _plain_text(value).casefold()
    if not text:
        return True
    generic_markers = (
        "responsibility and keeps it tied",
        "accepted first path",
        "assigned state, command, evidence",
        "records review evidence",
        "this responsibility:",
        "first implementation plan must name",
        "selected by the first implementation plan",
        "boundary; accepted inputs",
        "accepted inputs, produced outputs",
        "local refusal evidence",
        "validation evidence, and local handoff decisions",
        "owns combines reference ranges",
        "combines reference ranges with",
    )
    if any(marker in text for marker in generic_markers):
        return True
    return word_count(text) < 6


def _generated_sequence(value: Any) -> bool:
    rows = [str(item).strip() for item in (value if isinstance(value, list) else [value]) if str(item).strip()]
    if not rows:
        return True
    joined = " ".join(_plain_text(row).casefold() for row in rows)
    generic_markers = (
        "responsibility and keeps it tied",
        "assigned state, command, evidence",
        "first implementation plan must name",
        "command, query, or event contract",
        "valid transition, invalid input rejection",
        "normal path, blocked path",
        "accepted input, produced state",
        "state, behavior, evidence, or access",
    )
    return any(marker in joined for marker in generic_markers)


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
        "combines": "combined view of",
        "derives": "derivation of",
        "estimates": "estimate of",
        "exports": "export of",
        "forecasts": "forecast of",
        "handles": "handling of",
        "imports": "import of",
        "issues": "",
        "links": "links between",
        "normalizes": "normalized view of",
        "optimizes": "optimized result for",
        "owns": "",
        "own": "",
        "performs": "",
        "predicts": "prediction of",
        "preserves": "preservation of",
        "pulls": "source context for",
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
    return _normalize_system_action(action), rationale


def _responsibility_reference(*, action: str, fallback: str) -> str:
    action = str(action or "").strip(" .")
    fallback = str(fallback or "").strip(" .")
    if action:
        return f"this responsibility: {action[:1].lower() + action[1:]}"
    if fallback:
        return fallback[:1].lower() + fallback[1:]
    return "this component responsibility"


def _normalize_system_action(value: str) -> str:
    text = str(value or "").strip(" .")
    text = re.sub(
        r"^combines?\s+reference\s+ranges?\s+with\b",
        "evaluates reference ranges against",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _does_clause(action: str, fallback: str) -> str:
    action = str(action or "").strip(" .")
    if looks_like_finite_action(action):
        return action[:1].lower() + action[1:]
    fallback = str(fallback or "").strip(" .")
    return f"handles {fallback[:1].lower() + fallback[1:]}" if fallback else "handles its assigned responsibility"


def _dependency_focus(*, action: str, fallback: str) -> str:
    text = str(action or fallback or "").strip(" .")
    text = re.sub(r"^\s*this\s+responsibility\s*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*(?:the\s+)?accepted\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:guide|guides|guided|guiding)\s+(?:the\s+)?first\s+path\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:capture|captures|captured|capturing)\s+allowed\s+commands?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:expose|exposes|exposed|exposing)\s+blocked\s+states?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bkeeps?\s+the\s+next\s+action\s+(?:clear|visible)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*[:,;]\s*$", "", text).strip(" .,;")
    text = re.sub(r"^\s*(?:and|or|,|;)+\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*(?:and|or|,|;)+\s*$", "", text, flags=re.IGNORECASE)
    if not text or word_count(text) < 3:
        return "the local product behavior"
    if looks_like_finite_action(text):
        return base_action_clause(text)
    return text[:1].lower() + text[1:]


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


def _title_phrase(value: str) -> str:
    return " ".join(_title_word(word, first=index == 0) for index, word in enumerate(_plain_text(value).split()))


def _plain_text(value: object) -> str:
    return clean_markdown_text(value)


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
    prefix_tokens = _slug_tokens(label_slug)
    suffix_tokens = _slug_tokens(suffix)
    if not prefix_tokens and not suffix_tokens:
        return ""
    if not prefix_tokens:
        return "-".join(suffix_tokens)
    if not suffix_tokens:
        return "-".join(prefix_tokens)
    overlap = 0
    max_overlap = min(len(prefix_tokens), len(suffix_tokens))
    for size in range(max_overlap, 0, -1):
        if prefix_tokens[-size:] == suffix_tokens[:size]:
            overlap = size
            break
    return "-".join([*prefix_tokens, *suffix_tokens[overlap:]])


def _slug_tokens(value: str) -> list[str]:
    return [token for token in slugify(value).split("-") if token]


def _dedupe_slug_tokens(value: str) -> str:
    tokens = _slug_tokens(value)
    result: list[str] = []
    for token in tokens:
        if result and result[-1] == token:
            continue
        result.append(token)
    return "-".join(result)


def _path_slug(label_slug: str) -> str:
    return slugify(label_slug).replace("-", "_") or "greenfield"


__all__ = [
    "confirmed_components",
    "domain_label",
    "system_component_name",
]
