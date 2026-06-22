"""Small domain-neutral grammar helpers for generated product prose.

These helpers only handle the narrow verb-shape cases Odylith emits while
turning accepted product intent into governance records. They intentionally do
not classify domains or infer project meaning.
"""

from __future__ import annotations

import re


_INFINITIVE_TO_FINITE = {
    "accept": "accepts",
    "add": "adds",
    "advance": "advances",
    "allow": "allows",
    "allocate": "allocates",
    "answer": "answers",
    "apply": "applies",
    "assemble": "assembles",
    "ask": "asks",
    "attach": "attaches",
    "assign": "assigns",
    "bind": "binds",
    "block": "blocks",
    "book": "books",
    "build": "builds",
    "calculate": "calculates",
    "capture": "captures",
    "catch": "catches",
    "check": "checks",
    "choose": "chooses",
    "classify": "classifies",
    "click": "clicks",
    "clean": "cleans",
    "collect": "collects",
    "compare": "compares",
    "compute": "computes",
    "complete": "completes",
    "confirm": "confirms",
    "connect": "connects",
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
    "get": "gets",
    "guide": "guides",
    "handle": "handles",
    "highlight": "highlights",
    "hold": "holds",
    "identify": "identifies",
    "import": "imports",
    "ingest": "ingests",
    "inspect": "inspects",
    "issue": "issues",
    "keep": "keeps",
    "launch": "launches",
    "let": "lets",
    "link": "links",
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
    "optimize": "optimizes",
    "own": "owns",
    "pay": "pays",
    "perform": "performs",
    "place": "places",
    "predict": "predicts",
    "present": "presents",
    "preserve": "preserves",
    "prevent": "prevents",
    "persist": "persists",
    "pick": "picks",
    "play": "plays",
    "prompt": "prompts",
    "pull": "pulls",
    "push": "pushes",
    "produce": "produces",
    "propose": "proposes",
    "provide": "provides",
    "publish": "publishes",
    "rank": "ranks",
    "rate": "rates",
    "read": "reads",
    "receive": "receives",
    "recommend": "recommends",
    "record": "records",
    "recompute": "recomputes",
    "refresh": "refreshes",
    "reject": "rejects",
    "request": "requests",
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
    "set": "sets",
    "share": "shares",
    "start": "starts",
    "store": "stores",
    "stop": "stops",
    "submit": "submits",
    "suggest": "suggests",
    "support": "supports",
    "surface": "surfaces",
    "sync": "syncs",
    "tap": "taps",
    "track": "tracks",
    "transform": "transforms",
    "update": "updates",
    "upload": "uploads",
    "use": "uses",
    "view": "views",
    "validate": "validates",
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


def base_action_clause(value: str) -> str:
    """Convert a finite action clause into the form used after ``to``."""

    parts = [part for part in re.split(r"(,\s*)", str(value or "").strip(" .")) if part]
    first_content = next((part for part in parts if not re.fullmatch(r",\s*", part)), "")
    if first_content and not looks_like_action_clause(first_content):
        text = str(value or "").strip(" .")
        return _lower_initial_for_sentence(text)
    converted: list[str] = []
    for part in parts:
        if re.fullmatch(r",\s*", part):
            converted.append(part)
            continue
        converted.append(_base_action_part(part))
    return base_following_action_verbs("".join(converted))


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


def _lower_initial_for_sentence(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
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
