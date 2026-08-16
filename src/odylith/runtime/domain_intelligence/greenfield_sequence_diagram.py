"""Sequence-diagram routing for confirmed greenfield Atlas output."""

from __future__ import annotations
from collections.abc import Mapping
import re
from typing import Any

from odylith.runtime.common import display_text
from odylith.runtime.common import mermaid_text
from odylith.runtime.common.prose_grammar import action_base_verb_pattern
from odylith.runtime.common.prose_grammar import base_action_verb
from odylith.runtime.common.prose_grammar import base_following_action_verbs
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import modal_actor_action_parts
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import strip_action_subject
from odylith.runtime.domain_intelligence.greenfield_first_path_temporal import base_from_gerund_action
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import active_release_components
from odylith.runtime.domain_intelligence.greenfield_sequence_action_labels import compact_result_object_label as _compact_result_object_label, strip_actor_role_subject as _strip_actor_role_subject, subjectless_action_label_clause as _subjectless_action_label_clause
from odylith.runtime.domain_intelligence.greenfield_sequence_labeling import compact_text as _compact_text, flow_label as _flow_label, header_body_label as _header_body_label, node_id as _node_id, strip_dangling_tail as _strip_dangling_tail, trim as _trim, without_ellipsis as _without_ellipsis
from odylith.runtime.domain_intelligence.greenfield_sequence_steps import ACTION_VERB_PATTERN as _ACTION_VERB_PATTERN
from odylith.runtime.domain_intelligence.greenfield_sequence_steps import sequence_event_steps
from odylith.runtime.domain_intelligence.greenfield_sequence_terminal_labels import terminal_step_loses_distinctive_tail, terminal_step_prefers_visible_result

_BASE_ACTION_VERB_PATTERN = action_base_verb_pattern()

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
_COMPONENT_ACTION_AXES: tuple[tuple[frozenset[str], frozenset[str], int], ...] = (
    (
        frozenset({"configure", "create", "define", "setup"}),
        frozenset({"builder", "configuration", "management", "manager", "setup", "workspace"}),
        18,
    ),
    (
        frozenset({"add", "attach", "capture", "create", "draft", "enter", "import", "intake", "log", "open", "record", "save", "select", "store", "submit", "upload"}),
        frozenset({"capture", "entry", "form", "intake", "ledger", "log", "record", "register", "source", "store", "submission"}),
        14,
    ),
    (
        frozenset({"choose", "compare", "display", "highlight", "render", "review", "see", "show", "surface", "view"}),
        frozenset({"comparison", "dashboard", "display", "outcome", "presentation", "result", "review", "selection", "summary", "surface", "timeline", "view"}),
        18,
    ),
    (
        frozenset({"check", "configure", "define", "parameter", "policy", "setting", "setup", "validate"}),
        frozenset({"configuration", "gate", "guardrail", "parameter", "policy", "setting", "setup", "validation"}),
        14,
    ),
    (
        frozenset({"align", "analyze", "calculate", "compute", "correlate", "derive", "estimate", "evaluate", "measure", "metric", "model", "predict", "score", "simulate", "trend", "update"}),
        frozenset({"analysis", "calculation", "comparison", "correlation", "engine", "estimate", "estimation", "measurement", "metric", "model", "ranking", "score", "scoring", "trend", "visualization"}),
        18,
    ),
    (
        frozenset({"accept", "adjust", "approve", "condition", "decide", "decision", "dismiss", "finalize", "plan", "rationale", "recommendation", "target"}),
        frozenset({"adjustment", "condition", "decision", "outcome", "plan", "rationale", "recommendation", "signoff", "target"}),
        16,
    ),
    (
        frozenset({"deliver", "delivery", "followup", "message", "notify", "receive", "reminder", "send"}),
        frozenset({"deadline", "delivery", "followup", "freshness", "message", "notification", "reminder"}),
        12,
    ),
    (
        frozenset({"assign", "conflict", "eligible", "match", "route", "screen"}),
        frozenset({"assignment", "conflict", "eligibility", "handoff", "matching", "queue", "routing"}),
        12,
    ),
    (
        frozenset({"audit", "history", "proof", "publish", "replay", "report"}),
        frozenset({"attachment", "audit", "evidence", "history", "ledger", "proof", "provenance", "record", "report", "trail"}),
        16,
    ),
    (
        frozenset({"answer", "assessment", "feedback", "question", "resolved", "response", "rubric", "unresolved"}),
        frozenset({"assessment", "evaluation", "feedback", "form", "issue", "question", "response", "rubric", "tracker"}),
        12,
    ),
)


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
    actor_rows = actors[:8] or [f"{label} user"]
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
    terminal_outcome = _semantic_visible_result(semantic_model)
    visible_steps = _ensure_flowchart_event_floor(
        _flowchart_visible_steps(steps),
        terminal_outcome,
        semantic_model=semantic_model,
    )
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
        f'  actor["{_flow_label(actor_label, width=26, max_lines=3, limit=72)}"]',
    ]
    used_indexes = sorted(int(node[1:]) for node in used_components if node.startswith("C") and node[1:].isdigit())
    for index in used_indexes:
        component = selected[index - 1] if 0 <= index - 1 < len(selected) else {}
        lines.append(
            f'  C{index}["{_flow_label(str(component.get("label", "")) or f"Component {index}", width=28, max_lines=3, limit=84)}"]'
        )
    for index, step, owner in step_rows:
        step_node = f"S{index}"
        is_terminal = index == len(step_rows)
        step_label = _terminal_step_label(step, terminal_outcome) if is_terminal else _step_action_label(step)
        lines.append(
            f'  {step_node}["{_flow_label(step_label, width=30, max_lines=5 if is_terminal else 4, limit=168 if is_terminal else 112)}"]'
        )
        lines.append(f"  {previous} --> {step_node}")
        lines.append(f"  {step_node} --> {owner}")
        previous = owner
    proof_body = _header_body_label("Proof result", terminal_outcome)
    proof_label = _flow_label(proof_body, width=30, max_lines=5, limit=168) if proof_body else "state, evidence, and next action stay visible"
    lines.append(f'  proof["Proof result<br/>{proof_label}"]')
    lines.append(f"  {previous} --> proof")
    lines.extend(
        [
            "  classDef personStyle fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;",
            "  classDef step fill:#FFFFFF,stroke:#CBD5E1,color:#17233A,stroke-width:1px;",
            "  classDef service fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
            "  classDef evidenceStyle fill:#FFF7ED,stroke:#FDBA74,color:#17233A,stroke-width:1px;",
            "  class actor personStyle;",
            "  class " + ",".join(f"S{index}" for index in range(1, len(visible_steps) + 1)) + " step;",
            "  class " + ",".join(sorted(used_components) or ["C1"]) + " service;",
            "  class proof evidenceStyle;",
        ]
    )
    return "\n".join(lines) + "\n"

