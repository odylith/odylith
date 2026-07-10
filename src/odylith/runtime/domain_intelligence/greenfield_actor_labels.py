"""Actor-label normalization for confirmed greenfield product intent."""

from __future__ import annotations

from collections.abc import Sequence
import re

from odylith.runtime.common.prose_grammar import looks_like_base_action_token
from odylith.runtime.common.prose_grammar import looks_like_finite_action_token
from odylith.runtime.domain_intelligence.greenfield_actor_terms import generic_actor_label_prefix
from odylith.runtime.domain_intelligence.greenfield_actor_terms import looks_actor_term
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
_COLLECTIVE_ACTOR_WORDS = {"crew", "family", "group", "staff", "team"}
_BODY_FOCUS_ROLE_ONLY = {"admin", "administrator", "author", "coordinator", "reviewer"}

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
_MODAL_ACTION_BOUNDARIES = frozenset({"can", "could", "may", "might", "must", "shall", "should", "will", "would"})


def accepted_actor_label(value: str, *, project_focus: str = "") -> str:
    """Return a project-specific actor label from accepted actor prose."""

    text = _clean(value).strip(" .")
    if not text:
        return ""
    head, body = _split_actor_row(text)
    if body and (repaired := _repaired_repeated_action_label(head, body, project_focus=project_focus)):
        return repaired
    explicit_body = bool(body)
    original_head = _strip_modal_actor_tail(_strip_qualifiers(head).strip(" ."))
    original_role = _role_suffix(original_head)
    original_lower_head = _key(original_head)
    if explicit_body and _is_concrete_actor_head(
        original_head,
        lower_head=original_lower_head,
        role=original_role,
    ) and not _role_only_body_focus(original_lower_head, original_role):
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
    if explicit_body and _is_concrete_actor_head(head, lower_head=lower_head, role=role) and not _role_only_body_focus(lower_head, role):
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
    body_focus_role = bool(body) and _role_body_prefers_body_focus(role, body)
    needs_focus = _head_needs_focus(lower_head, role=role) or (
        marker_body_used and lower_head == role and role in _GENERIC_ROLE_ONLY
    ) or (
        marker_body_used and lower_head == role and role in {"coordinator"}
    ) or (lower_head == role and body_focus_role)
    if lower_head == role and body_focus_role:
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
    sentence_context: bool = False,
) -> str:
    """Replace a generic leading actor reference with an accepted actor label."""

    text = _clean(value).strip()
    prefix = generic_actor_label_prefix(text)
    if not prefix:
        if sentence_context:
            existing = _first_actor_display_label(actor_rows, project_focus=project_focus)
            if existing and text.startswith(existing):
                return f"{_sentence_actor_reference(existing)}{text[len(existing):]}"
        return text
    replacement = _first_actor_display_label(actor_rows, project_focus=project_focus) or fallback
    if sentence_context:
        replacement = _sentence_actor_reference(replacement)
    return f"{replacement}{text[len(prefix):]}"


def _sentence_actor_reference(value: str) -> str:
    words = _clean(value).strip(" .").split()
    if not words:
        return ""
    lowered = [word if _preserve_actor_token_case(word) else word.casefold() for word in words]
    lowered[0] = lowered[0][:1].upper() + lowered[0][1:]
    return " ".join(lowered)


def _preserve_actor_token_case(value: str) -> bool:
    letters = [char for char in str(value or "") if char.isalpha()]
    return len(letters) >= 2 and all(char.isupper() for char in letters)


def project_specific_actor_row(row: str, *, project_focus: str) -> str:
    """Rewrite one actor row so the visible label is not a stable-role placeholder."""

    text = _clean(row).strip(" .")
    if not text:
        return ""
    head, body = _split_actor_row(text)
    label = actor_display_label(text, project_focus=project_focus)
    if not label:
        return text
    label = _repaired_repeated_action_label(label, body, project_focus=project_focus) or label
    label = _repaired_repeated_action_label(head, body, project_focus=project_focus) or label
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
    relative_head, relative_tail = _split_relative_actor_marker(value)
    if relative_head:
        return relative_head, relative_tail
    action_head, action_tail = _split_actor_action_tail(value)
    if action_head:
        return action_head, action_tail
    marker_head, marker_tail = _split_description_marker(value)
    if marker_head:
        marker = _description_marker_between(value, marker_head)
        body = (
            f"{marker} {marker_tail}".strip()
            if marker.endswith("ing") or marker.endswith(" to")
            else marker_tail
        )
        return _title_label(marker_head), body
    return value, ""


