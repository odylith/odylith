"""Text casing helpers for first-path action fragments."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_first_path_common import (
    MATERIAL_ACTION_RE,
    clean_first_path_text,
)
from odylith.runtime.domain_intelligence.greenfield_text import lower_plain_title_subject_fragment


def lower_initial_for_fragment(value: str) -> str:
    text = clean_first_path_text(value).strip(" ,.")
    if not text:
        return ""
    match = MATERIAL_ACTION_RE.search(text)
    plain_subject = lower_plain_title_subject_fragment(text, action_offset=match.start() if match else 0)
    if plain_subject != text:
        return plain_subject
    match = re.match(r"(?P<prefix>[^A-Za-z0-9]*)(?P<token>[A-Za-z0-9][A-Za-z0-9_/-]*)", text)
    if not match:
        return text[:1].casefold() + text[1:]
    token = match.group("token")
    letters = [char for char in token if char.isalpha()]
    if len(letters) >= 2 and (all(char.isupper() for char in letters) or any(char.isupper() for char in letters[1:])):
        return text
    index = len(match.group("prefix"))
    return f"{text[:index]}{text[index:index + 1].casefold()}{text[index + 1:]}"
