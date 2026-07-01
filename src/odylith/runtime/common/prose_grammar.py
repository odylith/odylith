"""Small domain-neutral grammar helpers for generated product prose.

These helpers only handle the narrow verb-shape cases Odylith emits while
turning accepted product intent into governance records. They intentionally do
not classify domains or infer project meaning.
"""

from __future__ import annotations

import re


_INFINITIVE_TO_FINITE = {
    "accept": "accepts",
    "acknowledge": "acknowledges",
    "add": "adds",
    "advance": "advances",
    "adjust": "adjusts",
    "allow": "allows",
    "allocate": "allocates",
    "answer": "answers",
    "apply": "applies",
    "approve": "approves",
    "assemble": "assembles",
    "ask": "asks",
    "attach": "attaches",
    "attest": "attests",
    "assign": "assigns",
    "bind": "binds",
    "block": "blocks",
    "book": "books",
    "bring": "brings",
    "build": "builds",
    "calculate": "calculates",
    "capture": "captures",
    "catch": "catches",
    "check": "checks",
    "choose": "chooses",
    "classify": "classifies",
    "clear": "clears",
    "click": "clicks",
    "clean": "cleans",
    "close": "closes",
    "cluster": "clusters",
    "collect": "collects",
    "compare": "compares",
    "compute": "computes",
    "complete": "completes",
    "confirm": "confirms",
    "connect": "connects",
    "contain": "contains",
    "control": "controls",
    "convert": "converts",
    "coordinate": "coordinates",
    "correct": "corrects",
    "create": "creates",
    "decide": "decides",
    "define": "defines",
    "delete": "deletes",
    "derive": "derives",
    "describe": "describes",
    "detect": "detects",
    "deliver": "delivers",
    "dismiss": "dismisses",
    "display": "displays",
    "dispatch": "dispatches",
    "drill": "drills",
    "draft": "drafts",
    "drive": "drives",
    "edit": "edits",
    "emit": "emits",
    "enforce": "enforces",
    "end": "ends",
    "enter": "enters",
    "estimate": "estimates",
    "evaluate": "evaluates",
    "exchange": "exchanges",
    "expose": "exposes",
    "explain": "explains",
    "export": "exports",
    "fetch": "fetches",
    "filter": "filters",
    "flag": "flags",
    "forecast": "forecasts",
    "finalize": "finalizes",
    "find": "finds",
    "finish": "finishes",
    "follow": "follows",
    "gather": "gathers",
    "get": "gets",
    "give": "gives",
    "grant": "grants",
    "group": "groups",
    "guide": "guides",
    "handle": "handles",
    "highlight": "highlights",
    "hold": "holds",
    "identify": "identifies",
    "import": "imports",
    "include": "includes",
    "ingest": "ingests",
    "inspect": "inspects",
    "intake": "intakes",
    "issue": "issues",
    "keep": "keeps",
    "launch": "launches",
    "let": "lets",
    "link": "links",
    "load": "loads",
    "log": "logs",
    "manage": "manages",
    "maintain": "maintains",
    "map": "maps",
    "mark": "marks",
    "make": "makes",
    "monitor": "monitors",
    "normalize": "normalizes",
    "notify": "notifies",
    "open": "opens",
    "organize": "organizes",
    "optimize": "optimizes",
    "own": "owns",
    "pay": "pays",
    "perform": "performs",
    "place": "places",
    "prepare": "prepares",
    "predict": "predicts",
    "present": "presents",
    "progress": "progresses",
    "preserve": "preserves",
    "prevent": "prevents",
    "persist": "persists",
    "pick": "picks",
    "play": "plays",
    "prompt": "prompts",
    "pull": "pulls",
    "push": "pushes",
    "produce": "produces",
    "prove": "proves",
    "propose": "proposes",
    "provide": "provides",
    "publish": "publishes",
    "qualify": "qualifies",
    "quantify": "quantifies",
    "rank": "ranks",
    "rate": "rates",
    "read": "reads",
    "reach": "reaches",
    "receive": "receives",
    "recommend": "recommends",
    "record": "records",
    "reconcile": "reconciles",
    "recompute": "recomputes",
    "refresh": "refreshes",
    "register": "registers",
    "reject": "rejects",
    "remove": "removes",
    "report": "reports",
    "request": "requests",
    "repair": "repairs",
    "render": "renders",
    "resolve": "resolves",
    "return": "returns",
    "review": "reviews",
    "route": "routes",
    "run": "runs",
    "schedule": "schedules",
    "score": "scores",
    "screen": "screens",
    "serve": "serves",
    "show": "shows",
    "save": "saves",
    "see": "sees",
    "select": "selects",
    "send": "sends",
    "separate": "separates",
    "set": "sets",
    "share": "shares",
    "split": "splits",
    "start": "starts",
    "store": "stores",
    "stop": "stops",
    "submit": "submits",
    "suggest": "suggests",
    "supply": "supplies",
    "support": "supports",
    "surface": "surfaces",
    "sync": "syncs",
    "tap": "taps",
    "track": "tracks",
    "transform": "transforms",
    "triage": "triages",
    "turn": "turns",
    "understand": "understands",
    "update": "updates",
    "upload": "uploads",
    "use": "uses",
    "view": "views",
    "visit": "visits",
    "validate": "validates",
    "verify": "verifies",
    "watch": "watches",
    "write": "writes",
}