def _flowchart_visible_steps(steps: list[str], *, limit: int = 10) -> list[str]:
    if len(steps) <= limit:
        return list(steps)
    return [*steps[: max(0, limit - 1)], steps[-1]]

def _ensure_flowchart_event_floor(
    steps: list[str],
    visible_result: str,
    *,
    semantic_model: Mapping[str, Any] | None,
) -> list[str]:
    rows = [_compact_text(step).strip(" .") for step in steps if _compact_text(step).strip(" .")]
    if len(rows) >= 3:
        return rows
    outcome = _compact_text(visible_result).strip(" .")
    if outcome and not any(_sequence_terms(outcome) <= _sequence_terms(step) for step in rows if _sequence_terms(step)):
        rows.append(f"Review {outcome[:1].lower()}{outcome[1:]}")
    candidates = (
        _typed_replay_proof_step(semantic_model),
        "Record state change evidence",
        "Review blockers and recovery path",
        "Confirm next action and owner",
    )
    outcome_terms = _sequence_terms(outcome)
    existing = {_compact_text(row).casefold().strip(" .") for row in rows}
    for candidate in candidates:
        normalized = _compact_text(candidate).strip(" .")
        if not normalized or normalized.casefold() in existing:
            continue
        if outcome_terms and outcome_terms <= _sequence_terms(normalized):
            continue
        rows.append(normalized)
        existing.add(normalized.casefold())
        if len(rows) >= 3:
            break
    return rows


def _typed_replay_proof_step(semantic_model: Mapping[str, Any] | None) -> str:
    if not isinstance(semantic_model, Mapping):
        return ""
    contract = semantic_model.get("first_path_contract")
    if not isinstance(contract, Mapping):
        return ""
    entity = _compact_text(str(contract.get("entity") or "")).strip(" .")
    persistence = _compact_text(str(contract.get("persistence") or "")).strip(" .")
    if not entity or not re.search(r"\breplay(?:able)?\b", persistence, flags=re.IGNORECASE):
        return ""
    return f"Preserve replayable state for {entity}"

