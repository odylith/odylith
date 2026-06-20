"""Actor-label normalization for confirmed greenfield product intent."""

from __future__ import annotations

from collections.abc import Sequence
import re

from odylith.runtime.domain_intelligence.greenfield_actor_terms import generic_actor_label_prefix
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


_QUALIFIER_RE = re.compile(
    r"^(?:primary|optional|optionally|secondary|main|target|first|initial|prospective|potential)\s*,?\s+",
    re.IGNORECASE,
)

_DESCRIPTION_MARKERS = (
    " responsible for ",
    " accountable for ",
    " acknowledging ",
    " asking ",
    " assigning ",
    " classifying ",
    " creating ",
    " drafting ",
    " filling ",
    " submitting ",
    " evaluating ",
    " configuring ",
    " checking ",
    " managing ",
    " reviewing ",
    " reading ",
    " handling ",
    " approving ",
    " owning ",
    " operating ",
    " coordinating ",
    " preparing ",
    " recording ",
    " receiving ",
    " requesting ",
    " responding ",
    " following ",
    " following up ",
    " trying to ",
    " seeking to ",
    " wanting to ",
    " needing to ",
    " using ",
    " who ",
    " that ",
)

_ROLE_WORDS = {
    "admin",
    "administrator",
    "advocate",
    "analyst",
    "applicant",
    "approver",
    "auditor",
    "author",
    "beneficiary",
    "caregiver",
    "chair",
    "client",
    "coach",
    "consultant",
    "contact",
    "coordinator",
    "customer",
    "editor",
    "engineer",
    "evaluator",
    "guardian",
    "inspector",
    "individual",
    "lead",
    "manager",
    "operator",
    "owner",
    "participant",
    "people",
    "person",
    "planner",
    "preparer",
    "recipient",
    "requester",
    "researcher",
    "reviewer",
    "safety reviewer",
    "advisor",
    "specialist",
    "submitter",
    "support",
    "sufferer",
    "trainer",
    "trainee",
    "user",
}

_GENERIC_HEADS = {
    "admin",
    "administrator",
    "beneficiary",
    "domain operator",
    "domain reviewer",
    "end user",
    "end-user",
    "evidence owner",
    "implementation owner",
    "operator",
    "owner",
    "individual",
    "people",
    "person",
    "primary user",
    "product operator",
    "project operator",
    "proof reviewer",
    "release owner",
    "reviewer",
    "risk reviewer",
    "support",
    "user",
    "workflow operator",
}

_GENERIC_ROLE_ONLY = {
    "admin",
    "administrator",
    "manager",
    "operator",
    "owner",
    "participant",
    "individual",
    "people",
    "person",
    "reviewer",
    "support",
    "user",
}

_FOCUS_STOPWORDS = {
    "a",
    "an",
    "app",
    "application",
    "and",
    "are",
    "as",
    "be",
    "before",
    "can",
    "complete",
    "configuring",
    "decide",
    "decides",
    "for",
    "from",
    "guidance",
    "handling",
    "improve",
    "improving",
    "in",
    "issue",
    "manage",
    "managing",
    "of",
    "on",
    "or",
    "own",
    "review",
    "reviewing",
    "service",
    "state",
    "system",
    "the",
    "their",
    "through",
    "to",
    "tool",
    "tracker",
    "trying",
    "use",
    "uses",
    "using",
    "with",
    "workspace",
}
_TITLE_CONNECTORS = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}