_FINITE_ACTION_VERBS = set(_INFINITIVE_TO_FINITE.values()) | {
    "does",
    "has",
    "is",
}
_FINITE_TO_BASE = {finite: base for base, finite in _INFINITIVE_TO_FINITE.items()}
_FINITE_TO_BASE.update(
    {
        "does": "do",
        "has": "have",
        "is": "be",
    }
)
_FINITE_ACTION_SUFFIXES = (
    "ates",
    "ifies",
    "ises",
    "izes",
    "ves",
)
_FINITE_ACTION_SUFFIX_FALSE_POSITIVES = frozenset(
    {
        "alternatives",
        "archives",
        "incentives",
        "initiatives",
        "narratives",
        "objectives",
        "perspectives",
        "representatives",
    }
)
_MODAL_BASE_FORM_MARKERS = frozenset({"can", "could", "may", "might", "must", "shall", "should", "will", "would"})
_MODAL_COORDINATORS = frozenset({"and", "or"})
_MODAL_COORDINATED_PLURAL_OBJECT_TERMS = frozenset(
    {"blocks", "checks", "controls", "moves", "records", "requests", "runs", "signals", "updates"}
)
_MODAL_COORDINATED_OBJECT_BOUNDARIES = frozenset(
    {"", "after", "and", "because", "before", "for", "from", "if", "into", "or", "then", "through", "to", "until", "when", "where", "which", "while", "with", "without"}
)
_GERUND_NO_DOUBLE_FINAL_CONSONANT = frozenset(
    {
        "answer",
        "deliver",
        "edit",
        "enter",
        "filter",
        "gather",
        "monitor",
        "open",
        "visit",
    }
)
DEFAULT_DANGLING_TAIL_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "before",
        "by",
        "for",
        "from",
        "in",
        "into",
        "of",
        "or",
        "so",
        "the",
        "to",
        "until",
        "with",
    }
)


def strip_dangling_word_tail(
    value: str,
    *,
    dangling_words: set[str] | frozenset[str] | tuple[str, ...] | list[str],
    rstrip_chars: str = " ,;:.",
) -> str:
    """Trim incomplete connector tails after word-boundary clipping."""

    words = str(value or "").rstrip(rstrip_chars).split()
    dangling = {str(word or "").casefold().strip(".,;:") for word in dangling_words}
    dangling.discard("")
    while words and words[-1].casefold().strip(".,;:") in dangling:
        words.pop()
    return " ".join(words).rstrip(rstrip_chars)


