"""Deterministic completion for accepted greenfield Product Intent."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_actor_labels import accepted_actor_label
from odylith.runtime.domain_intelligence.greenfield_component_axes import component_axis_for_label
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


CORE_FIELD_MIN_WORDS = {
    "product_story": 28,
    "state_object": 12,
    "first_path": 18,
    "proof_boundary": 18,
}

_GENERIC_TITLE_WORDS = {
    "app",
    "application",
    "helper",
    "platform",
    "product",
    "service",
    "system",
    "tool",
    "tracker",
    "workspace",
}

_ROLE_WORDS = {
    "admin",
    "advocate",
    "analyst",
    "applicant",
    "auditor",
    "borrower",
    "buyer",
    "chief",
    "client",
    "coordinator",
    "crew",
    "customer",
    "decision",
    "director",
    "engineer",
    "expert",
    "finder",
    "helper",
    "inspector",
    "lead",
    "manager",
    "member",
    "operator",
    "owner",
    "planner",
    "reviewer",
    "renter",
    "resident",
    "seller",
    "staff",
    "submitter",
    "supervisor",
    "support",
    "technician",
    "user",
    "volunteer",
}

_SYSTEM_SUFFIXES = (
    "profile registry",
    "workflow planner",
    "evidence and decision log",
    "access and safety guardrail",
)


def complete_confirmed_intent(intent: Mapping[str, Any]) -> dict[str, Any]:
    """Fill reviewable fields that can be inferred from accepted intent text."""

    result = copy.deepcopy(dict(intent))
    title = _title(result)
    if not _completion_seed_is_sufficient(result):
        return result
    if _title_needs_repair(title):
        result["title"] = _derived_title(result, fallback=title)
        title = _title(result)
    result["human_actors"] = _completed_actor_rows(result, title=title)
    result["internal_systems"] = _completed_system_rows(result, title=title)
    _complete_core_fields(result, title=title)
    _complete_product_posture(result, title=title)
    return result


def _completion_seed_is_sufficient(intent: Mapping[str, Any]) -> bool:
    core = " ".join(
        _clean(intent.get(key))
        for key in ("product_story", "state_object", "first_path", "proof_boundary", "problem", "product_view")
        if _clean(intent.get(key))
    )
    if _word_count(core) < 24:
        return False
    return len(_semantic_terms(core)) >= 6


def _complete_core_fields(intent: dict[str, Any], *, title: str) -> None:
    story = _clean(intent.get("product_story"))
    state = _clean(intent.get("state_object"))
    first_path = _clean(intent.get("first_path"))
    proof = _clean(intent.get("proof_boundary"))
    actors = _actor_labels(intent)
    systems = _system_labels(intent)

    if _word_count(story) < CORE_FIELD_MIN_WORDS["product_story"]:
        actor_text = _join(actors[:2]) or f"{_focus_label(title)} users"
        intent["product_story"] = _sentence(
            f"{title} helps {actor_text} complete the accepted first path without losing the state, evidence, decision, and risk context needed to trust the outcome. "
            f"The product keeps {_short(state, fallback='the first release state')} and {_short(first_path, fallback='the first user journey')} connected so reviewers can understand what changed and why."
        )
    if _word_count(state) < CORE_FIELD_MIN_WORDS["state_object"]:
        state_label = _state_label(state, title=title)
        intent["state_object"] = _sentence(
            f"{state_label} records the current status, actor, source input, decision, blocked reason, evidence links, timestamp, and version history for the accepted first path."
        )
    if _word_count(first_path) < CORE_FIELD_MIN_WORDS["first_path"]:
        primary = actors[0] if actors else f"{_focus_label(title)} operator"
        system_text = _join(systems[:2]) or f"{_focus_label(title)} product systems"
        intent["first_path"] = _sentence(
            f"{primary} starts one real {title.lower()} case, uses {system_text} to move it through input, review, decision, and follow-up, then sees a clear outcome with missing or blocked evidence called out."
        )
    if _word_count(proof) < CORE_FIELD_MIN_WORDS["proof_boundary"]:
        intent["proof_boundary"] = _sentence(
            f"Release 0.0.1 is trusted only when the accepted path can be replayed from input through state change, reviewer-visible evidence, blocked or degraded states, access posture, and final decision. "
            f"It must not claim live integrations, broad automation, regulated correctness, or production-scale operation beyond the confirmed {title.lower()} boundary."
        )


def _complete_product_posture(intent: dict[str, Any], *, title: str) -> None:
    actors = _actor_labels(intent)
    systems = _system_labels(intent)
    story = _clean(intent.get("product_story"))
    state = _clean(intent.get("state_object"))
    first_path = _clean(intent.get("first_path"))
    proof = _clean(intent.get("proof_boundary"))
    focus = _focus_label(title)

    if not _clean(intent.get("problem")):
        intent["problem"] = _sentence(
            f"{focus} work becomes hard to trust when the user path, state, evidence, decision, and follow-up are scattered or under-specified."
        )
    if not _clean(intent.get("customer")):
        actor_text = _join_actor_segments(actors[:5]) or f"{focus} operators and reviewers"
        intent["customer"] = _sentence(
            f"{actor_text} need the accepted outcome to be understandable before broader scope is built."
        )
    if not _clean(intent.get("opportunity")):
        intent["opportunity"] = _sentence(
            f"Turn the confirmed {title.lower()} intent into a narrow first release that proves one complete path before adding broader automation, integrations, or scale."
        )
    if not _clean(intent.get("product_view")) or _product_view_needs_repair(intent.get("product_view")):
        state_phrase = _state_label(state, title=title) if state else "the accepted state object"
        intent["product_view"] = _sentence(
            f"{title} is useful when users can inspect {state_phrase}, the first-path outcome, visible blockers, risk posture, and evidence from {_join(systems[:3]) or 'the product-owned systems'} together."
        )
    metrics = _strings(intent.get("success_metrics"))
    if len(metrics) < 3 or any(_metric_needs_repair(metric) for metric in metrics):
        intent["success_metrics"] = [
            "One accepted path reaches a visible outcome with actor, timestamp, state, evidence, and decision context.",
            "At least one blocked, missing-data, stale, invalid, or degraded path is visible and cannot be mistaken for success.",
            f"Release readiness stays inside the confirmed proof boundary and preserves explicit non-goals: {_short(proof, limit=180)}.",
        ]
    if not _strings(intent.get("assumptions")):
        intent["assumptions"] = [
            f"The first release proves one concrete {title.lower()} path before broader scope or automation.",
            "External integrations can start as deterministic fixtures unless the accepted path cannot be proven without a live source.",
            f"Security, privacy, accessibility, safety, audit, and retention obligations scale with the {focus.lower()} data and decisions involved.",
        ]
    if not _strings(intent.get("ambiguities")):
        intent["ambiguities"] = [
            f"Which {focus.lower()} actor owns the final release decision when evidence is incomplete or disputed?",
            f"Which source, device, document, dataset, or external service is authoritative for the first {title.lower()} proof?",
            "Which privacy, safety, compliance, or access rule would change the first path if it is stricter than assumed?",
        ]
    if not _strings(intent.get("non_goals")):
        intent["non_goals"] = [
            f"No claim that {title} handles every user, integration, dataset, edge case, or operational scale in release 0.0.1.",
            "No irreversible automation, regulated decision, or live external dependency without a separately accepted proof boundary.",
        ]
    if not story:
        intent["product_story"] = _sentence(
            f"{title} helps {_join(actors[:2]) or f'{focus} users'} complete one accountable path with state, evidence, and decision context visible."
        )


def _completed_actor_rows(intent: Mapping[str, Any], *, title: str) -> list[str]:
    rows = [row for row in _strings(intent.get("human_actors")) if not _actor_row_is_meta(row)]
    labels = [_actor_label(row, title=title) for row in rows]
    labels = [label for label in labels if label]
    if len(labels) < 3:
        labels.extend(_derived_actor_labels(intent, title=title))
    labels = list(unique_text(labels))[:5]

    first_path = _short(_clean(intent.get("first_path")), fallback="the accepted first path")
    state = _short(_clean(intent.get("state_object")), fallback="the accepted state")
    completed: list[str] = []
    for index, label in enumerate(labels):
        original = rows[index] if index < len(rows) else label
        description = _actor_row_description(original)
        if description and _actor_label(original, title=title).casefold() == label.casefold():
            completed.append(f"{label}: {description}")
            continue
        completed.append(_actor_description(label=label, index=index, title=title, first_path=first_path, state=state))
    return list(unique_text(completed))


def _actor_row_is_meta(value: str) -> bool:
    """Reject generated summary rows that are not human participants."""

    text = _clean(value).casefold()
    return bool(
        re.search(r"\badditional\s+accepted\s+(?:items|actors|systems)\s+remain\b", text)
        or re.search(r"\bother\s+accepted\s+(?:items|actors|systems)\b", text)
        or re.search(r"\bplus\s+\d+\s+more\b", text)
        or text in {"human actors", "participants", "people named in the accepted product direction"}
    )


def _actor_description(*, label: str, index: int, title: str, first_path: str, state: str) -> str:
    label_text = label.casefold()
    if re.search(r"\b(public\s+figure|public\s+person|tracked|being\s+tracked|subject|official|executive|creator)\b", label_text):
        body = "is represented by lawful source records, evidence, confidence, and privacy limits; the product must not imply private access, endorsement, or guaranteed outcome"
    elif re.search(r"\b(compliance|policy|privacy|legal|risk|safety)\b", label_text):
        body = "reviews access, privacy, policy, risk, and evidence boundaries before the product treats the accepted path as release-ready"
    elif re.search(r"\b(user|researcher|investor|analyst|operator)\b", label_text):
        body = f"uses {title} to start the accepted path, inspect source-backed evidence, record a decision, and see blocked or risk states"
    elif re.search(r"\b(author|applicant|submitter|requester|customer|client|resident|buyer|seller)\b", label_text):
        body = f"starts the accepted path in {title}, supplies required input, sees feedback or blockers, and receives the visible outcome"
    elif re.search(r"\b(editor|manager|chair|coordinator|operator|supervisor|lead|owner|director)\b", label_text):
        body = "moves the work through screening, assignment, review, decision, exception handling, and recovery without losing state ownership"
    elif re.search(r"\b(reviewer|inspector|evaluator|analyst|auditor|expert|approver|compliance)\b", label_text):
        body = "reviews assigned work, submits structured evidence or decisions, and can challenge incomplete, disputed, or unsafe outcomes"
    elif re.search(r"\b(coach|trainer|advisor|consultant|specialist)\b", label_text):
        body = "reviews progress, guidance quality, evidence, and escalation signals where the accepted path needs human support"
    elif re.search(r"\b(participant|observer|applicant)\b", label_text):
        body = "supplies input, context, or objections that must remain traceable to the first-path decision"
    elif re.search(r"\b(admin|administrator|config|maintainer|support|scheduler)\b", label_text):
        body = "configures policy, templates, access, deadlines, notifications, recovery, and operational readiness for the accepted path"
    else:
        path_role = _actor_path_role(label=label, first_path=first_path, state=state)
        if path_role:
            return f"{label}: {path_role}."
        body = "can own a named responsibility in the accepted path and see the state, blockers, evidence, or outcome relevant to that responsibility"
    return f"{label}: {body}."


def _actor_path_role(*, label: str, first_path: str, state: str) -> str:
    """Prefer accepted-path language over generic role templates."""

    terms = _semantic_terms(label)
    if not terms:
        return ""
    context = _clean(". ".join(value.strip(" .") for value in (first_path, state) if value))
    if not context:
        return ""
    clauses = _path_clauses(context)
    scored: list[tuple[int, int, str]] = []
    for index, clause in enumerate(clauses):
        overlap = len(terms & _semantic_terms(clause))
        if overlap <= 0:
            continue
        scored.append((overlap, -index, clause))
    if not scored:
        return ""
    scored.sort(reverse=True)
    clause = _short(scored[0][2], limit=170)
    if not clause:
        return ""
    clause = re.sub(r"^(?:a|an|the)\s+", "", clause, flags=re.IGNORECASE)
    return f"can act where the accepted path requires {clause[:1].lower() + clause[1:]}"


def _path_clauses(value: str) -> list[str]:
    rows: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", _clean(value)):
        for clause in re.split(
            r";\s+|,\s+(?=(?:and\s+)?(?:a|an|the|[A-Za-z][a-z]+)\s+"
            r"(?:opens?|reviews?|reads?|compares?|saves?|records?|creates?|submits?|receives?|checks?|"
            r"assigns?|captures?|resolves?|moves?|builds?|exports?|imports?|sees?|supplies?|provides?))",
            sentence,
        ):
            cleaned = _clean(re.sub(r"^(?:and|then)\s+", "", clause, flags=re.IGNORECASE)).strip(" .")
            if _word_count(cleaned) >= 4:
                rows.append(cleaned)
    return rows


def _actor_row_has_usable_description(value: str) -> bool:
    return bool(_actor_row_description(value))


def _actor_row_description(value: str) -> str:
    text = _clean(value)
    for separator in (" — ", " – ", " - ", ":"):
        head, sep, body = text.partition(separator)
        body = body.strip(" .")
        if (
            sep
            and _word_count(head) <= 10
            and _word_count(body) >= 4
            and not re.search(r"\b(can act|supports the accepted path|additional accepted items)\b", body, re.IGNORECASE)
        ):
            return body
    return ""


def _join_actor_segments(values: Sequence[str]) -> str:
    labels = [_clean(value).split("—", 1)[0].split(":", 1)[0].strip(" .") for value in values]
    labels = [label for label in labels if label]
    return "; ".join(labels)


def _product_view_needs_repair(value: Any) -> bool:
    text = _clean(value)
    if not text:
        return False
    return bool(
        re.search(r"\binspect\s+(?:the\s+)?(?:core\s+)?state\s+is\b", text, re.IGNORECASE)
        or re.search(r"\bto\s+complete\s+(?:A|The)\b", text)
        or re.search(r"\.\s*,", text)
    )


def _metric_needs_repair(value: Any) -> bool:
    text = _clean(value)
    if not text:
        return True
    if re.search(r"[,:]\.$", text):
        return True
    if text.rstrip().endswith(","):
        return True
    tail = text.rstrip(".;:, ").split()[-1].casefold() if text.split() else ""
    return tail in {"and", "or", "to", "with", "for", "from", "of", "the", "a", "an", "required"}


def _completed_system_rows(intent: Mapping[str, Any], *, title: str) -> list[str]:
    rows = _strings(intent.get("internal_systems")) or _strings(intent.get("component_responsibilities"))
    context = _context(intent)
    completed = [_system_row(row, context=context, title=title) for row in rows]
    completed = [row for row in completed if row]
    if len(completed) < 2:
        completed = _derived_system_rows(intent, title=title)
    return list(unique_text(completed))[:8]


def _system_row(row: str, *, context: str, title: str) -> str:
    raw = _clean(row)
    if not raw:
        return ""
    if "—" in raw or ":" in raw:
        name, description = re.split(r"\s+—\s+|:\s*", raw, maxsplit=1)
        if _word_count(description) >= 5:
            return f"{_title_case(name)} — {description.rstrip('.')}"
    name = _system_label(raw, title=title)
    if not name:
        return ""
    clause = _best_context_clause(name, context)
    axis_description = _axis_system_description(name)
    if axis_description:
        return f"{name} — {axis_description}"
    if clause:
        return (
            f"{name} — owns its accepted inputs, blocked states, produced outputs, and handoff evidence. "
            f"Context: {_short(clause, limit=180)}"
        )
    return f"{name} — owns input capture, state change, validation evidence, blocked states, and handoff for the accepted {title.lower()} path"


def _axis_system_description(name: str) -> str:
    axis = component_axis_for_label(name)
    if axis is None:
        return ""
    owned = _axis_item_phrase(axis.owned_state, max_items=5)
    outputs = _axis_item_phrase(axis.produced_outputs, max_items=5)
    states = _axis_item_phrase(axis.states_or_transitions, max_items=6)
    return f"owns {owned}, produces {outputs}, and keeps {states} visible"


def _axis_item_phrase(value: str, *, max_items: int) -> str:
    items = []
    for raw in str(value or "").split(","):
        item = raw.strip(" .")
        item = re.sub(r"^(?:and|or)\s+", "", item, flags=re.IGNORECASE).strip()
        if item:
            items.append(item)
    selected = items[:max_items]
    if not selected:
        return _short(value, limit=120)
    if len(selected) == 1:
        return selected[0]
    return ", ".join(selected[:-1]) + f", and {selected[-1]}"


def _derived_system_rows(intent: Mapping[str, Any], *, title: str) -> list[str]:
    focus = _focus_label(title)
    state = _state_label(_clean(intent.get("state_object")), title=title)
    first_path = _short(_clean(intent.get("first_path")), fallback="the accepted first path")
    proof = _short(_clean(intent.get("proof_boundary")), fallback="the release proof")
    names = [f"{focus} {suffix}" for suffix in _SYSTEM_SUFFIXES]
    descriptions = [
        f"owns identity, current status, version history, and traceable changes for {state}",
        f"guides the first path, captures allowed commands, exposes blocked states, and keeps the next action clear: {first_path}",
        f"records source evidence, validation output, reviewer decision, failure reason, and release-readiness proof: {proof}",
        "keeps authorization, shared access, privacy, safety, retention, accessibility, reminders, and recovery behavior explicit before wider rollout",
    ]
    return [f"{_title_case(name)} — {description.rstrip('.')}" for name, description in zip(names, descriptions)]


def _derived_actor_labels(intent: Mapping[str, Any], *, title: str) -> list[str]:
    focus = _focus_label(title)
    context = _context(intent)
    candidates = _role_candidates(context)
    labels: list[str] = []
    for candidate in candidates:
        if _word_count(candidate) <= 5:
            labels.append(_title_case(candidate))
    labels.extend(
        [
            f"{focus} operator",
            f"{focus} reviewer",
            f"{focus} support owner",
            f"{focus} release decision owner",
        ]
    )
    return list(unique_text(labels))


def _role_candidates(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z/-]*", text)
    candidates: list[str] = []
    for index, word in enumerate(words):
        if word.casefold() not in _ROLE_WORDS:
            continue
        start = max(0, index - 2)
        phrase = " ".join(words[start : index + 1])
        phrase = re.sub(r"^(?:a|an|the|one|first|main|primary|current)\s+", "", phrase, flags=re.IGNORECASE)
        if phrase and not phrase.casefold().startswith(("product ", "project ", "workflow ")):
            candidates.append(phrase)
    return list(unique_text(candidates))


def _actor_label(row: str, *, title: str) -> str:
    raw = _clean(str(row).split("—", 1)[0].split(":", 1)[0])
    raw = re.sub(r"^(?:a|an|the)\s+", "", raw, flags=re.IGNORECASE).strip()
    if not raw:
        return ""
    accepted = accepted_actor_label(str(row), project_focus=_focus_label(title))
    if accepted:
        return accepted if _actor_row_has_usable_description(str(row)) else _title_case(accepted)
    specific = _specific_role_label(raw)
    if specific:
        return specific
    if raw.casefold() in {"operator", "reviewer", "user", "owner", "helper", "support", "admin"}:
        raw = f"{_role_focus(_focus_label(title), raw)} {raw}"
    return _title_case(raw)


def _specific_role_label(value: str) -> str:
    match = re.match(
        r"^(?P<role>author|reviewer|admin|administrator|editor|operator|manager|coordinator|supervisor|owner)\s+(?P<tail>.+)$",
        _clean(value),
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    role = match.group("role")
    if match.group("tail").casefold().startswith("or "):
        return ""
    tail = re.sub(
        r"^(?:submitting|evaluating|configuring|managing|reviewing|approving|owning|operating|coordinating)\s+",
        "",
        match.group("tail"),
        flags=re.IGNORECASE,
    ).strip(" .")
    tail = re.sub(r"^(?:a|an|the)\s+", "", tail, flags=re.IGNORECASE)
    if _word_count(tail) < 2:
        return ""
    return _title_case(f"{_role_focus(tail, role)} {role}")


def _role_focus(focus: str, role: str) -> str:
    text = _clean(focus)
    if role.casefold() == "reviewer":
        text = re.sub(r"\breview$", "", text, flags=re.IGNORECASE).strip()
    return text or _clean(focus) or "Project"


def _actor_labels(intent: Mapping[str, Any]) -> list[str]:
    labels: list[str] = []
    for row in _strings(intent.get("human_actors")):
        labels.append(_clean(row.split("—", 1)[0].split(":", 1)[0]))
    return [label for label in labels if label]


def _system_labels(intent: Mapping[str, Any]) -> list[str]:
    labels: list[str] = []
    for row in _strings(intent.get("internal_systems")):
        labels.append(_clean(row.split("—", 1)[0].split(":", 1)[0]))
    return [label for label in labels if label]


def _system_label(row: str, *, title: str) -> str:
    raw = _clean(row)
    raw = re.sub(r"^(?:a|an|the)\s+", "", raw, flags=re.IGNORECASE)
    raw = _repair_system_label_tail(raw)
    if _word_count(raw) > 14:
        raw = _compact_system_label(raw)
    return _title_case(raw or f"{_focus_label(title)} system")


def _repair_system_label_tail(value: str) -> str:
    text = _clean(value).strip(" ,;:.")
    words = text.split()
    while words and words[-1].casefold().strip(".,;:") in {"and", "or", "for", "of", "the", "to", "with"}:
        words.pop()
    return " ".join(words).strip(" ,;:.")


def _compact_system_label(value: str) -> str:
    text = _repair_system_label_tail(value)
    if _word_count(text) <= 12:
        return text
    match = re.match(r"(?P<head>.+?\b(?:flow|capture|tracking|tracker|analytics|explanations|guardrails|controls|viewer|dashboard|workspace|workflow|service|engine|ledger|registry|store|journal|planner|generation|management|intake|versioning))\b", text, flags=re.IGNORECASE)
    if match and _word_count(match.group("head")) >= 2:
        return _repair_system_label_tail(match.group("head"))
    words = text.split()[:12]
    while words and words[-1].casefold().strip(".,;:") in {"and", "or", "for", "of", "the", "to", "with"}:
        words.pop()
    return " ".join(words)


def _state_label(value: str, *, title: str) -> str:
    text = _clean(value)
    if text:
        first = re.split(r"[.;]", text, maxsplit=1)[0]
        match = re.search(r"\b(?:state object is|primary state object is|is)\s+(?:a|an|the)?\s*(?P<label>[^.;:]+)", first, re.IGNORECASE)
        if match:
            return _title_case(match.group("label"))
        if _word_count(first) <= 8:
            return _title_case(first)
    return f"{_focus_label(title)} state profile"


def _title(intent: Mapping[str, Any]) -> str:
    return _clean(intent.get("title")) or "Greenfield Project"


def _title_needs_repair(value: str) -> bool:
    text = _clean(value)
    if not text or text.casefold() == "greenfield project":
        return True
    words = re.findall(r"[A-Za-z0-9]+", text)
    if not words:
        return True
    tail = words[-1].casefold()
    if tail in {"a", "an", "and", "for", "from", "in", "of", "on", "or", "the", "to", "with"}:
        return True
    lowered = text.casefold()
    return len(words) > 10 and bool(
        re.search(r"\b(?:that|what|so|because|captures?|follows?|makes?|buying|using|needs?|wants?)\b", lowered)
    )


def _derived_title(intent: Mapping[str, Any], *, fallback: str) -> str:
    system_labels = [_clean(label) for label in _system_labels(intent) if _clean(label)]
    context = _title_context(intent)
    noun = _title_noun(context, system_labels)
    qualifier = _title_qualifier(context, system_labels, noun=noun)
    if qualifier and noun:
        return _title_case(f"{qualifier} {noun}")
    for label in system_labels:
        if 2 <= _word_count(label) <= 7:
            return _title_case(label)
    state_label = _state_label(_clean(intent.get("state_object")), title=fallback)
    if 2 <= _word_count(state_label) <= 7:
        return _title_case(state_label)
    return _focus_label(fallback)


def _title_context(intent: Mapping[str, Any]) -> str:
    parts = [
        _clean(intent.get("product_story")),
        _clean(intent.get("state_object")),
        _clean(intent.get("first_path")),
        _clean(intent.get("proof_boundary")),
        " ".join(_strings(intent.get("internal_systems"))),
    ]
    return ". ".join(part.strip(" .") for part in parts if part)


def _title_noun(context: str, system_labels: Sequence[str]) -> str:
    nouns = (
        "workbench",
        "workspace",
        "watchlist",
        "journal",
        "dashboard",
        "tracker",
        "registry",
        "ledger",
        "portal",
        "planner",
        "viewer",
        "console",
        "list",
        "profile",
        "record",
        "workflow",
    )
    combined = " ".join([context, *system_labels]).casefold()
    for noun in nouns:
        if re.search(rf"\b{re.escape(noun)}s?\b", combined):
            return noun
    return "workspace"


def _title_qualifier(context: str, system_labels: Sequence[str], *, noun: str) -> str:
    candidates: list[tuple[int, str]] = []
    sources = [*system_labels, context]
    for source in sources:
        text = _clean(source)
        for match in re.finditer(
            r"\b(?P<phrase>[A-Za-z][A-Za-z0-9'-]*(?:\s+[A-Za-z][A-Za-z0-9'-]*){0,2})\s+"
            r"(?P<noun>activity|signal|signals|case|cases|record|records|item|items|request|requests|submission|submissions|evidence|data|profile|profiles)\b",
            text,
        ):
            phrase = _clean(f"{match.group('phrase')} {match.group('noun')}")
            phrase = re.sub(r"^(?:a|an|the)\s+", "", phrase, flags=re.IGNORECASE)
            if _usable_title_phrase(phrase, noun=noun):
                candidates.append((_semantic_overlap(phrase, context), phrase))
    for label in system_labels:
        words = [
            word
            for word in re.findall(r"[A-Za-z0-9]+", label)
            if word.casefold() not in _GENERIC_TITLE_WORDS and word.casefold() != noun.casefold()
        ]
        if 1 <= len(words) <= 3:
            phrase = " ".join(words)
            if _usable_title_phrase(phrase, noun=noun):
                candidates.append((_semantic_overlap(phrase, context), phrase))
    candidates.sort(key=lambda item: (-item[0], len(item[1])))
    return candidates[0][1] if candidates else ""


def _usable_title_phrase(value: str, *, noun: str) -> bool:
    text = _clean(value)
    if not text:
        return False
    lowered = text.casefold()
    banned_words = {
        "can",
        "adds",
        "chooses",
        "compare",
        "compares",
        "could",
        "decide",
        "deserves",
        "doing",
        "each",
        "follow",
        "make",
        "makes",
        "needs",
        "only",
        "records",
        "reviews",
        "sees",
        "selected",
        "should",
        "that",
        "those",
        "whether",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "wants",
    }
    if any(word in banned_words for word in lowered.split()):
        return False
    if noun.casefold() in lowered:
        return False
    if any(word in _GENERIC_TITLE_WORDS for word in lowered.split()):
        return False
    return _word_count(text) <= 4


def _focus_label(title: str) -> str:
    words = [
        word
        for word in re.findall(r"[A-Za-z0-9]+", title)
        if word.casefold() not in _GENERIC_TITLE_WORDS
    ]
    if not words:
        words = re.findall(r"[A-Za-z0-9]+", title)[:3]
    return _title_case(" ".join(words[:4]) or "Project")


def _context(intent: Mapping[str, Any]) -> str:
    parts = [
        _clean(intent.get("title")),
        _clean(intent.get("product_story")),
        _clean(intent.get("problem")),
        _clean(intent.get("customer")),
        _clean(intent.get("opportunity")),
        _clean(intent.get("product_view")),
        _clean(intent.get("state_object")),
        _clean(intent.get("first_path")),
        _clean(intent.get("proof_boundary")),
        " ".join(_strings(intent.get("human_actors"))),
        " ".join(_strings(intent.get("external_systems"))),
        " ".join(_strings(intent.get("assumptions"))),
        " ".join(_strings(intent.get("ambiguities"))),
    ]
    return ". ".join(part.strip(" .") for part in parts if part)


def _best_context_clause(name: str, context: str) -> str:
    terms = _semantic_terms(name)
    scored: list[tuple[int, int, str]] = []
    for index, sentence in enumerate(re.split(r"(?<=[.!?])\s+", context)):
        clause = _clean(sentence).strip(" .")
        if _word_count(clause) < 6:
            continue
        overlap = len(terms & _semantic_terms(clause))
        if overlap:
            scored.append((overlap, -index, clause))
    scored.sort(reverse=True)
    return scored[0][2] if scored else ""


def _semantic_overlap(left: str, right: str) -> int:
    return len(_semantic_terms(left) & _semantic_terms(right))


def _semantic_terms(text: str) -> set[str]:
    stop = {
        "and",
        "are",
        "before",
        "can",
        "for",
        "from",
        "has",
        "have",
        "into",
        "that",
        "the",
        "this",
        "with",
        "without",
    }
    terms: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", _clean(text).casefold()):
        token = raw.strip("-_")
        if len(token) < 3 or token in stop:
            continue
        if token.endswith("ies") and len(token) > 4:
            token = f"{token[:-3]}y"
        elif token.endswith("ing") and len(token) > 5:
            token = token[:-3]
        elif token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
            token = token[:-1]
        if token not in stop:
            terms.add(token)
    return terms


def _strings(value: object) -> list[str]:
    return list(text_values(value))


def _join(values: Sequence[str]) -> str:
    cleaned = [_clean(value).rstrip(".") for value in values if _clean(value)]
    if len(cleaned) <= 1:
        return cleaned[0] if cleaned else ""
    return ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"


def _short(value: str, *, fallback: str = "", limit: int = 220) -> str:
    text = _clean(value) or fallback
    if len(text) <= limit:
        return text.rstrip(".")
    clipped = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    words = clipped.split()
    while words and words[-1].casefold().strip(".,;:") in {"and", "or", "to", "with", "without", "for", "from", "of", "the", "a", "an", "required"}:
        words.pop()
    return " ".join(words).rstrip(" ,;:.")


def _sentence(value: str) -> str:
    text = _clean(value).strip()
    if text and text[-1] not in ".!?":
        text += "."
    return text


def _lower_first(value: str) -> str:
    text = _clean(value)
    if not text:
        return ""
    return text[:1].lower() + text[1:]


def _title_case(value: str) -> str:
    words: list[str] = []
    for word in _clean(value).split():
        lower = word.casefold()
        if lower in {"ai", "api", "crm", "gis", "iot", "llm", "ml", "ui", "ux"}:
            words.append(lower.upper())
        else:
            words.append(word[:1].upper() + word[1:])
    return " ".join(words)


def _word_count(value: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+", _clean(value)))


def _clean(value: object) -> str:
    text = clean_text(value)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


__all__ = ["complete_confirmed_intent"]