def accepted_actor_label(value: str, *, project_focus: str = "") -> str:
    """Return a project-specific actor label from accepted actor prose."""

    text = _clean(value).strip(" .")
    if not text:
        return ""
    head, body = _split_actor_row(text)
    explicit_body = bool(body)
    original_head = _strip_modal_actor_tail(_strip_qualifiers(head).strip(" ."))
    original_role = _role_suffix(original_head)
    if explicit_body and _is_concrete_actor_head(
        original_head,
        lower_head=_key(original_head),
        role=original_role,
    ):
        return original_head
    marker_head, marker_tail = _split_description_marker(head)
    marker_body_used = False
    if marker_head:
        head, marker_body = marker_head, marker_tail
        body = body or marker_body
        marker_body_used = not explicit_body and bool(marker_body)
    head = _strip_actor_head_articles(_strip_modal_actor_tail(_strip_qualifiers(head).strip(" .")))
    shared_head, shared_tail = _split_shared_subject_tail(head)
    if shared_head:
        head = shared_head
        body = body or shared_tail
        marker_body_used = marker_body_used or (not explicit_body and bool(shared_tail))
    action_head, action_tail = _split_actor_action_tail(head)
    if action_head:
        head = action_head
        body = body or action_tail
        marker_body_used = marker_body_used or (not explicit_body and bool(action_tail))
    if not head:
        return ""

    lower_head = _key(head)
    role = _role_suffix(head)
    if not explicit_body and not marker_body_used and _preserve_standalone_label(head, lower_head=lower_head, role=role):
        return head
    if explicit_body and _is_concrete_actor_head(head, lower_head=lower_head, role=role):
        return head
    activity_label = _generic_person_activity_label(
        head,
        lower_head=lower_head,
        role=role,
        body=body,
        marker_body_used=marker_body_used or explicit_body,
    )
    if activity_label:
        return activity_label
    composite_label = _project_specific_composite_head(head, lower_head=lower_head, project_focus=project_focus)
    if composite_label:
        return composite_label
    needs_focus = _head_needs_focus(lower_head, role=role) or (
        marker_body_used and lower_head == role and role in _GENERIC_ROLE_ONLY
    ) or (
        marker_body_used and lower_head == role and role in {"coordinator"}
    )
    if lower_head == role and role in {"admin", "administrator", "author"} and body:
        focus = _focus_from_actor_body(body, role=role)
        if focus:
            return _title_label(f"{focus} {role}")
    if needs_focus:
        if (marker_body_used or explicit_body) and role in {"operator", "owner", "support", "user"}:
            if _body_names_control_focus(body):
                focus = _focus_from_actor_body(body or text, role=role) or _focus_from_text(project_focus, role=role)
            else:
                focus = _focus_from_text(project_focus, role=role) or _focus_from_actor_body(body or text, role=role)
        elif marker_body_used:
            focus = _focus_from_actor_body(body or text, role=role) or _focus_from_text(project_focus, role=role)
        else:
            focus = _focus_from_text(project_focus, role=role) or _focus_from_actor_body(body or text, role=role)
        if focus and role:
            return _title_label(f"{focus} {role}")
        if focus:
            return _title_label(focus)
        return ""
    if original_head and marker_head and lower_head != role and not marker_body_used:
        return _title_label(original_head)
    return _title_label(head)


def actor_display_label(value: str, *, project_focus: str = "") -> str:
    """Return the concrete actor label that should appear in public prose."""

    label = accepted_actor_label(value, project_focus=project_focus)
    return _drop_generic_actor_alternative(label) or label


def localize_leading_actor_reference(
    value: str,
    *,
    actor_rows: Sequence[str] = (),
    project_focus: str = "",
    fallback: str = "first user",
) -> str:
    """Replace a generic leading actor reference with an accepted actor label."""

    text = _clean(value).strip()
    prefix = generic_actor_label_prefix(text)
    if not prefix:
        return text
    replacement = _first_actor_display_label(actor_rows, project_focus=project_focus) or fallback
    return f"{replacement}{text[len(prefix):]}"


def project_specific_actor_row(row: str, *, project_focus: str) -> str:
    """Rewrite one actor row so the visible label is not a stable-role placeholder."""

    text = _clean(row).strip(" .")
    if not text:
        return ""
    _head, body = _split_actor_row(text)
    label = actor_display_label(text, project_focus=project_focus)
    if not label:
        return text
    return f"{label}: {body}" if body else label