def _repaired_repeated_action_label(label: str, body: str, *, project_focus: str) -> str:
    """Return a role label when an action was accidentally absorbed into it."""

    label_words = _clean(label).split()
    body_words = _clean(body).split()
    if len(label_words) < 2 or not body_words:
        return ""
    label_tail = _word_key(label_words[-1])
    body_head = _word_key(body_words[0])
    if not label_tail or label_tail != body_head:
        return ""
    role_prefix = _role_prefix(label_words[:-1])
    if not role_prefix:
        return ""
    role = _role_suffix(role_prefix)
    lower_prefix = _key(role_prefix)
    if _is_concrete_actor_head(role_prefix, lower_head=lower_prefix, role=role) and not _role_only_body_focus(
        lower_prefix,
        role,
    ):
        return _title_label(role_prefix)
    focus = _focus_from_actor_body(body, role=role) if _role_body_prefers_body_focus(role, body) else ""
    focus = focus or _focus_from_text(project_focus, role=role) or _focus_from_actor_body(body, role=role)
    if focus and role:
        return _title_label(f"{focus} {role}")
    return _title_label(role_prefix)


def _role_prefix(words: Sequence[str]) -> str:
    for end in range(len(words), 0, -1):
        candidate = _clean(" ".join(words[:end])).strip(" .")
        if _role_suffix(candidate):
            return candidate
    return ""


def _word_key(value: str) -> str:
    return re.sub(r"[^a-z0-9'-]+", "", str(value or "").casefold())


def _split_relative_actor_marker(value: str) -> tuple[str, str]:
    text = _clean(value).strip(" .")
    lowered = text.casefold()
    for marker in (" who ", " that "):
        index = lowered.find(marker)
        if index <= 0:
            continue
        head = text[:index].strip(" .")
        tail = text[index + len(marker) :].strip(" .")
        if not head or not tail:
            continue
        first = _first_body_token(tail)
        if marker.strip() == "that" and not (
            looks_like_finite_action_token(first)
            or looks_like_base_action_token(first)
            or first.endswith("ing")
        ):
            continue
        return _title_label(_strip_actor_head_articles(head)), tail
    return "", ""


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


def _description_marker_between(value: str, head: str) -> str:
    lowered = value.casefold()
    head_length = len(head.strip())
    matches = sorted(
        marker.strip()
        for marker in _DESCRIPTION_MARKERS
        if marker.strip() and lowered.startswith(f"{head.casefold().strip()}{marker}")
    )
    if matches:
        return matches[0]
    tail = lowered[head_length:].strip()
    first = tail.split(" ", 1)[0].strip(".,;:")
    return first if first.endswith("ing") else ""


def _split_actor_action_tail(value: str) -> tuple[str, str]:
    """Split role labels such as "coordinator reviews..." into label/body."""

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
        head_has_role_signal = _actor_head_has_role_signal(head_candidate)
        gerund_boundary = token in {
            "acknowledging",
            "asking",
            "assigning",
            "checking",
            "classifying",
            "configuring",
            "coordinating",
            "creating",
            "deciding",
            "drafting",
            "entering",
            "evaluating",
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
        } or (token.endswith("ing") and head_has_role_signal)
        finite_action_boundary = looks_like_finite_action_token(token)
        base_action_boundary = looks_like_base_action_token(token)
        modal_action_boundary = token in _MODAL_ACTION_BOUNDARIES and index + 1 < len(words)
        clause_action_boundary = finite_action_boundary or base_action_boundary or modal_action_boundary
        if not (gerund_boundary or clause_action_boundary):
            continue
        head = head_candidate
        head = re.sub(r"^(?:a|an|the)\s+", "", head, flags=re.IGNORECASE).strip(" .")
        tail = " ".join(words[index:]).strip(" .")
        role = _role_suffix(head)
        if not role and head_has_role_signal:
            role = "user"
        subject_head = bool(role) or (
            clause_action_boundary
            and _looks_like_finite_actor_subject(head, allow_singular_compound=finite_action_boundary)
        )
        if subject_head and 1 <= len(head.split()) <= 4 and tail and (gerund_boundary or len(tail.split()) >= 2):
            return _title_label(head), tail
    return "", ""