def looks_like_finite_action(value: str) -> bool:
    """Return true when a clause starts with a recognizable finite verb."""

    first, separator, _rest = str(value or "").strip().partition(" ")
    token = first.casefold().strip(".,:;")
    if not separator:
        return False
    if token in _FINITE_ACTION_VERBS:
        return True
    if token in _FINITE_ACTION_SUFFIX_FALSE_POSITIVES:
        return False
    return token.endswith(_FINITE_ACTION_SUFFIXES)


def looks_like_finite_action_token(value: str) -> bool:
    """Return true when a single token is a finite action verb shape."""

    token = _clean_word_token(value)
    if not token:
        return False
    if token in _FINITE_ACTION_VERBS:
        return True
    if token in _FINITE_ACTION_SUFFIX_FALSE_POSITIVES:
        return False
    return token.endswith(_FINITE_ACTION_SUFFIXES)


def modal_base_form_drift_phrases(value: str, *, window: int = 18) -> list[str]:
    """Return modal/action snippets that use finite verbs where base verbs are required."""

    phrases: list[str] = []
    for segment in _modal_segments(value):
        phrases.extend(_modal_base_form_drift_segment(segment, window=window))
    return _unique_strings(phrases)


def _modal_base_form_drift_segment(value: str, *, window: int) -> list[str]:
    tokens = _word_tokens(value)
    lowered = [_clean_word_token(token) for token in tokens]
    phrases: list[str] = []
    for modal_index, token in enumerate(lowered):
        if token not in _MODAL_BASE_FORM_MARKERS:
            continue
        window_end = min(len(lowered), modal_index + max(2, window))
        direct_index = _next_modal_candidate(lowered, modal_index + 1, window_end)
        if direct_index is not None and lowered[direct_index] == "be":
            continue
        if direct_index is not None and looks_like_finite_action_token(lowered[direct_index]):
            phrases.append(" ".join(tokens[modal_index : direct_index + 1]))
        if (
            direct_index is not None
            and not looks_like_base_action_token(lowered[direct_index])
            and direct_index + 1 < window_end
            and looks_like_finite_action_token(lowered[direct_index + 1])
        ):
            phrases.append(" ".join(tokens[modal_index : direct_index + 2]))
        for index in range(modal_index + 1, window_end - 1):
            if lowered[index] not in _MODAL_COORDINATORS:
                continue
            candidate_index = _next_modal_candidate(lowered, index + 1, window_end)
            if candidate_index is None:
                continue
            if looks_like_base_action_token(lowered[candidate_index]):
                continue
            if _coordinated_candidate_is_plural_object(lowered, candidate_index, window_end):
                continue
            if looks_like_finite_action_token(lowered[candidate_index]):
                phrases.append(" ".join(tokens[index : candidate_index + 1]))
    return _unique_strings(phrases)


def _coordinated_candidate_is_plural_object(tokens: list[str], candidate_index: int, window_end: int) -> bool:
    token = tokens[candidate_index]
    if token not in _MODAL_COORDINATED_PLURAL_OBJECT_TERMS:
        return False
    next_token = tokens[candidate_index + 1] if candidate_index + 1 < window_end else ""
    return next_token in _MODAL_COORDINATED_OBJECT_BOUNDARIES


def looks_like_base_action_token(value: str) -> bool:
    """Return true when a single token is a base action verb Odylith emits."""

    return _clean_word_token(value) in _INFINITIVE_TO_FINITE


def _modal_segments(value: str) -> list[str]:
    return [segment for segment in re.split(r"[.!?;:,]+", str(value or "")) if segment.strip()]