def _semantic_visible_result(semantic_model: Mapping[str, Any] | None) -> str:
    if not isinstance(semantic_model, Mapping):
        return ""
    contract = semantic_model.get("first_path_contract")
    if not isinstance(contract, Mapping):
        return ""
    return _lower_leading_possessive_fragment(_compact_text(str(contract.get("visible_result") or "")).strip(" ."))


def _lower_leading_possessive_fragment(value: str) -> str:
    text = _compact_text(value).strip(" .")
    if not text:
        return ""
    words = text.split(maxsplit=1)
    first = words[0].strip(".,:;").casefold() if words else ""
    if first in {"my", "your", "their", "his", "her", "our", "its"}:
        return f"{text[:1].casefold()}{text[1:]}"
    return text

def _terminal_step_label(step: str, visible_result: str) -> str:
    outcome = _compact_text(visible_result).strip(" .")
    action_label = _step_action_label(step)
    step_terms = _sequence_terms(step)
    action_terms = _sequence_terms(action_label)
    candidate = "" if _is_modal_delegation_label(action_label) else _terminal_subjectless_action_candidate(step)
    if candidate and not terminal_step_loses_distinctive_tail(step_terms=step_terms, label_terms=_sequence_terms(candidate)):
        if terminal_step_loses_distinctive_tail(step_terms=step_terms, label_terms=action_terms) or len(candidate) < len(action_label):
            action_label = candidate[:1].upper() + candidate[1:]
            action_terms = _sequence_terms(action_label)
    outcome_terms = _sequence_terms(outcome)
    if outcome and terminal_step_prefers_visible_result(
        action_label,
        outcome,
        step_terms=action_terms,
        visible_terms=outcome_terms,
    ):
        return outcome[:1].upper() + outcome[1:]
    if _starts_with_path_action(action_label):
        return action_label
    if not outcome:
        return action_label
    step_terms = _sequence_terms(step)
    if step_terms and not step_terms <= outcome_terms:
        return action_label
    return outcome[:1].upper() + outcome[1:] if outcome else action_label


def _terminal_subjectless_action_candidate(step: str) -> str:
    return _compress_step_action_label(_imperative_handoff_focus(strip_action_subject(step))).strip(" .")


def _is_modal_delegation_label(value: str) -> bool:
    return _compact_text(value).casefold().startswith("let ")


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
    routing_text = strip_action_subject(text) or text
    step_terms = _sequence_terms(routing_text)
    if not step_terms:
        return None
    step_words = _axis_words(routing_text)
    object_terms = {term for term in step_terms if not base_action_verb(term)}
    scored: list[tuple[int, int, int]] = []
    for index, row in enumerate(rows):
        row_terms = _sequence_terms(row)
        row_words = _axis_words(row)
        exact = len(step_terms & row_terms)
        fuzzy = sum(1 for step_term in step_terms for row_term in row_terms if _term_related(step_term, row_term))
        object_overlap = any(
            _term_related(step_term, row_term)
            for step_term in object_terms
            for row_term in row_terms
        )
        axis_score = _component_axis_score(step_words, row_words) if not object_terms or object_overlap else 0
        score = exact * 3 + fuzzy + axis_score
        if index == fallback_index and exact:
            score += 6
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


def _component_axis_score(step_words: set[str], row_words: set[str]) -> int:
    score = 0
    for action_words, owner_words, weight in _COMPONENT_ACTION_AXES:
        if step_words & action_words and row_words & owner_words:
            score += weight
    return score


