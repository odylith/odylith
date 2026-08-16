"""Output artifact extraction for greenfield component contracts."""

from __future__ import annotations

from collections.abc import Sequence

from odylith.runtime.common.prose_grammar import looks_like_finite_action_token
from odylith.runtime.domain_intelligence.greenfield_actor_roles import has_actor_role_word
from odylith.runtime.domain_intelligence.greenfield_actor_terms import looks_actor_term
from odylith.runtime.domain_intelligence.greenfield_component_terms import action_object_artifact_phrases
from odylith.runtime.domain_intelligence.greenfield_component_terms import canonical_action
from odylith.runtime.domain_intelligence.greenfield_component_terms import finite_action_clause, trim_phrase
from odylith.runtime.domain_intelligence.greenfield_component_term_constants import ARTIFACT_CARRIER_TERMS
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import transformation_result_object
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
    "keep": "process",
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
_NOMINAL_ACTION_MODIFIERS = {"check", "export"}


def produced_output_artifact_phrases(value: str, *, preserve_unclassified: bool = False) -> list[str]:
    rows: list[str] = []
    for raw in clean_artifact_text(value).replace(";", ",").split(","):
        if transformation_output := transformation_result_object(raw):
            rows.append(transformation_output)
            continue
        for words in _coordinated_action_segments(trim_phrase(raw).split()):
            action_clause, owns_action = finite_action_clause(" ".join(words))
            action_words = action_clause.split() if owns_action else words
            if not action_words:
                continue
            action = canonical_action(action_words[0].strip(".,;:"), _ACTION_KINDS)
            kind = _ACTION_KINDS.get(action, "")
            if (
                preserve_unclassified
                and _is_nominal_action_compound(action_words, action)
                and (action != "check" or len(words) - len(action_words) >= 2)
                and not has_actor_role_word(" ".join(words[: len(words) - len(action_words)]))
            ):
                kind = ""
            if kind == "nominal":
                rows.extend(action_object_artifact_phrases(" ".join(action_words)))
                continue
            if kind == "process":
                continue
            if kind in {"direct", "presentation"}:
                output_words = _output_object_words(action_words[1:], drop_recipient=kind == "presentation")
                output = trim_phrase(" ".join(output_words))
                if output:
                    rows.append(output)
                continue
            if preserve_unclassified:
                rows.append(" ".join(words))
    return unique_text(rows)


def _coordinated_action_segments(words: Sequence[str]) -> list[list[str]]:
    if not words:
        return []
    starts = [0]
    for index in range(1, len(words)):
        if words[index - 1].casefold().strip(".,;:") not in {"and", "then"}:
            continue
        token = words[index].strip(".,;:")
        action = canonical_action(token, _ACTION_KINDS)
        left = words[starts[-1] : index - 1]
        if (
            action in _ACTION_KINDS
            and looks_like_finite_action_token(token)
            and finite_action_clause(" ".join(left))[1]
        ):
            starts.append(index)
    ends = [start - 1 for start in starts[1:]] + [len(words)]
    return [words[start:end] for start, end in zip(starts, ends, strict=True) if words[start:end]]


def _is_nominal_action_compound(words: Sequence[str], action: str) -> bool:
    carrier = words[1].casefold().strip(".,;:") if len(words) >= 2 else ""
    return action in _NOMINAL_ACTION_MODIFIERS and carrier in ARTIFACT_CARRIER_TERMS


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
