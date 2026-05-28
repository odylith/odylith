"""Sequence-diagram routing for confirmed greenfield Atlas output."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from odylith.runtime.common import display_text
from odylith.runtime.common import mermaid_text
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import active_release_components
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_steps
from odylith.runtime.domain_intelligence.greenfield_text import normalize_domain_token


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
    steps = _semantic_event_steps(semantic_model) or _first_path_steps(first_path)
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


def best_component_node_for_text(value: str, *, components: list[dict[str, Any]]) -> str:
    """Return the component node id whose local language best matches the text."""

    scored: list[tuple[int, int, int, str]] = []
    terms = _domain_terms(value)
    if not terms:
        return ""
    for index, component in enumerate(components[:7], start=1):
        label_score = len(terms & _domain_terms(component.get("label", "")))
        component_text = " ".join(
            str(component.get(key, ""))
            for key in ("label", "source_system_description", "responsibility", "boundary")
        )
        body_score = len(terms & _domain_terms(component_text))
        score = label_score * 3 + body_score
        if score:
            scored.append((score, label_score, -index, _node_id("component", index)))
    scored.sort(reverse=True)
    return scored[0][3] if scored else ""


def _semantic_event_steps(semantic_model: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(semantic_model, Mapping):
        return []
    contract = semantic_model.get("first_path_contract")
    if not isinstance(contract, Mapping):
        return []
    rows = contract.get("events")
    if not isinstance(rows, list):
        return []
    steps: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        text = _compact_text(str(row.get("text") or row.get("mutation") or ""))
        if text:
            steps.append(text)
    return steps


def _first_path_steps(value: str) -> list[str]:
    semantic_steps = list(first_path_steps(value))
    if semantic_steps:
        return semantic_steps
    text = _compact_text(value)
    if not text:
        return []
    action_pattern = (
        r"attaches?|checks?|confirms?|verifies?|opens?|reviews?|reads?|compares?|saves?|records?|creates?|submits?|receives?|assigns?|"
        r"captures?|collects?|completes?|enters?|logs?|gets?|resolves?|moves?|builds?|exports?|imports?|screens?|sees?|supplies?|provides?|routes?|validates?|"
        r"calculates?|chooses?|fetches?|finds?|groups?|highlights?|lets?|links?|orders?|ranks?|selects?|shows?|stores|"
        r"tracks?|decides?|votes?|approves?|rejects?|declines?|requests?|notifies?|publishes?|preserves?|hands?|sends?|schedules|explains?|closes?"
    )
    numbered = [part.strip(" .") for part in re.split(r"(?:^|\s)\d+[.)]\s*", text) if part.strip(" .")]
    if len(numbered) > 1:
        first = numbered[0]
        if ":" in first:
            first = first.rsplit(":", 1)[-1].strip(" .")
        steps = [first, *numbered[1:]] if first else numbered[1:]
        return [_sentence(step).rstrip(".") for step in steps if len(re.findall(r"[A-Za-z0-9]+", step)) >= 3]
    steps = [part.strip(" .") for part in re.split(r"(?<=[.!?])\s+|;\s+", text) if part.strip(" .")]
    expanded: list[str] = []
    for step in steps:
        expanded.extend(
            part.strip(" .")
            for part in re.split(r"\s+and\s+(?=(?:the\s+)?[A-Za-z]+\s+receives?\b)", step)
            if part.strip(" .")
        )
    steps = expanded
    split_steps: list[str] = []
    for step in steps:
        split_steps.extend(
            part.strip(" .")
            for part in re.split(
                rf",\s+(?=(?:and\s+)?(?:(?:{action_pattern})\b|(?:(?:the|a|an)\s+)?[A-Za-z][A-Za-z0-9/-]*\s+(?:{action_pattern})\b))",
                step,
                flags=re.IGNORECASE,
            )
            if part.strip(" .")
        )
    steps = split_steps
    expanded_steps: list[str] = []
    for step in steps:
        expanded_steps.extend(
            part.strip(" .")
            for part in re.split(
                rf"\s+and\s+(?=(?:(?:{action_pattern})\b|(?:(?:the|a|an)\s+)?[A-Za-z][A-Za-z0-9/-]*\s+(?:{action_pattern})\b))",
                step,
                flags=re.IGNORECASE,
            )
            if part.strip(" .")
        )
    steps = expanded_steps
    return [_sentence(step).rstrip(".") for step in steps if step]


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
    axis_index = _step_axis_component_index(step, rows=label_rows)
    if axis_index is not None:
        return f"C{axis_index + 1}"
    target = _best_index_for_text(step, rows=rows, default=fallback_index)
    return f"C{target + 1}"


def _step_axis_component_index(step: str, *, rows: list[str]) -> int | None:
    text = _compact_text(step).casefold()
    step_terms = _domain_terms(text)
    if not step_terms:
        return None
    scored: list[tuple[int, int]] = []
    for index, row in enumerate(rows):
        row_text = row.casefold()
        row_terms = _domain_terms(row)
        exact = len(step_terms & row_terms)
        fuzzy = sum(1 for step_term in step_terms for row_term in row_terms if _term_related(step_term, row_term))
        score = exact * 3 + fuzzy
        if re.search(r"\b(?:show|shows|see|sees|view|views|display|renders?)\b", text) and (
            row_terms & {"view", "display", "surface", "timeline", "summary", "result", "presentation"}
        ):
            score += 6
        if re.search(r"\b(?:attach|attaches|create|creates|draft|drafts|import|imports|receive|receives|submit|submits|upload|uploads|validate|validates)\b", text) and (
            row_terms & {"capture", "entry", "intake", "packet", "submission"}
        ):
            score += 6
        if re.search(r"\b(?:screen|screens|check|checks|assign|assigns|match|matches|route|routes)\b", text) and (
            row_terms & {"assignment", "routing", "eligibility", "conflict", "matching"}
        ):
            score += 7
        if (step_terms & {"feedback", "form", "score", "scoring", "rubric", "answer", "assessment", "evaluation"}) and (
            row_terms & {"form", "scoring", "score", "rubric", "assessment", "evaluation"}
        ):
            score += 8
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
        if re.search(r"\b(?:highlight|highlights|choose|chooses|store|stores|display|show|shows)\b", text) and (
            row_terms & {"surface", "review", "display", "selected", "selection", "route", "comparison"}
        ):
            score += 9
        if re.search(r"\b(?:publish|publishes|attachment|attachments|audit|history|replay)\b", text) and (
            row_terms & {"audit", "trail", "history", "provenance", "source-backed", "attachment"}
        ):
            score += 10
        if score:
            scored.append((score, -index))
    if scored:
        scored.sort(reverse=True)
        return -scored[0][1]
    return None


def _term_related(left: str, right: str) -> bool:
    if left == right:
        return True
    return len(left) >= 5 and len(right) >= 5 and (left.startswith(right) or right.startswith(left))


def _best_index_for_text(value: str, *, rows: list[str], default: int) -> int:
    terms = _domain_terms(value)
    scored: list[tuple[int, int]] = []
    for index, row in enumerate(rows):
        score = len(terms & _domain_terms(row))
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
            r"^(?:attaches?|checks?|confirms?|verifies?|opens?|reviews?|reads?|compares?|saves?|records?|creates?|submits?|receives?|assigns?|captures?|collects?|completes?|enters?|logs?|gets?|resolves?|moves?|exports?|imports?|screens?|routes?|validates?|calculates?|chooses?|fetches?|finds?|groups?|highlights?|lets?|links?|orders?|ranks?|selects?|shows?|sees?|stores|tracks?|decides?|votes?|approves?|rejects?|declines?|requests?|notifies?|publishes?|preserves?|hands?|sends?|schedules|explains?|closes?)\b",
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
    return re.sub(
        r"^(?:(?:a|an|the|one)\s+)?(?:user|person|actor|requester|customer|operator|reviewer)\s+",
        "",
        _compact_text(value),
        count=1,
        flags=re.IGNORECASE,
    ).strip(" .")


def _imperative_handoff_focus(value: str) -> str:
    text = _compact_text(value).strip(" .")
    replacements = {
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
        "confirms": "confirm",
        "creates": "create",
        "decides": "decide",
        "enters": "enter",
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
        "opens": "open",
        "orders": "order",
        "publishes": "publish",
        "ranks": "rank",
        "reads": "read",
        "receives": "receive",
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
    for source, target in replacements.items():
        text = re.sub(rf"([,;]\s+){re.escape(source)}\b", rf"\1{target}", text, flags=re.IGNORECASE)
    return text


def _domain_terms(value: object) -> set[str]:
    stop = {
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
    terms: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", _compact_text(str(value)).casefold()):
        token = normalize_domain_token(raw, stopwords=stop)
        if token.endswith("ing") and len(token) > 6:
            token = token[:-3]
        if token:
            terms.add(token)
    return terms


def _sentence(value: str) -> str:
    text = display_text.strip_inline_markdown_emphasis_tokens(value).replace("`", "")
    text = " ".join(text.strip().split()).rstrip(".")
    if text:
        text = text[:1].upper() + text[1:]
    return f"{text}." if text else ""


def _participant_label(value: str) -> str:
    text = str(value or "").split("—", 1)[0].split(":", 1)[0].strip()
    return _without_ellipsis(mermaid_text.wrap_mermaid_label(text, width=24, max_lines=5, limit=120) or "Participant")


def _without_ellipsis(value: str) -> str:
    return str(value or "").replace("…", "").replace("...", "").rstrip(" ,;:")


def _trim(value: str, limit: int) -> str:
    text = _compact_text(value)
    if len(text) <= limit:
        return text
    clipped = text[: max(0, limit)].rstrip(" ,;:")
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip(" ,;:")
    return _strip_dangling_tail(clipped)


def _strip_dangling_tail(value: str) -> str:
    text = _compact_text(value).rstrip(" ,;:.")
    while True:
        cleaned = re.sub(
            r"\b(?:a|an|and|as|at|because|by|can|for|from|if|in|into|lets|must|of|on|or|should|the|through|tied|to|when|while|with|without)$",
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


__all__ = ["best_component_node_for_text", "sequence_mermaid"]
