"""Actor-label normalization for confirmed greenfield product intent."""

from __future__ import annotations

import re


_QUALIFIER_RE = re.compile(
    r"^(?:primary|optional|secondary|main|target|first|initial|prospective|potential)\s+",
    re.IGNORECASE,
)

_DESCRIPTION_MARKERS = (
    " responsible for ",
    " accountable for ",
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
    " receiving ",
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
    "buyer",
    "chair",
    "client",
    "coach",
    "consultant",
    "coordinator",
    "customer",
    "editor",
    "engineer",
    "evaluator",
    "inspector",
    "lead",
    "manager",
    "operator",
    "owner",
    "participant",
    "planner",
    "preparer",
    "recipient",
    "requester",
    "researcher",
    "resident",
    "reviewer",
    "safety reviewer",
    "advisor",
    "specialist",
    "submitter",
    "support",
    "trainer",
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
    "review",
    "reviewing",
    "service",
    "state",
    "system",
    "the",
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


def accepted_actor_label(value: str, *, project_focus: str = "") -> str:
    """Return a project-specific actor label from accepted actor prose."""

    text = _clean(value).strip(" .")
    if not text:
        return ""
    head, body = _split_actor_row(text)
    explicit_body = bool(body)
    original_head = _strip_qualifiers(head).strip(" .")
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
    head = _strip_qualifiers(head).strip(" .")
    if not head:
        return ""

    lower_head = _key(head)
    role = _role_suffix(head)
    if not explicit_body and not marker_body_used and _preserve_standalone_label(head, lower_head=lower_head, role=role):
        return head
    if explicit_body and _is_concrete_actor_head(head, lower_head=lower_head, role=role):
        return head
    composite_label = _project_specific_composite_head(head, lower_head=lower_head, project_focus=project_focus)
    if composite_label:
        return composite_label
    needs_focus = _head_needs_focus(lower_head, role=role) or (
        marker_body_used and lower_head == role and role in _ROLE_WORDS
    )
    if needs_focus:
        if marker_body_used:
            focus = _focus_from_text(body or text, role=role) or _focus_from_text(project_focus, role=role)
        else:
            focus = _focus_from_text(project_focus, role=role) or _focus_from_text(body or text, role=role)
        if focus and role:
            return _title_label(f"{focus} {role}")
        if focus:
            return _title_label(focus)
        return ""
    if original_head and marker_head and lower_head != role and not marker_body_used:
        return _title_label(original_head)
    return _title_label(head)


def project_specific_actor_row(row: str, *, project_focus: str) -> str:
    """Rewrite one actor row so the visible label is not a stable-role placeholder."""

    text = _clean(row).strip(" .")
    if not text:
        return ""
    _head, body = _split_actor_row(text)
    label = accepted_actor_label(text, project_focus=project_focus)
    if not label:
        return text
    return f"{label}: {body}" if body else label


def _split_actor_row(value: str) -> tuple[str, str]:
    for separator in (" — ", " – ", " - ", ":"):
        head, sep, body = value.partition(separator)
        if sep and head.strip():
            return head.strip(" ."), body.strip(" .")
    return value, ""


def _split_description_marker(value: str) -> tuple[str, str]:
    lowered = value.casefold()
    for marker in _DESCRIPTION_MARKERS:
        head, sep, tail = lowered.partition(marker)
        if sep and head.strip() and tail.strip():
            return value[: len(head)].strip(" ."), value[len(head) + len(marker) :].strip(" .")
    return "", ""


def _strip_qualifiers(value: str) -> str:
    text = _clean(value)
    while True:
        replacement = _QUALIFIER_RE.sub("", text).strip()
        if replacement == text:
            return replacement
        text = replacement


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


def _role_suffix(value: str) -> str:
    words = [word.strip(".,;:()").casefold() for word in _clean(value).replace("/", " ").split()]
    if not words:
        return ""
    two_word = " ".join(words[-2:])
    if two_word in _ROLE_WORDS:
        return two_word
    if words[-1] in _ROLE_WORDS:
        return words[-1]
    return ""


def _focus_from_text(value: str, *, role: str) -> str:
    text = re.sub(r"[/]", " ", _clean(value))
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
        if lower in {"ai", "api", "crm", "gis", "iot", "llm", "ml", "ui", "ux"}:
            words.append(stripped.upper())
            continue
        words.append(stripped[:1].upper() + stripped[1:])
    return " ".join(words).strip()


def _key(value: str) -> str:
    text = re.sub(r"[^a-z0-9\s-]+", " ", _clean(value).casefold())
    return re.sub(r"\s+", " ", text).strip()


def _clean(value: object) -> str:
    text = str(value or "").replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


__all__ = ["accepted_actor_label", "project_specific_actor_row"]