def _split_actor_row(value: str) -> tuple[str, str]:
    value = _strip_qualifiers(value).strip(" .")
    for separator in (" — ", " – ", " - ", ":"):
        head, sep, body = value.partition(separator)
        if sep and head.strip():
            return head.strip(" ."), body.strip(" .")
    comma_descriptor = re.match(
        r"^(?P<head>[A-Za-z][A-Za-z0-9 /&'()-]{1,100}?),\s+"
        r"(?P<body>(?:[A-Za-z]+ing\b\s+|(?:a|an|the|one)\s+)[A-Za-z][A-Za-z0-9 /&'()-]{2,160})$",
        value,
        flags=re.IGNORECASE,
    )
    if comma_descriptor and 1 <= len(comma_descriptor.group("head").split()) <= 8:
        head = _title_label(_strip_actor_head_articles(comma_descriptor.group("head").strip(" .")))
        return head, comma_descriptor.group("body").strip(" .")
    comma = re.match(
        r"^(?P<head>[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?),\s+"
        r"(?P<body>(?:a|an|the|one)\s+[A-Za-z][A-Za-z0-9 /&'()-]{2,120})$",
        value,
        flags=re.IGNORECASE,
    )
    if comma and 1 <= len(comma.group("head").split()) <= 5:
        return comma.group("head").strip(" ."), comma.group("body").strip(" .")
    action_head, action_tail = _split_actor_action_tail(value)
    if action_head:
        return action_head, action_tail
    return value, ""


def _split_description_marker(value: str) -> tuple[str, str]:
    lowered = value.casefold()
    matches = sorted(
        (index, marker)
        for marker in _DESCRIPTION_MARKERS
        if (index := lowered.find(marker)) > 0
    )
    for index, marker in matches:
        head = lowered[:index]
        tail = lowered[index + len(marker) :]
        if head.strip() and tail.strip():
            if _generic_person_head(head) and marker.strip() in {
                "acknowledging",
                "asking",
                "assigning",
                "checking",
                "classifying",
                "configuring",
                "coordinating",
                "creating",
                "drafting",
                "following",
                "handling",
                "managing",
                "owning",
                "preparing",
                "recording",
                "requesting",
                "responding",
                "reviewing",
                "using",
            }:
                return "", ""
            return value[:index].strip(" ."), value[index + len(marker) :].strip(" .")
    return "", ""


def _split_actor_action_tail(value: str) -> tuple[str, str]:
    """Split role labels such as "individual user running..." into label/body."""

    text = _clean(value).strip(" .")
    if not text:
        return "", ""
    words = text.split()
    if len(words) < 2:
        return "", ""
    for index, word in enumerate(words[1:], start=1):
        token = word.casefold().strip(".,;:")
        head_candidate = " ".join(words[:index]).strip(" .")
        if token == "being":
            continue
        if token not in {
            "acknowledging",
            "asking",
            "assigning",
            "checking",
            "classifying",
            "configuring",
            "coordinating",
            "creating",
            "drafting",
            "entering",
            "following",
            "handling",
            "helping",
            "logging",
            "managing",
            "monitoring",
            "owning",
            "preparing",
            "recording",
            "requesting",
            "reviewing",
            "responding",
            "running",
            "sharing",
            "tracking",
            "using",
            "watching",
        } and not (token.endswith("ing") and _generic_person_head(head_candidate)):
            continue
        head = head_candidate
        head = re.sub(r"^(?:a|an|the)\s+", "", head, flags=re.IGNORECASE).strip(" .")
        tail = " ".join(words[index:]).strip(" .")
        role = _role_suffix(head)
        if not role and _generic_person_head(head):
            role = "user"
        if role and 1 <= len(head.split()) <= 4 and tail:
            return _title_label(head), tail
    return "", ""


