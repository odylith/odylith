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
    "allow": "allows",
    "apply": "applies",
    "assemble": "assembles",
    "assign": "assigns",
    "bind": "binds",
    "calculate": "calculates",
    "capture": "captures",
    "check": "checks",
    "classify": "classifies",
    "clean": "cleans",
    "collect": "collects",
    "compare": "compares",
    "compute": "computes",
    "connect": "connects",
    "convert": "converts",
    "coordinate": "coordinates",
    "create": "creates",
    "decide": "decides",
    "derive": "derives",
    "detect": "detects",
    "enforce": "enforces",
    "estimate": "estimates",
    "evaluate": "evaluates",
    "explain": "explains",
    "export": "exports",
    "fetch": "fetches",
    "filter": "filters",
    "flag": "flags",
    "guide": "guides",
    "handle": "handles",
    "hold": "holds",
    "identify": "identifies",
    "import": "imports",
    "ingest": "ingests",
    "link": "links",
    "manage": "manages",
    "map": "maps",
    "normalize": "normalizes",
    "own": "owns",
    "perform": "performs",
    "present": "presents",
    "preserve": "preserves",
    "prevent": "prevents",
    "produce": "produces",
    "provide": "provides",
    "publish": "publishes",
    "rank": "ranks",
    "record": "records",
    "refresh": "refreshes",
    "reject": "rejects",
    "render": "renders",
    "resolve": "resolves",
    "review": "reviews",
    "route": "routes",
    "score": "scores",
    "serve": "serves",
    "show": "shows",
    "store": "stores",
    "submit": "submits",
    "support": "supports",
    "sync": "syncs",
    "track": "tracks",
    "use": "uses",
    "validate": "validates",
    "watch": "watches",
    "write": "writes",
}

_FINITE_ACTION_VERBS = set(_INFINITIVE_TO_FINITE.values()) | {
    "does",
    "has",
    "is",
}

_FINITE_ACTION_SUFFIXES = (
    "ates",
    "ifies",
    "ises",
    "izes",
    "ves",
)


def looks_like_finite_action(value: str) -> bool:
    """Return true when a clause starts with a recognizable finite verb."""

    first, separator, _rest = str(value or "").strip().partition(" ")
    token = first.casefold().strip(".,:;")
    if not separator:
        return False
    if token in _FINITE_ACTION_VERBS:
        return True
    return token.endswith(_FINITE_ACTION_SUFFIXES)


def looks_like_action_clause(value: str) -> bool:
    """Return true when a clause starts with a recognizable action verb."""

    first, separator, _rest = str(value or "").strip().partition(" ")
    token = first.casefold().strip(".,:;")
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
        return text[:1].lower() + text[1:]
    if separator or default_single_token:
        default = str(default_verb or "owns").strip().lower() or "owns"
        return f"{default} {text[:1].lower()}{text[1:]}"
    return text[:1].lower() + text[1:]


def base_action_clause(value: str) -> str:
    """Convert a finite action clause into the form used after ``to``."""

    parts = [part for part in re.split(r"(,\s*)", str(value or "").strip(" .")) if part]
    converted: list[str] = []
    for part in parts:
        if re.fullmatch(r",\s*", part):
            converted.append(part)
            continue
        converted.append(_base_action_part(part))
    return "".join(converted).strip()


def _base_action_part(value: str) -> str:
    prefix_match = re.match(r"^(\s*(?:and|or)\s+)?(.+)$", value, flags=re.I)
    prefix = (prefix_match.group(1) or "") if prefix_match else ""
    body = prefix_match.group(2) if prefix_match else value
    first, separator, rest = body.partition(" ")
    verb = first.casefold().strip(".,:;")
    if verb == "has":
        base = "have"
    elif verb == "does":
        base = "do"
    elif verb == "is":
        base = "be"
    elif verb.endswith("ies"):
        base = f"{verb[:-3]}y"
    elif verb.endswith(("ches", "shes", "sses", "xes", "zes", "oes")):
        base = verb[:-2]
    elif verb.endswith("s"):
        base = verb[:-1]
    else:
        base = verb
    suffix = f" {rest.strip()}" if separator else ""
    return f"{prefix}{base}{suffix}"