def _word_tokens(value: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", str(value or ""))


def _clean_word_token(value: str) -> str:
    return str(value or "").casefold().strip(".,:;()[]{}")


def _next_modal_candidate(tokens: list[str], start: int, end: int) -> int | None:
    index = start
    while index < end and tokens[index].endswith("ly"):
        index += 1
    return index if index < end else None


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        key = value.casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(value)
    return rows


def contains_finite_action(value: str) -> bool:
    """Return true when any phrase segment starts with a recognizable finite verb."""

    text = re.sub(r"[^A-Za-z0-9'-]+", " ", str(value or " ")).strip()
    words = text.split()
    for index in range(max(0, len(words) - 1)):
        if looks_like_finite_action(" ".join(words[index:])):
            return True
    return False


def looks_like_action_clause(value: str) -> bool:
    """Return true when a clause starts with a recognizable action verb."""

    first, separator, _rest = str(value or "").strip().partition(" ")
    token = first.casefold().strip(".,:;")
    if separator and token.endswith("ly"):
        return looks_like_action_clause(_rest)
    return bool(separator) and (looks_like_finite_action(value) or token in _INFINITIVE_TO_FINITE)


def finite_action_clause(value: str, *, default_verb: str = "owns", default_single_token: bool = True) -> str:
    """Return a responsibility clause with a finite leading verb.

    `default_single_token=False` preserves the older component-authoring
    behavior where a one-word noun fragment remains a fragment.
    """

    text = str(value or "").strip(" .")
    if not text:
        return ""
    head, separator, tail = text.partition(" ")
    verb = head.strip(",:;").casefold()
    if verb in _INFINITIVE_TO_FINITE and separator:
        return f"{_INFINITIVE_TO_FINITE[verb]} {tail.strip()}"
    if looks_like_finite_action(text):
        return _lower_initial_for_sentence(text)
    if separator or default_single_token:
        default = str(default_verb or "owns").strip().lower() or "owns"
        return f"{default} {_lower_initial_for_sentence(text)}"
    return _lower_initial_for_sentence(text)


def third_person_action_verb(value: str) -> str:
    """Return a narrow third-person form for action verbs Odylith emits."""

    verb = str(value or "").strip()
    if not verb:
        return verb
    lowered = verb.casefold()
    if lowered in _FINITE_ACTION_VERBS:
        return verb
    if lowered in _INFINITIVE_TO_FINITE:
        return _INFINITIVE_TO_FINITE[lowered]
    if lowered.endswith(("s", "x", "z", "ch", "sh")):
        return f"{verb}es"
    if lowered.endswith("y") and len(lowered) > 1 and lowered[-2] not in {"a", "e", "i", "o", "u"}:
        return f"{verb[:-1]}ies"
    return f"{verb}s"


def gerund_action_verb(value: str) -> str:
    """Return a narrow gerund form for action verbs Odylith emits."""

    token = _clean_word_token(value)
    if not token:
        return ""
    if token in _INFINITIVE_TO_FINITE:
        return _regular_gerund_form(token)
    base = _FINITE_TO_BASE.get(token)
    return _regular_gerund_form(base) if base else ""


def normalize_binary_action_control_phrase(value: str) -> str:
    """Repair clipped phrases like ``accept or dismiss control``."""

    action_pattern = action_verb_pattern(include_base=True, include_finite=True)

    def replace(match: re.Match[str]) -> str:
        left = gerund_action_verb(match.group("left"))
        right = gerund_action_verb(match.group("right"))
        if not left or not right:
            return match.group(0)
        return f"control for {left} or {right}"

    return re.sub(
        rf"\b(?P<left>{action_pattern})\s+or\s+(?P<right>{action_pattern})\s+control\b",
        replace,
        str(value or ""),
        flags=re.IGNORECASE,
    )


def repair_modal_base_form_drift(value: str) -> str:
    """Repair generated modal clauses that coordinate finite verbs."""

    finite_pattern = "|".join(re.escape(verb) for verb in sorted(_FINITE_TO_BASE, key=len, reverse=True))
    modal_pattern = "|".join(re.escape(modal) for modal in sorted(_MODAL_BASE_FORM_MARKERS))

    def replace_clause(match: re.Match[str]) -> str:
        return f"{match.group('modal')} {_repair_modal_clause_body(match.group('body'), finite_pattern=finite_pattern)}"

    return re.sub(
        rf"\b(?P<modal>{modal_pattern})\s+(?P<body>[^.!?;:]+)",
        replace_clause,
        str(value or ""),
        flags=re.IGNORECASE,
    )


def _repair_modal_clause_body(value: str, *, finite_pattern: str) -> str:
    text = str(value or "")
    first, separator, rest = text.partition(" ")
    first_token = _clean_word_token(first)
    if separator and first_token != "be" and first_token in _FINITE_TO_BASE:
        text = f"{_replace_word_token(first, _FINITE_TO_BASE[first_token])} {rest}"

    def replace_coordinated(match: re.Match[str]) -> str:
        verb = match.group("verb")
        base = _FINITE_TO_BASE.get(_clean_word_token(verb), verb.casefold())
        return f"{match.group('connector')} {match.group('modifier') or ''}{_replace_word_token(verb, base)}"

    return re.sub(
        rf"(?P<connector>\b(?:and|or)|,)\s+(?P<modifier>(?:[a-z]+ly\s+)?)"
        rf"(?P<verb>{finite_pattern})\b",
        replace_coordinated,
        text,
        flags=re.IGNORECASE,
    )


def action_base_verb_pattern() -> str:
    """Return a regex alternation for base action verbs recognized by this module."""

    return "|".join(re.escape(verb) for verb in sorted(_INFINITIVE_TO_FINITE, key=len, reverse=True))


def action_verb_pattern(
    *,
    include_base: bool = True,
    include_finite: bool = True,
    exclude: set[str] | frozenset[str] | None = None,
) -> str:
    """Return a regex alternation for recognized base and finite action verbs."""

    verbs: set[str] = set()
    if include_base:
        verbs.update(_INFINITIVE_TO_FINITE)
    if include_finite:
        verbs.update(_INFINITIVE_TO_FINITE.values())
    if exclude:
        verbs.difference_update(str(verb).casefold() for verb in exclude)
    return "|".join(re.escape(verb) for verb in sorted(verbs, key=len, reverse=True))


def base_following_action_verbs(value: str) -> str:
    """Convert leading and coordinated finite action verbs to base form."""

    text = str(value or "").strip(" .")
    if not text:
        return ""
    text = _base_action_part(text)
    finite_pattern = "|".join(re.escape(verb) for verb in sorted(_FINITE_TO_BASE, key=len, reverse=True))

    def replace(match: re.Match[str]) -> str:
        connector = match.group("connector")
        modifier = match.group("modifier") or ""
        verb = match.group("verb")
        base = _FINITE_TO_BASE.get(verb.casefold(), verb.casefold())
        return f"{connector} {modifier}{base}"

    return re.sub(
        rf"(?P<connector>\b(?:and|or)|,)\s+(?P<modifier>(?:[a-z]+ly\s+)?)"
        rf"(?P<verb>{finite_pattern})\b",
        replace,
        text,
        flags=re.IGNORECASE,
    )


def base_action_clause(value: str, *, force_leading_finite: bool = False) -> str:
    """Convert a finite action clause into the form used after ``to``."""

    parts = [part for part in re.split(r"(,\s*)", str(value or "").strip(" .")) if part]
    first_content = next((part for part in parts if not re.fullmatch(r",\s*", part)), "")
    if first_content and not looks_like_action_clause(first_content):
        first_token = first_content.split(maxsplit=1)[0] if first_content.split(maxsplit=1) else ""
        if not force_leading_finite or not looks_like_finite_action_token(first_token):
            text = str(value or "").strip(" .")
            return _lower_initial_for_sentence(text)
    converted: list[str] = []
    for part in parts:
        if re.fullmatch(r",\s*", part):
            converted.append(part)
            continue
        converted.append(_base_action_part(part))
    return base_following_action_verbs("".join(converted))


def base_gerund_clause(value: str) -> str:
    """Convert a generated gerund action list into a direct action claim."""

    parts = [part for part in re.split(r"(,\s*)", str(value or "").strip(" .")) if part]
    if not parts:
        return ""
    converted: list[str] = []
    conversion_seen = False
    for part in parts:
        if re.fullmatch(r",\s*", part):
            converted.append(part)
            continue
        text, converted_part = _base_gerund_part(part)
        converted.append(text)
        conversion_seen |= converted_part
    return "".join(converted).strip(" .") if conversion_seen else ""


def _base_action_part(value: str) -> str:
    leading_match = re.match(r"^\s*", value)
    leading = leading_match.group(0) if leading_match else ""
    core = value[len(leading) :]
    prefix_match = re.match(r"^((?:and|or)\s+)?(.+)$", core, flags=re.I)
    prefix = (prefix_match.group(1) or "") if prefix_match else ""
    body = prefix_match.group(2) if prefix_match else core
    adverb_match = re.match(r"^(?P<adverb>[A-Za-z]+ly\s+)(?P<body>.+)$", body)
    if adverb_match and looks_like_action_clause(adverb_match.group("body")):
        prefix = f"{prefix}{adverb_match.group('adverb')}"
        body = adverb_match.group("body")
    first, separator, rest = body.partition(" ")
    verb = first.casefold().strip(".,:;")
    if not separator and verb not in _FINITE_ACTION_VERBS:
        return f"{leading}{prefix}{_lower_initial_for_sentence(body)}"
    if verb in _FINITE_TO_BASE:
        base = _FINITE_TO_BASE[verb]
    elif verb not in _FINITE_ACTION_VERBS and not verb.endswith(_FINITE_ACTION_SUFFIXES):
        return f"{leading}{prefix}{_lower_initial_for_sentence(body)}"
    elif verb.endswith("ies"):
        base = f"{verb[:-3]}y"
    elif verb.endswith(("ches", "shes", "sses", "xes", "zes", "oes")):
        base = verb[:-2]
    elif verb.endswith("s"):
        base = verb[:-1]
    else:
        base = verb
    suffix = f" {rest.strip()}" if separator else ""
    return f"{leading}{prefix}{base}{suffix}"


def _base_gerund_part(value: str) -> tuple[str, bool]:
    leading_match = re.match(r"^\s*", value)
    leading = leading_match.group(0) if leading_match else ""
    core = value[len(leading) :]
    prefix_match = re.match(r"^((?:and|or)\s+)?(.+)$", core, flags=re.I)
    prefix = (prefix_match.group(1) or "") if prefix_match else ""
    body = prefix_match.group(2) if prefix_match else core
    first, separator, rest = body.partition(" ")
    token = first.casefold().strip(".,:;")
    base = _GERUND_TO_BASE.get(token)
    if not base:
        text, converted = _base_embedded_gerunds(body)
        return f"{leading}{prefix}{text}", converted
    tail, _ = _base_embedded_gerunds(rest.strip()) if separator else ("", False)
    suffix = f" {tail}" if tail else ""
    return f"{leading}{prefix}{_replace_word_token(first, base)}{suffix}", True


def _base_embedded_gerunds(value: str) -> tuple[str, bool]:
    converted = False

    def replace(match: re.Match[str]) -> str:
        nonlocal converted
        base = _GERUND_TO_BASE.get(match.group("verb").casefold().strip(".,:;"))
        if not base:
            return match.group(0)
        converted = True
        return f"{match.group('connector')} {_replace_word_token(match.group('verb'), base)}"

    text = re.sub(r"\b(?P<connector>and|or)\s+(?P<verb>[A-Za-z][A-Za-z'-]*ing)\b", replace, value)
    return text, converted


def _replace_word_token(original: str, replacement: str) -> str:
    leading = re.match(r"^\W*", original).group(0)
    trailing = re.search(r"\W*$", original).group(0)
    return f"{leading}{replacement}{trailing}"


def _regular_gerund_form(base: str) -> str:
    token = str(base or "").casefold()
    if token.endswith("ie"):
        return f"{token[:-2]}ying"
    if token.endswith("e") and not token.endswith(("ee", "oe", "ye")):
        return f"{token[:-1]}ing"
    if _should_double_final_consonant_for_gerund(token):
        return f"{token}{token[-1]}ing"
    return f"{token}ing"


def _should_double_final_consonant_for_gerund(token: str) -> bool:
    if len(token) < 3 or token[-1] in "wxy":
        return False
    if token in _GERUND_NO_DOUBLE_FINAL_CONSONANT:
        return False
    vowels = set("aeiou")
    return token[-1] not in vowels and token[-2] in vowels and token[-3] not in vowels


_GERUND_TO_BASE = {
    _regular_gerund_form(base): base
    for base in _INFINITIVE_TO_FINITE
}


def _lower_initial_for_sentence(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    subject_lowered = _lower_plain_title_subject_before_action(text)
    if subject_lowered != text:
        return subject_lowered
    phrase_lowered = _lower_plain_title_phrase(text)
    if phrase_lowered != text:
        return phrase_lowered
    match = re.match(r"(?P<prefix>[^A-Za-z0-9]*)(?P<token>[A-Za-z0-9][A-Za-z0-9_/-]*)", text)
    if not match:
        return text[:1].lower() + text[1:]
    token = match.group("token")
    if _preserve_initial_token_case(token):
        return text
    index = len(match.group("prefix"))
    return f"{text[:index]}{text[index:index + 1].lower()}{text[index + 1:]}"


def _preserve_initial_token_case(token: str) -> bool:
    letters = [char for char in str(token or "") if char.isalpha()]
    if len(letters) < 2:
        return False
    if all(char.isupper() for char in letters):
        return True
    return any(char.isupper() for char in letters[1:])


_PLAIN_TITLE_SUBJECT_CONNECTORS = frozenset({"and", "for", "in", "of", "on", "or", "to", "with"})


def _lower_plain_title_subject_before_action(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    body_match = re.match(r"(?P<prefix>[^A-Za-z0-9]*)(?P<body>.*)$", text, flags=re.DOTALL)
    prefix = body_match.group("prefix") if body_match else ""
    body = body_match.group("body") if body_match else text
    for match in re.finditer(
        rf"(?<![A-Za-z0-9_-])(?:{action_verb_pattern(include_base=False)})(?![A-Za-z0-9_-])",
        body,
        flags=re.IGNORECASE,
    ):
        if match.start() <= 0:
            continue
        before = body[: match.start()]
        subject = before.strip(" ,")
        if not _plain_title_subject_phrase(subject):
            continue
        subject_start = before.find(subject)
        subject_end = subject_start + len(subject)
        lowered_before = f"{before[:subject_start]}{subject.casefold()}{before[subject_end:]}"
        return f"{prefix}{lowered_before}{body[match.start():]}"
    return text


def _lower_plain_title_phrase(value: str) -> str:
    text = str(value or "")
    body_match = re.match(r"(?P<prefix>[^A-Za-z0-9]*)(?P<body>.*?)(?P<suffix>[^A-Za-z0-9]*)$", text, flags=re.DOTALL)
    prefix = body_match.group("prefix") if body_match else ""
    body = body_match.group("body") if body_match else text
    suffix = body_match.group("suffix") if body_match else ""
    if not _plain_title_subject_phrase(body.strip(" ,")):
        return text
    return f"{prefix}{body.casefold()}{suffix}"


def _plain_title_subject_phrase(value: str) -> bool:
    words = [word.strip(".,;:()[]{}") for word in str(value or "").split() if word.strip(".,;:()[]{}")]
    if len(words) < 2:
        return False
    if any(any(char.isdigit() for char in word) or (word.isupper() and len(word) > 1) for word in words):
        return False
    return all(word[:1].isupper() or word.casefold() in _PLAIN_TITLE_SUBJECT_CONNECTORS for word in words)