def _axis_words(value: object) -> set[str]:
    words: set[str] = set()
    for raw in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", _compact_text(str(value)).casefold()):
        token = raw.replace("-", "")
        if not token:
            continue
        words.add(token)
        action_base = base_action_verb(token)
        if action_base:
            words.add(action_base)
        gerund_base = base_from_gerund_action(token)
        if gerund_base:
            words.add(gerund_base)
        if token.endswith("ies") and len(token) > 4:
            words.add(f"{token[:-3]}y")
        elif token.endswith("es") and len(token) > 4:
            words.add(token[:-2])
        elif token.endswith("s") and len(token) > 4:
            words.add(token[:-1])
    return words

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
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", _strip_dangling_tail(_trim(value, 220)), flags=re.IGNORECASE)
    text = re.sub(r"^(?:the\s+)?(?:product|app|application|system)\s+", "", text, flags=re.IGNORECASE)
    compact_result = _compact_result_object_label(text)
    if compact_result:
        return compact_result
    modal_actor, modal_action = modal_actor_action_parts(text)
    if modal_action:
        text = _modal_actor_step_label(actor=modal_actor, action=modal_action)
        text = _compress_step_action_label(text)
        text = _subjectless_action_label_clause(text)
        return text[:1].upper() + text[1:] if text else "Advance accepted path"
    if _retains_readable_step_subject(text):
        text = _compress_step_action_label(text)
        return text[:1].upper() + text[1:] if text else "Advance accepted path"
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
    text = _compress_step_action_label(text)
    return text[:1].upper() + text[1:] if text else "Advance accepted path"

def _retains_readable_step_subject(value: str) -> bool:
    return bool(
        re.match(
            r"^(?:they|we|he|she|it)\s+",
            _compact_text(value),
            flags=re.IGNORECASE,
        )
    )

def _compress_step_action_label(value: str) -> str:
    text = _compact_text(value).strip(" .")
    text = re.sub(
        r"^over\s+the\s+following\s+days\s+(?:the\s+)?(?:app|application|product|system)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bif\s+[^.]{1,120}?\b(?:cross|crosses)\s+(?:a\s+)?safety\s+threshold\b",
        "when safety threshold is crossed",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bif\s+[^.]{1,120}?\b(?:trigger|triggers)\s+(?:an?\s+)?(?:escalation\s+)?warning\b",
        "when warning signs trigger",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+", " ", text).strip(" .")
    text = _title_named_result_tail(text)
    return _strip_dangling_tail(text)


def _title_named_result_tail(value: str) -> str:
    text = _compact_text(value).strip(" .")
    if not text:
        return ""
    heads = {"trend", "timeline", "summary", "status", "report", "readout", "result"}
    nouns = {"readout", "report", "result", "status", "summary", "timeline", "view"}
    words = text.split()
    for index in range(0, max(0, len(words) - 2)):
        if words[index].casefold().strip(".,:;") != "and":
            continue
        head = words[index + 1].casefold().strip(".,:;")
        noun = words[index + 2].casefold().strip(".,:;")
        if head in heads and noun in nouns:
            words[index + 1] = words[index + 1][:1].upper() + words[index + 1][1:]
    return " ".join(words)

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

def _modal_actor_step_label(*, actor: str, action: str) -> str:
    role = _actor_role_label(actor)
    singular = bool(re.match(r"^(?:a|an|the|one)\s+", role, flags=re.IGNORECASE))
    role = re.sub(r"^(?:a|an|the|one)\s+", "", role, flags=re.IGNORECASE).strip()
    singular = singular or not role.casefold().endswith("s")
    words = [word for word in _compact_text(action).strip(" .").split() if word]
    if not role or not words:
        return action
    verb = words[0]
    rest = " " + " ".join(words[1:]) if len(words) > 1 else ""
    if singular:
        verb = _third_person_verb(verb)
        rest = _role_can_rest_to_third_person(rest)
    return f"{role} {verb}{rest}".strip()

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
    text = _strip_actor_role_subject(text)
    match = re.match(
        rf"^(?P<subject>(?:(?:a|an|the|one)\s+)(?:[A-Za-z0-9][A-Za-z0-9/-]*\s+){{1,4}})(?P<verb>{_ACTION_VERB_PATTERN})\b(?!-)(?P<rest>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if match and re.search(
        r"\b(?:actor|applicant|coordinator|customer|owner|participant|person|requester|reviewer|supervisor|user)\b",
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
    return _subjectless_action_label_clause(text)

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
    text = re.sub(r"(?<!-)\bprimary\b(?!-)", "", text, flags=re.IGNORECASE)
    text = re.split(
        r"\b(?:who|that|where|when|while|with|filling|reading|reviewing|configuring|tracking|using|entering|submitting|following|managing|auditing|approving)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    text = re.sub(r"\s+", " ", text).strip(" ,.;:-")
    return _trim(text or "Product user", 58)

__all__ = ["best_component_node_for_text", "first_path_flowchart_mermaid", "sequence_mermaid"]