def _split_shared_subject_tail(value: str) -> tuple[str, str]:
    text = _clean(value).strip(" .")
    match = re.match(
        r"(?P<head>.+?)\s+(?P<tail>(?:the|a|an)\s+"
        r"[A-Za-z][A-Za-z-]*(?:\s+[A-Za-z][A-Za-z-]*){0,3}\s+"
        r"(?:shares?|sends?|gives?|provides?|submits?|uploads?|forwards?)\b.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return "", ""
    head = _strip_actor_head_articles(match.group("head"))
    if not head or len(head.split()) > 6:
        return "", ""
    return head, match.group("tail").strip(" .")


def _generic_person_activity_label(
    head: str,
    *,
    lower_head: str,
    role: str,
    body: str,
    marker_body_used: bool,
) -> str:
    if not marker_body_used or role != "user" or lower_head not in {"person", "people", "individual", "user"}:
        return ""
    text = _strip_parenthetical_qualifiers(body)
    match = re.match(r"(?P<verb>[A-Za-z]+ing)\s+(?P<tail>.+)$", text, flags=re.IGNORECASE)
    if not match:
        return ""
    focus = _focus_from_text(match.group("tail"), role="")
    if not focus:
        return ""
    head_label = "Person" if lower_head in {"person", "people", "individual"} else "User"
    return _title_label(f"{head_label} {match.group('verb')} {focus}")


def _strip_parenthetical_qualifiers(value: str) -> str:
    text = _clean(value)
    text = re.sub(
        r"\([^)]*\b(?:primary|secondary|optional|later|read-only|self|tracking|user|role)\b[^)]*\)",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    return _clean(text)


def _strip_qualifiers(value: str) -> str:
    text = _clean(value)
    while True:
        replacement = _QUALIFIER_RE.sub("", text).strip()
        if replacement == text:
            return replacement
        text = replacement


def _strip_actor_head_articles(value: str) -> str:
    return re.sub(r"^(?:a|an|the)\s+", "", _clean(value), flags=re.IGNORECASE).strip(" .")


def _strip_modal_actor_tail(value: str) -> str:
    text = _clean(value).strip(" .")
    words = text.split()
    if len(words) < 2 or words[-1].casefold().strip(".,;:") not in {"can", "must", "should"}:
        return text
    head = " ".join(words[:-1]).strip(" .")
    return head if _role_suffix(head) else text


def _head_needs_focus(lower_head: str, *, role: str) -> bool:
    if lower_head in _GENERIC_HEADS:
        return True
    if lower_head.startswith(("product ", "project ", "domain ", "workflow ")) and role in _ROLE_WORDS:
        return True
    return lower_head == role and role in _GENERIC_ROLE_ONLY


def _is_concrete_actor_head(head: str, *, lower_head: str, role: str) -> bool:
    if not head:
        return False
    if _head_needs_focus(lower_head, role=role):
        return False
    if lower_head in {"actor", "actors", "human actors", "main human actors"}:
        return False
    return True


def _preserve_standalone_label(head: str, *, lower_head: str, role: str) -> bool:
    if not _is_concrete_actor_head(head, lower_head=lower_head, role=role):
        return False
    if not role or len(head.split()) > 6:
        return False
    return bool(re.match(r"^[A-Z][a-z]+(?:\s+[a-z][a-z-]+)+$", head))


def _project_specific_composite_head(head: str, *, lower_head: str, project_focus: str) -> str:
    for generic in sorted(_GENERIC_HEADS, key=len, reverse=True):
        if lower_head.startswith((f"{generic} or ", f"{generic} and ")):
            focus = _focus_from_text(project_focus, role="") or _focus_from_text(head, role="")
            return _title_label(f"{focus} {head}" if focus else head)
    return ""


def _drop_generic_actor_alternative(value: str) -> str:
    label = _clean(value).strip(" .")
    if not label:
        return ""
    for separator in (" / ", "/", " or "):
        if separator not in label:
            continue
        parts = [part.strip(" .") for part in label.split(separator) if part.strip(" .")]
        if len(parts) != 2:
            continue
        concrete = [part for part in parts if not _actor_alternative_is_generic(part)]
        if len(concrete) == 1:
            return concrete[0]
    return label


def _actor_alternative_is_generic(value: str) -> bool:
    text = _key(value)
    return bool(text in _GENERIC_ROLE_ONLY or text in _GENERIC_HEADS)


def _first_actor_display_label(values: Sequence[str], *, project_focus: str) -> str:
    for value in values:
        label = actor_display_label(str(value), project_focus=project_focus)
        if label:
            return label
    return ""


def _role_suffix(value: str) -> str:
    words = [word.strip(".,;:()").casefold() for word in _clean(value).replace("/", " ").split()]
    if not words:
        return ""
    two_word = " ".join(words[-2:])
    if len(words) >= 2 and two_word in _ROLE_WORDS:
        return two_word
    if words[-1] in _ROLE_WORDS:
        return "user" if words[-1] in {"individual", "people", "person"} else words[-1]
    return ""


def _generic_person_head(value: str) -> bool:
    words = [word.casefold().strip(".,;:()") for word in _clean(value).split()]
    return bool(words and words[-1] in {"individual", "people", "person", "user"})


def _body_names_control_focus(value: str) -> bool:
    words = {word.casefold().strip(".,;:()") for word in _clean(value).split()}
    return bool(words & {"content", "policy", "privacy", "risk", "safety"})


def _focus_from_actor_body(value: str, *, role: str) -> str:
    text = _strip_parenthetical_qualifiers(value)
    text = re.sub(
        r"^(?:accepting|approving|checking|configuring|coordinating|editing|evaluating|handling|"
        r"following|logging|managing|monitoring|owning|receiving|reviewing|running|sharing|submitting|tracking|using)\s+",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^(?:a|an|the|one)\s+", "", text, flags=re.IGNORECASE).strip(" .")
    return _focus_from_text(text or value, role=role)


def _focus_from_text(value: str, *, role: str) -> str:
    text = re.sub(r"[/]", " ", _strip_parenthetical_qualifiers(value))
    tokens = [token.strip(";:()").rstrip(".") for token in text.split()]
    selected: list[str] = []
    selected_count = 0
    limit = 2 if role in {"user", "operator", "owner", "support"} else 5
    connectors = {"and", "or"}

    def selectable(raw: str) -> bool:
        lower_raw = raw.casefold().strip(",")
        if not raw or lower_raw in connectors:
            return False
        if lower_raw in _FOCUS_STOPWORDS or lower_raw in _ROLE_WORDS:
            return False
        return lower_raw in {"privacy", "safety", "content", "policy", "risk"} or len(raw) >= 4

    for index, token in enumerate(tokens):
        lower = token.casefold().strip(",")
        if lower in connectors:
            next_token = tokens[index + 1] if index + 1 < len(tokens) else ""
            if selected and selectable(next_token):
                selected.append(token)
            continue
        if selectable(token):
            selected.append(token.strip(",") if limit <= 2 else token)
            selected_count += 1
        if selected_count >= limit:
            break
    while selected and selected[-1].casefold() in connectors:
        selected.pop()
    return _title_label(" ".join(selected))


def _title_label(value: str) -> str:
    words: list[str] = []
    for index, word in enumerate(_clean(value).split()):
        stripped = word.strip()
        lower = stripped.casefold().strip(".,;:()")
        if not stripped:
            continue
        if index > 0 and lower in _TITLE_CONNECTORS:
            words.append(lower)
            continue
        if _looks_like_preserved_acronym_token(stripped.strip(".,;:()")):
            words.append(stripped)
            continue
        if lower in {"ai", "api", "crm", "gis", "iot", "llm", "ml", "ui", "ux"}:
            words.append(stripped.upper())
            continue
        words.append(stripped[:1].upper() + stripped[1:])
    while words and words[-1].casefold().strip(".,;:()") in _TITLE_CONNECTORS:
        words.pop()
    return " ".join(words).strip()


def _looks_like_preserved_acronym_token(value: str) -> bool:
    letters = [char for char in value if char.isalpha()]
    if len(letters) < 2 or not all(char.isupper() for char in letters):
        return False
    return any(not char.isalpha() for char in value)


def _key(value: str) -> str:
    text = re.sub(r"[^a-z0-9\s-]+", " ", _clean(value).casefold())
    return re.sub(r"\s+", " ", text).strip()


def _clean(value: object) -> str:
    return clean_markdown_text(value)


__all__ = [
    "accepted_actor_label",
    "actor_display_label",
    "localize_leading_actor_reference",
    "project_specific_actor_row",
]
