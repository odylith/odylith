"""Sequence-diagram routing for confirmed greenfield Atlas output."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from odylith.runtime.common import display_text
from odylith.runtime.common import mermaid_text
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import active_release_components
from odylith.runtime.domain_intelligence.greenfield_sequence_steps import ACTION_VERB_PATTERN as _ACTION_VERB_PATTERN
from odylith.runtime.domain_intelligence.greenfield_sequence_steps import sequence_event_steps
from odylith.runtime.domain_intelligence.greenfield_text import clip_text_at_word_boundary


_BASE_ACTION_VERB_PATTERN = (
    r"add|adjust|approve|assign|attach|calculate|capture|check|choose|close|collect|compare|complete|compute|"
    r"confirm|correct|create|decide|decline|delete|derive|edit|enter|evaluate|export|fetch|find|get|group|hand|"
    r"highlight|import|inspect|keep|link|log|notify|open|order|persist|preserve|produce|publish|rank|read|receive|"
    r"record|reject|render|request|resolve|return|review|route|run|save|schedule|screen|see|select|send|show|store|"
    r"submit|supply|track|validate|verify|view|vote"
)

_SEQUENCE_TERM_STOPWORDS = {
    "accepted",
    "actor",
    "and",
    "app",
    "application",
    "boundary",
    "component",
    "evidence",
    "first",
    "from",
    "outcome",
    "path",
    "product",
    "proof",
    "record",
    "release",
    "result",
    "state",
    "system",
    "that",
    "the",
    "through",
    "with",
}


def sequence_mermaid(
    *,
    label: str,
    actors: list[str],
    components: list[dict[str, Any]],
    first_path: str,
    semantic_model: Mapping[str, Any] | None = None,
) -> str:
    """Render the first-path sequence from structured semantic events."""

    selected = [dict(row) for row in active_release_components(components)] if components else []
    selected = selected[:7] or [{"label": f"{label} product core"}]
    actor_rows = actors[:5] or [f"{label} user"]
    lines = [
        "sequenceDiagram",
        "  autonumber",
    ]
    for index, actor in enumerate(actor_rows, start=1):
        lines.append(f"  participant A{index} as {_participant_label(actor)}")
    for index, component in enumerate(selected, start=1):
        lines.append(f"  participant C{index} as {_participant_label(str(component.get('label', 'Component')))}")
    steps = sequence_event_steps(first_path, semantic_model=semantic_model)
    if not steps:
        steps = ["Start the accepted first path", "Record product state and evidence", "Review the outcome and blockers"]
    visible_steps = steps[: min(14, max(10, len(selected) + 6))]
    for index, step in enumerate(visible_steps):
        actor_node = _step_actor(step, actors=actor_rows, fallback_index=min(index, len(actor_rows) - 1))
        component_node = _step_component(step, components=selected, fallback_index=min(index, len(selected) - 1))
        lines.append(f"  {actor_node}->>{component_node}: {_step_message(step, keep_actor_subject=index == 0)}")
        if index + 1 < len(visible_steps):
            next_component_node = _step_component(
                visible_steps[index + 1],
                components=selected,
                fallback_index=min(index + 1, len(selected) - 1),
            )
            if next_component_node != component_node:
                lines.append(f"  {component_node}->>{next_component_node}: {_handoff_message(visible_steps[index + 1])}")
    first_actor = "A1"
    final_component = _step_component(visible_steps[-1], components=selected, fallback_index=min(len(selected) - 1, len(visible_steps) - 1))
    lines.append(f"  {final_component}-->>{first_actor}: show outcome, evidence, and next action")
    return "\n".join(lines) + "\n"


def first_path_flowchart_mermaid(
    *,
    label: str,
    actors: list[str],
    components: list[dict[str, Any]],
    first_path: str,
    semantic_model: Mapping[str, Any] | None = None,
) -> str:
    """Render the accepted first path as an Odylith-style Atlas flowchart."""

    selected = [dict(row) for row in active_release_components(components)] if components else []
    selected = selected[:7] or [{"label": f"{label} product core"}]
    steps = sequence_event_steps(first_path, semantic_model=semantic_model, dedupe=True)
    if not steps:
        steps = ["Start the accepted path", "Record product state and evidence", "Review the outcome and blockers"]
    visible_steps = _flowchart_visible_steps(steps)
    actor_label = _actor_role_label((actors or [f"{label} user"])[0])
    previous = "actor"
    used_components: set[str] = set()
    step_rows: list[tuple[int, str, str]] = []
    for index, step in enumerate(visible_steps, start=1):
        owner = _step_component(step, components=selected, fallback_index=min(index - 1, len(selected) - 1))
        used_components.add(owner)
        step_rows.append((index, step, owner))
    lines = [
        "flowchart LR",
        f'  actor["User action<br/>{_flow_label(actor_label, width=26, max_lines=3, limit=72)}"]',
    ]
    used_indexes = sorted(int(node[1:]) for node in used_components if node.startswith("C") and node[1:].isdigit())
    for index in used_indexes:
        component = selected[index - 1] if 0 <= index - 1 < len(selected) else {}
        lines.append(
            f'  C{index}["{_flow_label(str(component.get("label", "")) or f"Component {index}", width=28, max_lines=3, limit=84)}"]'
        )
    for index, step, owner in step_rows:
        step_node = f"S{index}"
        lines.append(f'  {step_node}["{_flow_label(_step_action_label(step), width=30, max_lines=4, limit=112)}"]')
        lines.append(f"  {previous} --> {step_node}")
        lines.append(f"  {step_node} --> {owner}")
        previous = owner
    lines.append('  proof["Outcome<br/>state, evidence, and next action stay visible"]')
    lines.append(f"  {previous} --> proof")
    lines.extend(
        [
            "  classDef actor fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;",
            "  classDef step fill:#FFFFFF,stroke:#CBD5E1,color:#17233A,stroke-width:1px;",
            "  classDef service fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
            "  classDef proof fill:#FFF7ED,stroke:#FDBA74,color:#17233A,stroke-width:1px;",
            "  class actor actor;",
            "  class " + ",".join(f"S{index}" for index in range(1, len(visible_steps) + 1)) + " step;",
            "  class " + ",".join(sorted(used_components) or ["C1"]) + " service;",
            "  class proof proof;",
        ]
    )
    return "\n".join(lines) + "\n"


def _flowchart_visible_steps(steps: list[str], *, limit: int = 10) -> list[str]:
    if len(steps) <= limit:
        return list(steps)
    return [*steps[: max(0, limit - 1)], steps[-1]]


def best_component_node_for_text(value: str, *, components: list[dict[str, Any]]) -> str:
    """Return the component node id whose local language best matches the text."""

    scored: list[tuple[int, int, int, str]] = []
    terms = _sequence_terms(value)
    if not terms:
        return ""
    for index, component in enumerate(components[:7], start=1):
        label_score = len(terms & _sequence_terms(component.get("label", "")))
        component_text = " ".join(
            str(component.get(key, ""))
            for key in ("label", "source_system_description", "responsibility", "boundary")
        )
        body_score = len(terms & _sequence_terms(component_text))
        score = label_score * 3 + body_score
        if score:
            scored.append((score, label_score, -index, _node_id("component", index)))
    scored.sort(reverse=True)
    return scored[0][3] if scored else ""


def _step_actor(step: str, *, actors: list[str], fallback_index: int) -> str:
    if _starts_with_path_action(step):
        return "A1"
    axis_index = _step_axis_actor_index(step, rows=actors)
    if axis_index is not None:
        return f"A{axis_index + 1}"
    if _starts_with_primary_actor_clause(step):
        return "A1"
    target = _best_index_for_text(step, rows=actors, default=fallback_index)
    return f"A{target + 1}"


def _step_axis_actor_index(step: str, *, rows: list[str]) -> int | None:
    text = _compact_text(step).casefold()
    direct_subjects: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
        (("editor", "chair"), ("editor", "chair", "manager", "coordinator", "supervisor", "owner")),
        (("record owner", "clerk"), ("record owner", "clerk", "publisher", "records")),
        (("applicant", "submit", "request"), ("applicant", "submitter", "requester", "customer")),
        (("reviewer", "reviewers"), ("reviewer", "evaluator", "analyst", "inspector", "approver")),
        (("admin", "administrator"), ("admin", "administrator", "config", "maintainer", "support")),
    )
    for step_tokens, actor_tokens in direct_subjects:
        if not any(token in text for token in step_tokens):
            continue
        for index, row in enumerate(rows):
            row_text = row.casefold()
            if any(token in row_text for token in actor_tokens):
                return index
    axes: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
        (("reviewer", "feedback", "score", "quality", "reproducibility"), ("reviewer", "evaluator", "analyst", "inspector", "approver")),
        (("editor", "chair", "screen", "assign", "compare", "decision"), ("editor", "chair", "manager", "coordinator", "supervisor", "owner")),
        (("applicant", "submit", "request", "receives"), ("applicant", "submitter", "requester", "customer")),
        (("admin", "configure", "policy", "template", "deadline", "permission"), ("admin", "administrator", "config", "maintainer", "support")),
    )
    for step_tokens, actor_tokens in axes:
        if not any(token in text for token in step_tokens):
            continue
        for index, row in enumerate(rows):
            row_text = row.casefold()
            if any(token in row_text for token in actor_tokens):
                return index
    return None


def _step_component(step: str, *, components: list[dict[str, Any]], fallback_index: int) -> str:
    label_rows = [str(component.get("label", "")) for component in components]
    rows = [
        " ".join(str(component.get(key, "")) for key in ("label", "source_system_description", "responsibility", "boundary"))
        for component in components
    ]
    axis_index = _step_axis_component_index(step, rows=label_rows, fallback_index=fallback_index)
    if axis_index is not None:
        return f"C{axis_index + 1}"
    target = _best_index_for_text(step, rows=rows, default=fallback_index)
    return f"C{target + 1}"


def _step_axis_component_index(step: str, *, rows: list[str], fallback_index: int = 0) -> int | None:
    text = _compact_text(step).casefold()
    step_terms = _sequence_terms(text)
    if not step_terms:
        return None
    if re.search(r"\b(?:highlight|highlights|choose|chooses|display|show|shows|review|compare|compares)\b", text):
        for index, row in enumerate(rows):
            row_terms = _sequence_terms(row)
            if row_terms & {"comparison", "display", "presentation", "review", "selected", "selection", "surface", "view"}:
                return index
    if re.search(r"\b(?:calculate|calculates|compute|computes|derive|derives)\b", text) and re.search(
        r"\b(?:price|pricing|cost|discount|quote|quoted)\b",
        text,
    ):
        for index, row in enumerate(rows):
            row_terms = _sequence_terms(row)
            if row_terms & {"price", "pricing", "cost", "discount", "quote", "quoted"}:
                return index
    scored: list[tuple[int, int, int]] = []
    for index, row in enumerate(rows):
        row_text = row.casefold()
        row_terms = _sequence_terms(row)
        exact = len(step_terms & row_terms)
        fuzzy = sum(1 for step_term in step_terms for row_term in row_terms if _term_related(step_term, row_term))
        score = exact * 3 + fuzzy
        if re.search(r"\b(?:show|shows|see|sees|view|views|display|renders?)\b", text) and (
            row_terms & {"dashboard", "display", "interface", "owner", "presentation", "result", "summary", "surface", "timeline", "view"}
        ):
            score += 12
        if re.search(r"\b(?:align|aligned|correlat|correlation|overlay|overlaid|timeline|trend|chart|visuali[sz]e)\b", text) and (
            row_terms & {"alignment", "correlation", "dashboard", "display", "overlay", "timeline", "trend", "view", "visualization"}
        ):
            score += 42
        if re.search(r"\b(?:add|adds|enter|enters|entry|log|logs|manual|record|records|save|saves|trip|upload)\b", text) and (
            row_terms & {"capture", "entry", "form", "history", "intake", "log", "profile", "record", "store", "vehicle"}
        ):
            score += 14
        if re.search(r"\b(?:intervention|dose|dosing|adherence)\b", text) and (
            row_terms & {"intervention", "dose", "dosing", "adherence", "schedule", "scheduling", "log"}
        ):
            score += 30
        if re.search(r"\b(?:calculate|calculates|compute|computes|derive|derives|estimate|estimated|estimates|metric|metrics|trend|update|updates)\b", text) and (
            row_terms & {"calculation", "engine", "estimation", "estimate", "metric", "metrics", "trend"}
        ):
            score += 12
        if re.search(r"\b(?:calculate|calculates|compute|computes|derive|derives|evaluate|evaluates)\b", text) and (
            row_terms & {"comparison", "option", "rank", "ranking", "score", "scoring", "selection"}
        ):
            score += 26
        if re.search(r"\b(?:plan|target|recommendation|adjusted|adjustment|off\s+track)\b", text) and (
            row_terms & {"plan", "target", "recommendation", "adjustment"}
        ):
            score += 18
        if re.search(r"\b(?:log|logs|progress|daily)\b", text) and (
            row_terms & {"daily", "progress", "log", "logging"}
        ):
            score += 18
        if re.search(r"\b(?:reminder|reminders|follow-up|followup|updates?\s+stop|unsafe|guardrail)\b", text) and (
            row_terms & {"reminder", "notification", "guardrail", "follow-up", "followup"}
        ):
            score += 18
        if re.search(r"\b(?:price|pricing|cost|discount|schedule|transfer)\b", text) and (
            row_terms & {"price", "pricing", "cost", "discount", "schedule", "transfer", "evidence"}
        ):
            score += 16
        if re.search(r"\b(?:price|pricing|cost|discount)\b", text) and (
            row_terms & {"price", "pricing", "cost", "discount", "quote", "quoted"}
        ):
            score += 20
        if re.search(r"\b(?:schedule|schedules|timetable|departure|arrival|transfer)\b", text) and (
            row_terms & {"schedule", "timetable", "departure", "arrival", "transfer"}
        ):
            score += 10
        if re.search(r"\b(?:accept|dismiss|recommendation|suggestion|card|rank|ranks)\b", text) and (
            row_terms & {"advice", "card", "recommendation", "suggestion"}
        ):
            score += 12
        if re.search(r"\b(?:attach|attaches|create|creates|draft|drafts|enter|enters|import|imports|open|opens|receive|receives|select|selects|submit|submits|upload|uploads|validate|validates)\b", text) and (
            row_terms & {"application", "capture", "entry", "intake", "packet", "submission"}
        ):
            score += 12
        if re.search(r"\bopen(?:s)?\b", text) and re.search(r"\bpacket\b", text) and (
            row_terms & {"intake", "versioning", "import", "submission"}
        ):
            score += 18
        if re.search(r"\b(?:result|reason|qualified|qualification|decision|returns?|next steps?)\b", text) and (
            row_terms & {"decision", "reason", "result", "qualification", "outcome"}
        ):
            score += 10
        if re.search(r"\b(?:screen|screens|check|checks|assign|assigns|match|matches|route|routes)\b", text) and (
            row_terms & {"assignment", "routing", "eligibility", "conflict", "matching"}
        ):
            score += 7
        if (step_terms & {"feedback", "form", "score", "scoring", "rubric", "answer", "assessment", "evaluation"}) and (
            row_terms & {"form", "scoring", "score", "rubric", "assessment", "evaluation"}
        ):
            score += 8
        if re.search(r"\b(?:question|questions|response|responses|follow-up|followup|preparer|preparers|resolved|unresolved)\b", text) and (
            row_terms & {"question", "response", "issue", "tracker", "follow-up", "followup", "preparer", "resolved", "unresolved"}
        ):
            score += 18
        if re.search(r"\b(?:rationale|final|finalize|finalized|outcome|condition|decision|record)\b", text) and (
            row_terms & {"decision", "rationale", "outcome", "condition", "vote", "signoff"}
        ):
            score += 18
        if re.search(r"\b(?:compare|compares|comparison)\b", text) and (
            row_terms & {"comparison", "recommendation", "readiness", "dashboard"}
        ):
            score += 8
        if re.search(r"\b(?:receive|receives|notify|notifies|sent|delivered|delivery)\b", text) and (
            row_terms & {"notification", "delivery", "deadline", "message", "freshness"}
        ):
            score += 8
        if re.search(r"\b(?:price|cost|pricing|charge|quote|quoted)\b", text) and (
            row_terms & {"price", "pricing", "cost", "quote", "quoted", "option", "estimate"}
        ):
            score += 8
        if re.search(r"\b(?:calculate|calculates|compute|computes|derive|derives|estimate|estimates)\b", text) and re.search(
            r"\b(?:evidence|proof|calculation|metric|measurement|estimate)\b",
            row_text,
        ):
            score += 5
        if re.search(r"\b(?:reminder|reminders|follow-up|followup)\b", text) and (
            row_terms & {"reminder", "notification", "follow-up", "followup"}
        ):
            score += 8
        if re.search(r"\b(?:highlight|highlights|choose|chooses|display|show|shows)\b", text) and (
            row_terms & {"surface", "review", "display", "selected", "selection", "comparison"}
        ):
            score += 18
        if re.search(r"\b(?:store|stores)\b", text) and (
            row_terms & {"surface", "review", "display", "selected", "selection", "route", "comparison"}
        ):
            score += 9
        if re.search(r"\b(?:publish|publishes|attachment|attachments|audit|history|replay)\b", text) and (
            row_terms & {"audit", "trail", "history", "provenance", "source-backed", "attachment"}
        ):
            score += 24
        if index == fallback_index and exact:
            score += 30
        if score:
            scored.append((score, -abs(index - fallback_index), -index))
    if scored:
        scored.sort(reverse=True)
        return -scored[0][2]
    return None


def _term_related(left: str, right: str) -> bool:
    if left == right:
        return True
    return len(left) >= 5 and len(right) >= 5 and (left.startswith(right) or right.startswith(left))


def _best_index_for_text(value: str, *, rows: list[str], default: int) -> int:
    terms = _sequence_terms(value)
    scored: list[tuple[int, int]] = []
    for index, row in enumerate(rows):
        score = len(terms & _sequence_terms(row))
        if score:
            scored.append((score, -index))
    if not scored:
        return max(0, min(default, max(0, len(rows) - 1)))
    scored.sort(reverse=True)
    return -scored[0][1]


def _starts_with_path_action(step: str) -> bool:
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", _compact_text(step), flags=re.IGNORECASE)
    text = re.sub(r"^(?:the\s+)?(?:product|app|application|system)\s+", "", text, flags=re.IGNORECASE)
    return bool(
        re.match(
            rf"^(?:{_ACTION_VERB_PATTERN}|explains?)\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def _starts_with_primary_actor_clause(step: str) -> bool:
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", _compact_text(step), flags=re.IGNORECASE)
    if re.match(r"^(?:the\s+)?(?:product|app|application|system)\b", text, re.IGNORECASE):
        return True
    if re.match(r"^(?:a|an|the|one)\s+(?:user|person|actor|requester|customer|operator|reviewer)\b", text, re.IGNORECASE):
        return True
    return bool(
        re.match(
            r"^(?:adds?|adjusts?|edits?|corrects?|records?|logs?|creates?|enters?|views?|sees?|shows?)\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def _step_message(value: str, *, keep_actor_subject: bool = True) -> str:
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", _strip_dangling_tail(_trim(value, 150)), flags=re.IGNORECASE)
    text = re.sub(r"^(?:the\s+)?(?:product|app|application|system)\s+", "", text, flags=re.IGNORECASE)
    if not keep_actor_subject:
        text = _strip_primary_actor_subject(text)
    if text:
        text = text[:1].upper() + text[1:]
    return _without_ellipsis(mermaid_text.wrap_mermaid_label(text, width=34, max_lines=4, limit=160)) or "advance accepted path"


def _step_action_label(value: str) -> str:
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", _strip_dangling_tail(_trim(value, 130)), flags=re.IGNORECASE)
    text = re.sub(r"^(?:the\s+)?(?:product|app|application|system)\s+", "", text, flags=re.IGNORECASE)
    role_can = re.match(
        r"^(?:a|an|the|one)\s+(?P<role>[A-Za-z][A-Za-z0-9 /&'()-]{1,60}?)\s+can\s+(?P<verb>[A-Za-z]+)\b(?P<rest>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if role_can:
        role = role_can.group("role").strip()
        verb = _third_person_verb(role_can.group("verb"))
        rest = _role_can_rest_to_third_person(role_can.group("rest"))
        text = f"{role} {verb}{rest}".strip(" .")
        return text[:1].upper() + text[1:] if text else "Advance accepted path"
    text = _strip_primary_actor_subject(text)
    text = re.sub(r"^(?:they|them|their)\s+", "", text, flags=re.IGNORECASE).strip(" .")
    text = _imperative_handoff_focus(text)
    return text[:1].upper() + text[1:] if text else "Advance accepted path"


def _third_person_verb(value: str) -> str:
    verb = str(value or "").strip()
    if not verb:
        return verb
    irregular = {"do": "does", "go": "goes", "have": "has"}
    lowered = verb.casefold()
    if lowered in irregular:
        return irregular[lowered]
    if lowered.endswith(("s", "x", "z", "ch", "sh")):
        return f"{verb}es"
    if lowered.endswith("y") and len(verb) > 1 and lowered[-2] not in {"a", "e", "i", "o", "u"}:
        return f"{verb[:-1]}ies"
    return f"{verb}s"


def _role_can_rest_to_third_person(value: str) -> str:
    rest = str(value or "")

    def replace_comma(match: re.Match[str]) -> str:
        prefix = " and " if match.group("and") else ", "
        return f"{prefix}{_third_person_verb(match.group('verb'))}"

    rest = re.sub(
        rf"\s*,\s+(?P<and>and\s+)?(?P<verb>{_BASE_ACTION_VERB_PATTERN})\b",
        replace_comma,
        rest,
        flags=re.IGNORECASE,
    )
    return re.sub(
        rf"\s+and\s+(?P<verb>{_BASE_ACTION_VERB_PATTERN})\b",
        lambda match: f" and {_third_person_verb(match.group('verb'))}",
        rest,
        flags=re.IGNORECASE,
    )


def _handoff_message(next_step: str) -> str:
    focus = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", _strip_dangling_tail(_trim(next_step, 90)), flags=re.IGNORECASE)
    focus = re.sub(r"^(?:a|an|the)\s+", "", focus, flags=re.IGNORECASE).strip(" .")
    focus = re.sub(r"^(?:the\s+)?(?:product|app|application|system)\s+", "", focus, flags=re.IGNORECASE).strip(" .")
    focus = _strip_primary_actor_subject(focus)
    if not focus:
        focus = "next accepted action"
    focus = _imperative_handoff_focus(focus)
    if _starts_with_path_action(focus):
        label = f"next step: {focus[:1].lower()}{focus[1:]}"
    else:
        label = f"handoff: {focus[:1].lower()}{focus[1:]}"
    return _without_ellipsis(mermaid_text.wrap_mermaid_label(label, width=34, max_lines=4, limit=160))


def _strip_primary_actor_subject(value: str) -> str:
    text = re.sub(
        r"^(?:(?:a|an|the|one)\s+)?(?:user|person|actor|requester|customer|operator|reviewer|coordinator)\s+",
        "",
        _compact_text(value),
        count=1,
        flags=re.IGNORECASE,
    ).strip(" .")
    match = re.match(
        rf"^(?P<subject>(?:(?:a|an|the|one)\s+)(?:[A-Za-z0-9][A-Za-z0-9/-]*\s+){{1,4}})(?P<verb>{_ACTION_VERB_PATTERN})\b(?P<rest>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if match and re.search(
        r"\b(?:actor|applicant|borrower|coordinator|customer|owner|participant|patient|person|requester|reviewer|supervisor|user)\b",
        match.group("subject"),
        flags=re.IGNORECASE,
    ):
        text = f"{match.group('verb')}{match.group('rest')}".strip(" .")
    elif match and re.match(r"^(?:a|an|the|one)\s+", match.group("subject"), flags=re.IGNORECASE) and not re.search(
        r"\b(?:app|application|dashboard|engine|product|service|system|view|workspace)\b",
        match.group("subject"),
        flags=re.IGNORECASE,
    ):
        text = f"{match.group('verb')}{match.group('rest')}".strip(" .")
    return text


def _imperative_handoff_focus(value: str) -> str:
    text = _compact_text(value).strip(" .")
    replacements = {
        "accepts": "accept",
        "adds": "add",
        "attaches": "attach",
        "assigns": "assign",
        "captures": "capture",
        "calculates": "calculate",
        "checks": "check",
        "chooses": "choose",
        "closes": "close",
        "collects": "collect",
        "compares": "compare",
        "completes": "complete",
        "computes": "compute",
        "confirms": "confirm",
        "creates": "create",
        "decides": "decide",
        "dismisses": "dismiss",
        "enters": "enter",
        "evaluates": "evaluate",
        "exports": "export",
        "fetches": "fetch",
        "finds": "find",
        "gets": "get",
        "groups": "group",
        "highlights": "highlight",
        "imports": "import",
        "notifies": "notify",
        "lets": "let",
        "links": "link",
        "logs": "log",
        "displays": "display",
        "opens": "open",
        "orders": "order",
        "produces": "produce",
        "publishes": "publish",
        "ranks": "rank",
        "reads": "read",
        "receives": "receive",
        "renders": "render",
        "returns": "return",
        "records": "record",
        "requests": "request",
        "resolves": "resolve",
        "reviews": "review",
        "routes": "route",
        "saves": "save",
        "sees": "see",
        "selects": "select",
        "shows": "show",
        "screens": "screen",
        "sends": "send",
        "schedules": "schedule",
        "stores": "store",
        "submits": "submit",
        "tracks": "track",
        "validates": "validate",
        "verifies": "verify",
        "votes": "vote",
        "explains": "explain",
        "hands": "hand",
        "preserves": "preserve",
    }
    first, sep, rest = text.partition(" ")
    replacement = replacements.get(first.casefold())
    if replacement:
        text = f"{replacement}{sep}{rest}".strip()
    text = re.sub(
        r"^(manually\s+)(logs|enters|selects|submits|saves|chooses|clicks|accepts|dismisses|records|captures|reviews)\b",
        lambda match: match.group(1)
        + {
            "logs": "log",
            "enters": "enter",
            "selects": "select",
            "submits": "submit",
            "saves": "save",
            "chooses": "choose",
            "clicks": "click",
            "accepts": "accept",
            "dismisses": "dismiss",
            "records": "record",
            "captures": "capture",
            "reviews": "review",
        }[match.group(2).casefold()],
        text,
        flags=re.IGNORECASE,
    )
    for source, target in replacements.items():
        text = re.sub(rf"((?:[,;]|\band\b|\bor\b)\s+){re.escape(source)}\b", rf"\1{target}", text, flags=re.IGNORECASE)
    return text


def _sequence_terms(value: object) -> set[str]:
    return set(
        ordered_terms(
            _compact_text(str(value)),
            stopwords=_SEQUENCE_TERM_STOPWORDS,
            stem_ing=True,
        )
    )


def _participant_label(value: str) -> str:
    text = _actor_role_label(value)
    return _without_ellipsis(mermaid_text.wrap_mermaid_label(text, width=24, max_lines=5, limit=120) or "Participant")


def _actor_role_label(value: object) -> str:
    text = display_text.strip_inline_markdown_emphasis_tokens(str(value or ""))
    text = re.split(r"\s+[—-]\s+|:", text, maxsplit=1)[0]
    text = text.replace("(", " ").replace(")", " ")
    text = re.sub(r"\bprimary\b", "", text, flags=re.IGNORECASE)
    text = re.split(
        r"\b(?:who|that|where|when|while|with|filling|reading|reviewing|configuring|tracking|using|entering|submitting|following|managing|auditing|approving)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    text = re.sub(r"\s+", " ", text).strip(" ,.;:-")
    return _trim(text or "Product user", 58)


def _flow_label(value: str, *, width: int, max_lines: int, limit: int) -> str:
    return _without_ellipsis(mermaid_text.wrap_mermaid_label(_trim(value, limit), width=width, max_lines=max_lines, limit=limit))


def _without_ellipsis(value: str) -> str:
    return str(value or "").replace("…", "").replace("...", "").rstrip(" ,;:")


def _trim(value: str, limit: int) -> str:
    text = _compact_text(value)
    if len(text) <= limit:
        return text
    clipped = clip_text_at_word_boundary(text, limit=limit)
    return _balance_label(_strip_dangling_tail(clipped))


def _balance_label(value: str) -> str:
    text = _compact_text(value).strip(" ,;:.")
    if text.count("(") > text.count(")"):
        text = text.rsplit("(", 1)[0].rstrip(" ,;:.")
    if text.count("[") > text.count("]"):
        text = text.rsplit("[", 1)[0].rstrip(" ,;:.")
    return text


def _strip_dangling_tail(value: str) -> str:
    text = _compact_text(value).rstrip(" ,;:.")
    while True:
        cleaned = re.sub(
            r"\b(?:a|an|and|as|at|because|by|can|for|from|if|in|into|lets|must|of|on|or|should|that|the|through|tied|to|until|when|while|with|without|alongside)$",
            "",
            text,
            flags=re.IGNORECASE,
        ).rstrip(" ,;:.")
        if cleaned == text:
            return cleaned
        text = cleaned


def _compact_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _node_id(prefix: str, index: int) -> str:
    return f"{prefix}{index}"


__all__ = ["best_component_node_for_text", "first_path_flowchart_mermaid", "sequence_mermaid"]
