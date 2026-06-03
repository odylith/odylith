"""Actor row completion for accepted greenfield Product Intent records."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_actor_labels import accepted_actor_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import focus_label as _focus_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import semantic_terms as _semantic_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_confirmed_text as _short
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_case_text as _title_case
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count as _word_count
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


_ROLE_WORDS = {
    "admin",
    "analyst",
    "auditor",
    "applicant",
    "beneficiary",
    "chief",
    "client",
    "coordinator",
    "customer",
    "director",
    "engineer",
    "expert",
    "inspector",
    "lead",
    "manager",
    "member",
    "operator",
    "owner",
    "planner",
    "reviewer",
    "requester",
    "resident",
    "staff",
    "submitter",
    "supervisor",
    "support",
    "team",
    "technician",
    "user",
    "volunteer",
}


def completed_actor_rows(intent: Mapping[str, Any], *, title: str) -> list[str]:
    rows = [row for row in confirmed_text_values(intent.get("human_actors")) if not _actor_row_is_meta(row)]
    labels = [_actor_label(row, title=title) for row in rows]
    labels = [label for label in labels if label and not _actor_label_has_clause_lead(label)]
    if not labels:
        labels.extend(_derived_actor_labels(intent, title=title))
    labels = list(unique_text(labels))[:5]

    first_path = _short(_clean(intent.get("first_path")), fallback="the accepted first path")
    state = _short(_clean(intent.get("state_object")), fallback="the accepted state")
    completed: list[str] = []
    for index, label in enumerate(labels):
        original = rows[index] if index < len(rows) else label
        description = actor_row_description(original)
        if description and _actor_label(original, title=title).casefold() == label.casefold():
            completed.append(f"{label}: {description}")
            continue
        completed.append(_actor_description(label=label, index=index, title=title, first_path=first_path, state=state))
    return list(unique_text(completed))


def actor_labels(intent: Mapping[str, Any]) -> list[str]:
    labels: list[str] = []
    for row in confirmed_text_values(intent.get("human_actors")):
        labels.append(_clean(row.split("—", 1)[0].split(":", 1)[0]))
    return [label for label in labels if label]


def actor_row_description(value: str) -> str:
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
        body = "reviews access, privacy, policy, risk, and evidence boundaries"
    elif re.search(r"\b(user|researcher|investor|analyst|operator)\b", label_text):
        body = f"uses {title} to reach a clear outcome, compare it with their goal, and decide what to do next"
    elif re.search(r"\b(author|applicant|submitter|requester|customer|client|resident|buyer|seller)\b", label_text):
        body = "provides the information the product needs and expects a clear result, explanation, and next step"
    elif re.search(r"\b(editor|manager|chair|coordinator|operator|supervisor|lead|owner|director)\b", label_text):
        body = "keeps the product outcome aligned with the real operational goal and decides when exceptions need human judgment"
    elif re.search(r"\bteam\b", label_text):
        body = "owns the operating context around the request, keeps expectations clear, and uses the product outcome to coordinate follow-up"
    elif re.search(r"\b(reviewer|inspector|evaluator|analyst|auditor|expert|approver|compliance)\b", label_text):
        body = "uses the product output to review quality, challenge weak results, and decide whether follow-up is needed"
    elif re.search(r"\b(coach|trainer|advisor|consultant|specialist)\b", label_text):
        body = "reviews progress, guidance quality, evidence, and escalation signals where the accepted path needs human support"
    elif re.search(r"\b(participant|observer|applicant)\b", label_text):
        body = "supplies input, context, or objections that must remain traceable to the first-path decision"
    elif re.search(r"\b(admin|administrator|config|maintainer|support|scheduler)\b", label_text):
        body = "owns the policies, settings, and operating limits that keep the product outcome reliable"
    else:
        path_role = _actor_path_role(label=label, first_path=first_path, state=state)
        if path_role:
            return f"{label}: {path_role}."
        body = (
            "contributes information, review, or action needed for the first product outcome and needs the result, limits, "
            "and next step to stay understandable"
        )
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
    clause = _strip_actor_subject_from_clause(clause, label=label)
    if not clause:
        return ""
    return f"uses the product around {clause[:1].lower() + clause[1:]} and needs the outcome to remain clear enough to act on"


def _strip_actor_subject_from_clause(value: str, *, label: str) -> str:
    """Remove a role label when it was copied into a clause as the subject."""

    text = _clean(value).strip(" .")
    if not text:
        return ""
    label_terms = sorted(_semantic_terms(label), key=len, reverse=True)
    if label_terms:
        lead = r"(?:a|an|the|one)?\s*(?:" + "|".join(re.escape(term) for term in label_terms) + r")"
        text = re.sub(rf"^{lead}\s+", "", text, count=1, flags=re.IGNORECASE).strip(" .")
    text = re.sub(
        r"^(?:signs?|opens?|starts?)\s+(?:in|into|the\s+app|the\s+product|the\s+site|the\s+web\s+app)\b[,.]?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text.strip(" .")


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
    return bool(actor_row_description(value))


def _derived_actor_labels(intent: Mapping[str, Any], *, title: str) -> list[str]:
    focus = _focus_label(title)
    first_path = _clean(intent.get("first_path"))
    story = _clean(intent.get("product_story"))
    state = _clean(intent.get("state_object"))
    candidates = unique_text(
        [
            *_role_candidates(first_path),
            *_role_candidates(state),
            *_role_candidates(story),
            *_role_candidates(_actor_context(intent)),
        ]
    )
    labels: list[str] = []
    for candidate in candidates:
        if _word_count(candidate) <= 5:
            label = _title_case(candidate)
            if not _actor_label_has_clause_lead(label):
                labels.append(label)
    labels = _dedupe_actor_labels(list(unique_text(labels)))
    if len(labels) < 2:
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
    candidates: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+|;\s+", _clean(text)):
        words = re.findall(r"[A-Za-z][A-Za-z/-]*", sentence)
        for index, word in enumerate(words):
            if word.casefold() not in _ROLE_WORDS:
                continue
            if _role_token_is_artifact_context(words, index):
                continue
            start = max(0, index - 2)
            phrase = " ".join(words[start : index + 1])
            phrase = re.sub(
                r"^(?:a|an|and|the|one|first|main|primary|current)\s+",
                "",
                phrase,
                flags=re.IGNORECASE,
            )
            phrase_words = phrase.split()
            if (
                len(phrase_words) >= 3
                and phrase_words[-2].casefold() in {"a", "an", "the"}
                and phrase_words[0].casefold().endswith("ing")
            ):
                phrase = phrase_words[-1]
            phrase = _trim_non_actor_lead_words(phrase)
            if (
                phrase
                and phrase.casefold() not in {"team"}
                and not _actor_label_has_clause_lead(phrase)
                and not phrase.casefold().startswith(("product ", "project ", "workflow "))
            ):
                candidates.append(phrase)
    return list(unique_text(candidates))


def _role_token_is_artifact_context(words: Sequence[str], index: int) -> bool:
    previous_token = words[index - 1].casefold().strip(".,;:-") if index > 0 else ""
    next_token = words[index + 1].casefold().strip(".,;:-") if index + 1 < len(words) else ""
    sentence = " ".join(words).casefold()
    if re.search(r"\b(?:defer(?:red|s)?|out\s+of\s+scope|non[-\s]?goals?|later|future|not\s+included)\b", sentence):
        return True
    artifact_neighbors = {
        "confirmation",
        "contact",
        "decision",
        "detail",
        "details",
        "field",
        "fields",
        "follow-up",
        "history",
        "information",
        "note",
        "notes",
        "record",
        "status",
        "visible",
    }
    if previous_token in artifact_neighbors or next_token in artifact_neighbors:
        return True
    current = words[index].casefold()
    return "-" in current and any(part in artifact_neighbors for part in current.split("-"))


def _dedupe_actor_labels(values: Sequence[str]) -> list[str]:
    labels = [
        re.sub(r"^(?:one|first|main|primary)\s+", "", _clean(value), flags=re.IGNORECASE).strip()
        for value in values
        if _clean(value)
    ]
    result: list[str] = []
    lowered_labels = [label.casefold() for label in labels]
    for label, lowered in zip(labels, lowered_labels):
        if any(other != lowered and other.endswith(f" {lowered}") for other in lowered_labels):
            continue
        result.append(label)
    return result


def _trim_non_actor_lead_words(value: str) -> str:
    words = _clean(value).split()
    non_actor_leads = {
        "a",
        "answer",
        "against",
        "an",
        "and",
        "after",
        "before",
        "because",
        "displays",
        "decision",
        "detail",
        "details",
        "evidence",
        "gives",
        "history",
        "in",
        "input",
        "places",
        "provides",
        "request",
        "note",
        "notes",
        "outcome",
        "path",
        "proof",
        "reason",
        "record",
        "release",
        "result",
        "returns",
        "scope",
        "shows",
        "state",
        "status",
        "summary",
        "the",
        "then",
        "when",
        "where",
        "which",
        "with",
    }
    while len(words) > 1 and words[0].casefold().strip(".,;:") in non_actor_leads:
        words.pop(0)
    if len(words) > 1 and words[-2].casefold().strip(".,;:") in non_actor_leads:
        words = words[-1:]
    return " ".join(words)


def _actor_label_has_clause_lead(value: str) -> bool:
    return bool(
        re.match(
            r"^(?:and|or|where|when|if|because|so|that|which|what|why|how|with|against|from|until|before|after|"
            r"displays?|gives?|places?|provides?|returns?|shows?)\b",
            _clean(value).casefold(),
        )
    )


def _actor_label(row: str, *, title: str) -> str:
    raw = _clean(str(row).split("—", 1)[0].split(":", 1)[0])
    raw = re.sub(r"^(?:a|an|the)\s+", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r"^(?:one|first|main|primary)\s+", "", raw, flags=re.IGNORECASE).strip()
    if not raw:
        return ""
    accepted = accepted_actor_label(str(row), project_focus=_focus_label(title))
    if accepted:
        accepted = re.sub(r"^(?:one|first|main|primary)\s+", "", accepted, flags=re.IGNORECASE).strip()
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


def _actor_context(intent: Mapping[str, Any]) -> str:
    parts = [
        _clean(intent.get("title")),
        _clean(intent.get("product_story")),
        _clean(intent.get("problem")),
        _clean(intent.get("customer")),
        _clean(intent.get("opportunity")),
        _clean(intent.get("product_view")),
        _clean(intent.get("state_object")),
        _clean(intent.get("first_path")),
        " ".join(confirmed_text_values(intent.get("human_actors"))),
    ]
    return ". ".join(part.strip(" .") for part in parts if part)


__all__ = ["actor_labels", "actor_row_description", "completed_actor_rows"]
