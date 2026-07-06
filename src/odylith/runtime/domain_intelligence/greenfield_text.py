"""Shared text coercion for greenfield proposal runtime paths."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from odylith.runtime.common.prose_grammar import action_base_verb_pattern
from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common import display_text
from odylith.runtime.domain_intelligence.greenfield_status_modifiers import RESULT_STATUS_MODIFIERS

_LIST_SPLIT_RE = re.compile(r"(?:\r?\n|;)+")
_COMMA_LIST_SPLIT_RE = re.compile(r"(?:\r?\n|;|,)+")
_LIST_BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s*")
_PUNCTUATION_SPACING_RE = re.compile(r"\s+([,.;:?!])")
_CONTROL_ACTION_TARGET_RE = re.compile(
    r"\b(?P<action>control\s+actions?)\s+to\s+(?:the\s+)?(?P<target>[^.;:,]+)",
    re.IGNORECASE,
)
_COVER_ARTICLE_SKIP_WORDS = frozenset(
    {
        "a",
        "all",
        "an",
        "another",
        "any",
        "both",
        "each",
        "either",
        "every",
        "its",
        "no",
        "our",
        "that",
        "the",
        "their",
        "these",
        "this",
        "those",
        "your",
    }
)


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def dedupe_adjacent_words(value: Any) -> str:
    """Collapse adjacent duplicate word tokens in generated prose."""

    text = clean_text(value)
    if not text:
        return ""
    output: list[str] = []
    previous_key = ""
    for token in text.split(" "):
        key = _adjacent_word_key(token)
        if key and key == previous_key:
            _carry_duplicate_terminal_punctuation(output, token)
            continue
        output.append(token)
        previous_key = key
    return clean_text(" ".join(output))


def _adjacent_word_key(token: str) -> str:
    word = str(token or "").strip("`*_~.,;:!?()[]{}\"'")
    if len(word) < 2:
        return ""
    return word.casefold() if any(char.isalnum() for char in word) else ""


def _carry_duplicate_terminal_punctuation(output: list[str], token: str) -> None:
    if not output:
        return
    suffix = str(token or "")[-1:]
    if suffix in ".!?" and output[-1][-1:] not in ".!?":
        output[-1] = f"{output[-1]}{suffix}"


def clean_artifact_text(value: Any, *, split_parentheses: bool = False) -> str:
    text = clean_text(value).replace("`", "")
    if split_parentheses:
        text = text.replace("(", " ").replace(")", " ")
    text = _PUNCTUATION_SPACING_RE.sub(_punctuation_spacing_replacement, text)
    return clean_text(text)


def clean_artifact_sentence(value: Any, *, split_parentheses: bool = False) -> str:
    text = clean_artifact_text(value, split_parentheses=split_parentheses).strip()
    if not text:
        return ""
    text = text[:1].upper() + text[1:]
    return text if text[-1] in ".!?" else f"{text}."


def clean_markdown_text(value: Any) -> str:
    text = display_text.strip_inline_markdown_emphasis_tokens(clean_text(value)).replace("`", "")
    text = _PUNCTUATION_SPACING_RE.sub(_punctuation_spacing_replacement, text)
    return clean_text(text)


def _punctuation_spacing_replacement(match: re.Match[str]) -> str:
    punctuation = match.group(1)
    if punctuation == ".":
        prefix = match.string[: match.start()].rstrip()
        previous = prefix.rsplit(" ", 1)[-1] if prefix else ""
        if previous.startswith("--"):
            return match.group(0)
    return punctuation


def clean_markdown_sentence(value: Any) -> str:
    text = clean_markdown_text(value).strip()
    if text:
        text = text[:1].upper() + text[1:]
    if not text:
        return ""
    return text if text[-1] in ".!?" else f"{text}."


def word_count(value: Any) -> int:
    return len(visible_words(value))


def word_occurrences(value: Any, word: Any) -> int:
    token = clean_text(word)
    if not token:
        return 0
    return len(
        re.findall(
            rf"\b{re.escape(token)}\b",
            clean_text(value),
            re.IGNORECASE,
        )
    )


def normalize_visible_result_language(value: Any) -> str:
    text = clean_text(value)
    text = re.sub(r"\bintaked\b", "received", text, flags=re.IGNORECASE)
    text = _normalize_saved_destination_language(text)
    text = _normalize_possessive_result_lists(text)
    text = normalize_reviewed_result_nouns(text)
    text = _normalize_result_status_item_order(text)
    text = _replace_casefolded_phrase(text, "reasons against", "uses for comparison")
    text = _replace_casefolded_phrase(text, "reason against", "use for comparison")
    text = re.sub(r"\bvisible[- ]result\s+event\b", "visible result", text, flags=re.IGNORECASE)
    text = re.sub(r"\breadout\s+plus\b", "readout and", text, flags=re.IGNORECASE)
    text = re.sub(r"\bagainst\s+(?:the\s+)?target\s+plus\b", "compared with the target and", text, flags=re.IGNORECASE)
    text = re.sub(r"\bagainst\s+target\b", "against the target", text, flags=re.IGNORECASE)
    text = re.sub(r"\bon\s+screen,\s+alongside\b", "on screen with", text, flags=re.IGNORECASE)
    text = re.sub(r"\balongside\b", "with", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmetrics?\s+(?:trended|moved)\s+with\b", "metrics changed with", text, flags=re.IGNORECASE)
    text = _normalize_progress_status_terminal_result(text)
    text = re.sub(
        r"\bthe\s+tracked\s+metrics\s+(?:trended|moved)\s+with\b",
        "the tracked metrics changed with",
        text,
        flags=re.IGNORECASE,
    )
    text = normalize_action_target_language(text)
    return clean_text(text)


def _normalize_result_status_item_order(value: str) -> str:
    original = clean_text(value)
    terminal = original[-1:] if original[-1:] in {".", "!", "?"} else ""
    body = original[:-1] if terminal else original
    parts = _split_commas_outside_quotes(body)
    if len(parts) <= 1:
        normalized = _normalize_result_status_item(parts[0]) if parts else ""
    else:
        normalized = ", ".join(_normalize_result_status_item(part) for part in parts)
    return f"{normalized}{terminal}" if normalized and terminal else normalized


def _split_commas_outside_quotes(value: str) -> list[str]:
    rows: list[str] = []
    current: list[str] = []
    quote: str | None = None
    for char in value:
        if char == '"':
            quote = None if quote == char else char if quote is None else quote
        if char == "," and quote is None:
            rows.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    rows.append("".join(current).strip())
    return [row for row in rows if row]


def _normalize_result_status_item(value: str) -> str:
    text = clean_text(value).strip(" .,;:")
    split = re.split(r"\s+[–—-]\s+", text, maxsplit=1)
    if len(split) == 2:
        head, tail = (part.strip(" .,;:") for part in split)
        normalized_head = _normalize_result_status_item(head)
        if normalized_head != head and _starts_with_result_status_tail(tail):
            return f"{normalized_head}, {tail[:1].casefold()}{tail[1:]}".strip(" .,;:")
    words = text.split()
    if len(words) < 2:
        return text
    connector = ""
    if words[0].casefold() in {"and", "or"}:
        connector = words.pop(0).casefold()
    article = ""
    if words and words[0].casefold() in {"a", "an", "the"}:
        article = words.pop(0).casefold()
    if len(words) < 2:
        return text
    status = words[-1].strip(".,;:").casefold()
    object_words = words[:-1]
    object_keys = [word.strip(".,;:").casefold() for word in object_words]
    if status not in RESULT_STATUS_MODIFIERS:
        return text
    if any(key in {"and", "or"} for key in object_keys):
        return text
    if len(object_words) > 5 or any(key in {"am", "are", "be", "been", "being", "is", "was", "were"} for key in object_keys):
        return text
    if any(re.fullmatch(action_verb_pattern(), key, flags=re.IGNORECASE) for key in object_keys):
        return text
    if not object_words:
        return text
    if article in {"a", "an"}:
        article = "an" if status[:1] in {"a", "e", "i", "o", "u"} else "a"
    prefix = f"{connector} " if connector else ""
    article_text = f"{article} " if article else ""
    if object_words[0].casefold().endswith(("'s", "s'")):
        normalized_object = f"{object_words[0]} {status}"
        if len(object_words) > 1:
            normalized_object = f"{normalized_object} {' '.join(object_words[1:])}"
    else:
        normalized_object = f"{status} {' '.join(object_words)}"
    return f"{prefix}{article_text}{normalized_object}".strip()


def _starts_with_result_status_tail(value: str) -> bool:
    words = clean_text(value).strip(" .,;:").split()
    if not words:
        return False
    first = words[0].strip(".,;:").casefold()
    if first in {"and", "or"} and len(words) > 1:
        first = words[1].strip(".,;:").casefold()
    return first in RESULT_STATUS_MODIFIERS or (len(first) > 4 and first.endswith("ed"))


def normalize_cover_article_language(value: Any) -> str:
    """Insert a missing article after cover/covers in clipped validation copy."""

    text = clean_text(value)
    if not text:
        return ""
    for marker in (" covers ", " cover "):
        repaired = _add_article_after_cover_marker(text, marker)
        if repaired != text:
            return repaired
    for marker in ("covers ", "cover "):
        if text.casefold().startswith(marker):
            return _add_article_after_cover_marker(text, marker)
    return text


def _add_article_after_cover_marker(value: str, marker: str) -> str:
    text = clean_text(value)
    lowered = text.casefold()
    index = lowered.find(marker)
    if index < 0:
        return text
    prefix_end = index + len(marker)
    tail = text[prefix_end:]
    tail_words = tail.split(maxsplit=1)
    first_word = tail_words[0].strip(" ,;:.").casefold() if tail_words else ""
    if first_word and first_word not in _COVER_ARTICLE_SKIP_WORDS:
        return f"{text[:prefix_end]}the {tail}"
    return text


def normalize_reviewed_result_nouns(value: Any) -> str:
    """Remove generic review modifiers from result nouns while preserving grammar."""

    def replace(match: re.Match[str]) -> str:
        modifiers = clean_text(match.group("modifiers")).strip()
        noun = match.group("noun")
        object_text = f"{modifiers} {noun}".strip()
        article = _review_result_article(match.group("article"), object_text)
        return f"{article} {object_text}"

    return re.sub(
        r"\b(?P<article>a|an|the)\s+reviewed\s+"
        r"(?P<modifiers>(?:[a-z][a-z0-9'-]*\s+){0,4})"
        r"(?P<noun>answer|decision|evidence|outcome|packet|plan|record|report|result|summary|view)\b",
        replace,
        clean_text(value),
        flags=re.IGNORECASE,
    )


def _review_result_article(article: str, noun: str) -> str:
    token = str(noun or "").casefold()
    if token == "evidence":
        return "the"
    requested = str(article or "").casefold()
    if requested == "the":
        return "the"
    return "an" if token[:1] in {"a", "e", "i", "o", "u"} else "a"


def _normalize_progress_status_terminal_result(value: str) -> str:
    text = clean_text(value)
    match = re.match(
        r"^(?:display|displays|present|presents|render|renders|show|shows|surface|surfaces)\s+"
        r"(?:the\s+)?(?:progress|status|current\s+state|result\s+status)"
        r"\s*,?\s+and\s+(?P<tail>(?:ends?|finishes?|produces?|reaches?|returns?|shows?)\b.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return text
    return clean_text(
        re.sub(
            r"^(?:ends?|finishes?|produces?|reaches?|returns?|shows?)\s+",
            "",
            match.group("tail").strip(" ."),
            count=1,
            flags=re.IGNORECASE,
        )
    )


def _normalize_saved_destination_language(value: str) -> str:
    text = clean_text(value)
    return re.sub(
        r"\b(?P<object>(?:the\s+|a\s+|an\s+)?[A-Za-z][A-Za-z0-9'/-]*(?:\s+[A-Za-z][A-Za-z0-9'/-]*){0,4})\s+"
        r"to\s+(?P<destination>history|log|ledger|journal|timeline|archive)\s+with\b",
        lambda match: f"{match.group('object')} in {match.group('destination')} with",
        text,
        flags=re.IGNORECASE,
    )


def _normalize_possessive_result_lists(value: str) -> str:
    text = clean_text(value)
    return re.sub(
        r"\b(?P<object>history|record|entry|summary|report|view|timeline|log|ledger)\s+with\s+its\s+",
        lambda match: f"{match.group('object')} with ",
        text,
        flags=re.IGNORECASE,
    )


def normalize_action_target_language(value: Any) -> str:
    return clean_text(_CONTROL_ACTION_TARGET_RE.sub(_control_action_target_text, clean_text(value)))


def _control_action_target_text(match: re.Match[str]) -> str:
    target = clean_text(match.group("target")).strip(" .")
    if not target:
        return match.group(0)
    return f"{match.group('action')} for {target}"


def _replace_casefolded_phrase(value: str, needle: str, replacement: str) -> str:
    text = value
    target = clean_text(needle).casefold()
    if not target:
        return text
    while True:
        index = text.casefold().find(target)
        if index < 0:
            return text
        text = f"{text[:index]}{replacement}{text[index + len(needle):]}"


def normalize_proof_boundary_language(value: Any) -> str:
    text = clean_text(value).strip(" .:")
    if not text:
        return ""
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip()
    ]
    if len(sentences) > 1 and re.search(
        r"\b(?:confirmation-only|confirmed?\s+draft|no\s+product\s+code\s+exists)\b",
        sentences[0],
        flags=re.IGNORECASE,
    ):
        text = " ".join(sentences[1:]).strip(" .:")
    replacements = (
        (r"^what\s+would\s+count\s+as\s+evidence[^:]*:\s*", ""),
        (r"^(?:accepted\s+first\s+path|visible\s+outcome)\s+proof\s*:\s*", ""),
        (r"^done\s+means\s*:?\s*", ""),
        (r"^the\s+first\s+proof\s+is\s+", ""),
        (r"^(?:the\s+)?first\s+version\s+is\s+proven\s+when\s+", ""),
        (r"^(?:release\s+[A-Za-z0-9_.-]+\s+)?(?:is\s+)?proven\s+when\s+", ""),
        (r"^(?:release\s+[A-Za-z0-9_.-]+\s+|the\s+release\s+)?(?:is\s+)?trusted\s+only\s+when\s+", ""),
        (r"^(?:the\s+)?first\s+release\s+works\s+when\s+", ""),
        (r"^release\s+[A-Za-z0-9_.-]+\s+succeeds\s+when\s+", ""),
        (r"^the\s+release\s+succeeds\s+when\s+", ""),
        (r"^(?:the\s+)?accepted\s+path\s+can\s+be\s+replayed\s+from\s+", "replay "),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        text = clean_text(text).strip(" .:")
    text = _normalize_first_path_complete_proof(text)
    text = re.split(r"\bwhat\s+must\s+not\s+be\s+claimed\s+yet\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
    return clean_text(text).strip(" .:")


def normalize_confirmed_proof_boundary_sentence(value: Any) -> str:
    text = clean_text(value).strip(" .:")
    if not text:
        return ""
    match = re.match(
        r"^(?P<prefix>(?:release\s+[A-Za-z0-9_.-]+\s+|the\s+release\s+)?(?:is\s+)?(?:proven|trusted|succeeds|works)\s+when)\s+"
        r"(?P<body>.+)$",
        text,
        flags=re.I,
    )
    if not match:
        return _normalize_first_path_complete_proof(text)
    body = _normalize_first_path_complete_proof(match.group("body"))
    return f"{match.group('prefix')} {body}".strip(" .:")


def _normalize_first_path_complete_proof(value: str) -> str:
    text = clean_text(value).strip(" .:")
    lowered = text.casefold()
    prefixes = (
        "this first path is complete:",
        "the first path is complete:",
        "the accepted first path is complete:",
    )
    prefix = next((candidate for candidate in prefixes if lowered.startswith(candidate)), "")
    if not prefix:
        return text
    tail = text[len(prefix) :].strip(" .:")
    if not tail:
        return "the accepted first path is complete"
    parts = [part.strip(" .:") for part in re.split(r"(?<=[.!?])\s+", tail) if part.strip(" .:")]
    if not parts:
        return "the accepted first path is complete"
    first = parts[0]
    match = re.match(r"(?P<actor>[A-Za-z0-9][A-Za-z0-9 /&()'-]{1,120}?)\s+who\s+(?P<action>.+)$", first, flags=re.I)
    if match:
        actor = _lower_initial_prose(match.group("actor"))
        actions = [base_action_clause(match.group("action")), *(base_action_clause(part) for part in parts[1:])]
        action_text = _join_proof_action_parts(actions)
        return f"{actor} can {action_text}" if action_text else f"{actor} can complete the accepted first path"
    action_text = _join_proof_action_parts(base_action_clause(part) for part in parts)
    return f"the accepted first path is complete when {action_text}" if action_text else "the accepted first path is complete"


def _join_proof_action_parts(values: Iterable[str]) -> str:
    parts = [clean_text(value).strip(" .:") for value in values if clean_text(value).strip(" .:")]
    parts = list(unique_text(parts))
    if len(parts) <= 1:
        return parts[0] if parts else ""
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return f"{', '.join(parts[:-1])}, and {parts[-1]}"


def _lower_initial_prose(value: str) -> str:
    text = clean_text(value).strip(" .:")
    if not text:
        return ""
    first_word = text.split(maxsplit=1)[0]
    if first_word.isupper() or any(char in first_word for char in ("/", "&")):
        return text
    return f"{text[:1].lower()}{text[1:]}"


def clip_text_at_word_boundary(
    value: Any,
    *,
    limit: int,
    dangling_words: Iterable[str] = (),
    strip_edges: str = "",
    rstrip_chars: str = " ,;:-",
) -> str:
    text = clean_text(value)
    if strip_edges:
        text = text.strip(strip_edges)
    if len(text) <= limit:
        return text
    clipped = text[: max(0, limit)].rstrip(rstrip_chars)
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip(rstrip_chars)
    return _strip_unbalanced_quote_tail(
        strip_dangling_word_tail(clipped, dangling_words=dangling_words, rstrip_chars=rstrip_chars)
    )


def strip_dangling_word_tail(
    value: Any,
    *,
    dangling_words: Iterable[str],
    rstrip_chars: str = " ,;:.",
) -> str:
    words = clean_text(value).rstrip(rstrip_chars).split()
    dangling = {clean_text(word).casefold().strip(".,;:") for word in dangling_words}
    dangling.discard("")
    while words and words[-1].casefold().strip(".,;:") in dangling:
        words.pop()
    return " ".join(words).rstrip(rstrip_chars)


def _strip_unbalanced_quote_tail(value: Any) -> str:
    text = clean_text(value).rstrip(" ,;:.")
    if text.count('"') % 2:
        return text.rsplit('"', 1)[0].rstrip(" ,;:.")
    if re.search(r"(?:^|\s)'[A-Za-z][^']*$", text):
        return text.rsplit("'", 1)[0].rstrip(" ,;:.")
    return text


_PLAIN_TITLE_CONNECTORS = frozenset({"and", "for", "in", "of", "on", "or", "to", "with"})


def lower_plain_title_subject_fragment(value: Any, *, action_offset: int) -> str:
    """Lowercase a plain title-cased subject when it is embedded before an action."""

    text = clean_markdown_text(value).strip(" .")
    if action_offset <= 0 or action_offset > len(text):
        return _lower_plain_title_phrase(text)
    action_tail = text[action_offset:].lstrip()
    if not re.match(
        rf"^(?:{action_verb_pattern(include_base=False)})(?![A-Za-z0-9_-])",
        action_tail,
        flags=re.IGNORECASE,
    ):
        return _lower_plain_title_phrase(text)
    subject = text[:action_offset].strip(" ,")
    if len(subject.split()) < 2 or not plain_title_phrase(subject):
        return text
    return f"{subject.casefold()} {text[action_offset:].lstrip()}"


def _lower_plain_title_phrase(value: str) -> str:
    text = clean_markdown_text(value).strip(" .")
    if not plain_title_phrase(text):
        return text
    return text.casefold()


def plain_title_phrase(value: Any) -> bool:
    words = [word.strip(".,;:()[]{}") for word in clean_markdown_text(value).split() if word.strip(".,;:()[]{}")]
    if len(words) < 2:
        return False
    if any(any(char.isdigit() for char in word) or (word.isupper() and len(word) > 1) for word in words):
        return False
    return all(word[:1].isupper() or word.casefold() in _PLAIN_TITLE_CONNECTORS for word in words)


def imperative_action_with_copula_words(words: Sequence[str], index: int) -> bool:
    """Return true when an imperative action owns a later readiness copula."""

    if index < 2:
        return False
    verb = words[index].strip(".,;:").casefold()
    if verb not in {"is", "are", "was", "were"}:
        return False
    head = words[0].strip(".,;:").casefold()
    if not re.fullmatch(action_base_verb_pattern(), head, flags=re.IGNORECASE):
        return False
    second = words[1].strip(".,;:").casefold()
    return second in {"a", "an", "the", "this", "that", "one", "their", "its", "our", "your"}


def visible_words(value: Any) -> tuple[str, ...]:
    return tuple(re.findall(r"[A-Za-z0-9]+", clean_text(value)))


def progression_marker_count(
    value: Any,
    *,
    connectors: Iterable[str] = (),
    punctuation: str = "",
) -> int:
    text = clean_text(value)
    connector_set: set[str] = set()
    for connector in connectors:
        cleaned = clean_text(connector).casefold()
        if cleaned:
            connector_set.add(cleaned)
    count = sum(1 for word in visible_words(text) if word.casefold() in connector_set)
    return count + sum(text.count(mark) for mark in punctuation)


def normalize_domain_token(value: Any, *, minimum: int = 4, stopwords: Iterable[str] = ()) -> str:
    """Normalize one extracted product term without corrupting common nouns.

    Greenfield renderers use these tokens to derive artifact nouns from the
    accepted intent. The normalization must stay conservative because a bad
    stem leaks directly into human-visible governance text.
    """

    token = str(value or "").strip("-_").casefold()
    if len(token) < minimum or token.isdigit() or any(char.isdigit() for char in token):
        return ""
    stop = {str(item or "").casefold() for item in stopwords}
    if token in stop:
        return ""
    if token.endswith("ies") and len(token) > 5:
        token = f"{token[:-3]}y"
    elif token == "statuses":
        token = "status"
    elif token.endswith("izes") and len(token) > 6:
        token = token[:-1]
    elif token.endswith(("ches", "shes", "xes", "zes", "sses")) and len(token) > 5:
        token = token[:-2]
    elif token.endswith("s") and len(token) > 4 and not token.endswith(("ss", "us", "is")):
        token = token[:-1]
    return token if len(token) >= minimum and token not in stop else ""


def text_values(
    value: Any,
    *,
    split_scalar: bool = False,
    split_commas: bool = False,
    strip_bullets: bool = False,
) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        values: list[str] = []
        for nested in value.values():
            values.extend(
                text_values(
                    nested,
                    split_scalar=split_scalar,
                    split_commas=split_commas,
                    strip_bullets=strip_bullets,
                )
            )
        return unique_text(values)
    if isinstance(value, (list, tuple, set)):
        values = []
        for nested in value:
            values.extend(
                text_values(
                    nested,
                    split_scalar=split_scalar,
                    split_commas=split_commas,
                    strip_bullets=strip_bullets,
                )
            )
        return unique_text(values)
    if not split_scalar:
        token = clean_text(value)
        return (token,) if token else ()
    splitter = _COMMA_LIST_SPLIT_RE if split_commas else _LIST_SPLIT_RE
    values = []
    for part in splitter.split(str(value or "").strip()):
        raw = _LIST_BULLET_RE.sub("", part) if strip_bullets else part
        token = clean_text(raw)
        if token:
            values.append(token)
    return unique_text(values)


def unique_text(values: Iterable[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        for token in text_values(value):
            key = token.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(token)
    return tuple(result)


def collect_text_values(
    row: Mapping[str, Any],
    fields: Iterable[str],
    *,
    split_scalar: bool = False,
    split_commas: bool = False,
) -> tuple[str, ...]:
    values: list[str] = []
    for field in fields:
        values.extend(text_values(row.get(field), split_scalar=split_scalar, split_commas=split_commas))
    return tuple(values)


def delimited_text_values(value: Any) -> tuple[str, ...]:
    return text_values(value, split_scalar=True, split_commas=True, strip_bullets=True)


def collect_delimited_text_values(row: Mapping[str, Any], fields: Iterable[str]) -> tuple[str, ...]:
    values: list[str] = []
    for field in fields:
        values.extend(delimited_text_values(row.get(field)))
    return tuple(values)


def join_sentence_text(value: Any) -> str:
    result = ""
    for token in text_values(value):
        if not result:
            result = token
            continue
        separator = " " if result[-1:] in {".", "!", "?"} else "; "
        result = f"{result}{separator}{token}"
    return result.strip()


def normalize_text_list(value: Any, *, split_commas: bool = False) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        values: list[str] = []
        for nested in value:
            if isinstance(nested, (list, tuple, set, Mapping)):
                values.extend(normalize_text_list(nested, split_commas=split_commas))
                continue
            token = clean_text(_LIST_BULLET_RE.sub("", str(nested or "")))
            if token:
                values.append(token)
        return list(unique_text(values))
    return list(
        text_values(
            value,
            split_scalar=True,
            split_commas=split_commas,
            strip_bullets=True,
        )
    )
