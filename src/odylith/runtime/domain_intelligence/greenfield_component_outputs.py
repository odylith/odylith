"""Output artifact extraction for greenfield component contracts."""

from __future__ import annotations

from collections.abc import Sequence

from odylith.runtime.domain_intelligence.greenfield_actor_terms import looks_actor_term
from odylith.runtime.domain_intelligence.greenfield_component_terms import action_object_artifact_phrases
from odylith.runtime.domain_intelligence.greenfield_component_terms import canonical_action
from odylith.runtime.domain_intelligence.greenfield_component_terms import trim_phrase
from odylith.runtime.domain_intelligence.greenfield_component_term_constants import ARTIFACT_CARRIER_TERMS
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_text
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


_ACTION_KINDS = {
    "apply": "process",
    "check": "process",
    "coordinate": "process",
    "create": "direct",
    "display": "presentation",
    "emit": "direct",
    "export": "direct",
    "generate": "direct",
    "hand": "process",
    "handle": "process",
    "issue": "direct",
    "pass": "process",
    "present": "presentation",
    "produce": "direct",
    "publish": "direct",
    "return": "direct",
    "route": "process",
    "send": "process",
    "show": "presentation",
    "validate": "nominal",
    "verify": "process",
}
_NOMINAL_ACTION_MODIFIERS = {"export"}


def produced_output_artifact_phrases(value: str, *, preserve_unclassified: bool = False) -> list[str]:
    """Return artifact nouns from output clauses without retaining process narration."""

    rows: list[str] = []
    for raw in clean_artifact_text(value).replace(";", ",").split(","):
        words = trim_phrase(raw).split()
        if words and words[0].casefold() in {"and", "or"}:
            words = words[1:]
        if not words:
            continue
        raw_action = words[0].strip(".,;:")
        action = canonical_action(raw_action, _ACTION_KINDS)
        kind = _ACTION_KINDS.get(action, "")
        if preserve_unclassified and _is_nominal_action_compound(words, action):
            kind = ""
        if kind == "nominal":
            rows.extend(action_object_artifact_phrases(" ".join(words)))
            continue
        if kind == "process":
            continue
        if kind in {"direct", "presentation"}:
            output_words = _output_object_words(words[1:], drop_recipient=kind == "presentation")
            output = trim_phrase(" ".join(output_words))
            if output:
                rows.append(output)
            continue
        if preserve_unclassified:
            rows.append(" ".join(words))
    return unique_text(rows)


def _is_nominal_action_compound(words: Sequence[str], action: str) -> bool:
    if action not in _NOMINAL_ACTION_MODIFIERS or len(words) < 2:
        return False
    return words[1].casefold().strip(".,;:") in ARTIFACT_CARRIER_TERMS


def _output_object_words(words: Sequence[str], *, drop_recipient: bool) -> list[str]:
    result = list(words)
    if result and result[0].casefold().strip(".,;:") in {"a", "an", "the"}:
        result = result[1:]
    if not drop_recipient:
        return result
    for index, word in enumerate(result[:3]):
        if looks_actor_term(word):
            return result[index + 1 :]
    return result


__all__ = ["produced_output_artifact_phrases"]