def _actor_head_has_role_signal(value: str) -> bool:
    words = [word.casefold().strip(".,;:()") for word in _clean(value).replace("/", " ").split()]
    if not words:
        return False
    if _role_suffix(value) or _generic_person_head(value):
        return True
    return looks_actor_term(words[-1])


def _looks_like_finite_actor_subject(value: str, *, allow_singular_compound: bool = False) -> bool:
    words = [word.casefold().strip(".,;:()") for word in _clean(value).split()]
    if not 1 <= len(words) <= 4:
        return False
    if words[-1] in _TITLE_CONNECTORS or words[-1] in {"that", "which", "who"}:
        return False
    content = [word for word in words if word and word not in _TITLE_CONNECTORS]
    if not content:
        return False
    if content[0] in {"it", "that", "there", "this", "what", "which"}:
        return False
    if (
        len(content) == 1
        and content[0] not in _COLLECTIVE_ACTOR_WORDS
        and content[0] not in _ROLE_WORDS
        and not content[0].endswith("s")
    ):
        return False
    tail = content[-1]
    if tail.endswith("ing"):
        return False
    if (
        len(content) > 1
        and tail not in _COLLECTIVE_ACTOR_WORDS
        and tail not in _ROLE_WORDS
        and not tail.endswith("s")
        and not allow_singular_compound
    ):
        return False
    return any(word not in _FOCUS_STOPWORDS for word in content)


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
    if len(words) < 2 or words[-1].casefold().strip(".,;:") not in _MODAL_ACTION_BOUNDARIES:
        return text
    head = " ".join(words[:-1]).strip(" .")
    return head if _role_suffix(head) else text


def _head_needs_focus(lower_head: str, *, role: str) -> bool:
    if lower_head in _GENERIC_HEADS:
        return True
    if lower_head.startswith(("product ", "project ", "domain ", "workflow ")) and role in _ROLE_WORDS:
        return True
    return lower_head == role and role in _GENERIC_ROLE_ONLY


def _role_only_body_focus(lower_head: str, role: str) -> bool:
    return bool(role and lower_head == role and role in _BODY_FOCUS_ROLE_ONLY)


def _role_body_prefers_body_focus(role: str, body: str) -> bool:
    if not _role_only_body_focus(role, role):
        return False
    first = _first_body_token(body)
    if not first:
        return False
    if first.endswith("ing"):
        return True
    return role == "reviewer" and (
        looks_like_finite_action_token(first) or looks_like_base_action_token(first)
    )


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
    first = _first_body_token(text)
    finite_action_body = looks_like_finite_action_token(first) or looks_like_base_action_token(first)
    if finite_action_body:
        text = " ".join(text.split()[1:]).strip(" .")
        text = _before_coordinated_action(text)
    text = re.sub(
        r"^(?:accepting|approving|checking|configuring|coordinating|editing|evaluating|handling|"
        r"following|logging|managing|monitoring|owning|receiving|reviewing|running|sharing|submitting|tracking|using)\s+",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^(?:a|an|the|one)\s+", "", text, flags=re.IGNORECASE).strip(" .")
    if re.match(r"^(?:if|that|whether|who|which)\b", text, flags=re.IGNORECASE):
        return ""
    if finite_action_body:
        text = re.split(r",|\s+\band\b\s+", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .")
    return _focus_from_text(text or value, role=role)


def _before_coordinated_action(value: str) -> str:
    text = _clean(value).strip(" .")
    for match in re.finditer(r"\s+(?:and|or)\s+(?P<word>[A-Za-z][A-Za-z'-]*)\b", text, flags=re.IGNORECASE):
        word = match.group("word")
        if looks_like_finite_action_token(word) or looks_like_base_action_token(word):
            return text[: match.start()].strip(" ,")
    return text


def _first_body_token(value: str) -> str:
    match = re.search(r"[A-Za-z][A-Za-z'-]*", _clean(value))
    return match.group(0).casefold() if match else ""


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
