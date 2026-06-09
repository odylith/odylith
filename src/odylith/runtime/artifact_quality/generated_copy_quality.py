"""Generated-copy quality classifiers for public greenfield artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


@dataclass(frozen=True)
class GeneratedCopyFinding:
    category: str
    message: str


def generated_public_copy_issues(scope: str, value: Any) -> tuple[str, ...]:
    """Return public-copy failures classified by generated-prose shape."""

    findings: list[GeneratedCopyFinding] = []
    for text in _text_quality_units(value):
        tokens = _word_tokens(text)
        lowered = tuple(token.casefold() for token in tokens)
        if _has_mechanical_actor_path_clause(lowered):
            findings.append(GeneratedCopyFinding("mechanical_actor_path", f"{scope} leaked mechanical actor-path prose"))
        if _has_expected_local_output_clause(lowered):
            findings.append(GeneratedCopyFinding("generic_local_output", f"{scope} leaked generic local-output prose"))
        if _concept_tuple_hits(lowered, _ABSTRACT_INPUT_CONCEPTS) >= 3:
            findings.append(GeneratedCopyFinding("contract_tuple", f"{scope} leaked Registry contract tuple prose"))
        if _concept_tuple_hits(lowered, _ABSTRACT_OUTPUT_CONCEPTS) >= 3:
            findings.append(GeneratedCopyFinding("produced_output_tuple", f"{scope} leaked produced-output tuple prose"))
        if _has_raw_success_metric_gate(lowered):
            findings.append(GeneratedCopyFinding("raw_success_metric_gate", f"{scope} leaked raw success-metric gate prose"))
        if _has_actor_action_splice(lowered):
            findings.append(GeneratedCopyFinding("actor_action_splice", f"{scope} leaked actor/action splice prose"))
        if _has_terminal_result_chain(lowered):
            findings.append(GeneratedCopyFinding("terminal_result_chain", f"{scope} leaked terminal action inside result prose"))
        if _has_awkward_visible_result_action(lowered):
            findings.append(GeneratedCopyFinding("awkward_visible_result_action", f"{scope} leaked awkward visible-result action prose"))
        if _has_meta_loop_outcome(lowered):
            findings.append(GeneratedCopyFinding("meta_loop_outcome", f"{scope} leaked meta loop summary as product outcome"))
        if _has_malformed_component_responsibility(lowered):
            findings.append(GeneratedCopyFinding("malformed_component_responsibility", f"{scope} leaked malformed component responsibility prose"))
    return unique_text(finding.message for finding in findings)


def _has_mechanical_actor_path_clause(tokens: tuple[str, ...]) -> bool:
    return _has_ordered_terms(tokens, ("can", "act", "accepted", "path", "requires"), max_gap=3)


def _has_expected_local_output_clause(tokens: tuple[str, ...]) -> bool:
    return _has_ordered_terms(tokens, ("expected", "local", "output"), max_gap=1)


def _has_raw_success_metric_gate(tokens: tuple[str, ...]) -> bool:
    return _has_ordered_terms(tokens, ("validate", "that", "satisfies", "local", "success", "criteria"), max_gap=12)


def _has_actor_action_splice(tokens: tuple[str, ...]) -> bool:
    finite_actions = {"adds", "creates", "makes", "opens", "picks", "sees"}
    for index in range(0, max(0, len(tokens) - 4)):
        if tokens[index : index + 4] != ("uses", "the", "product", "to"):
            continue
        window = tokens[index + 4 : min(len(tokens), index + 11)]
        for offset, token in enumerate(window):
            if offset == 0 or token not in finite_actions:
                continue
            return True
    return False


def _has_terminal_result_chain(tokens: tuple[str, ...]) -> bool:
    result_words = {"consequence", "outcome", "readout", "reflection", "result", "summary", "view"}
    terminal_words = {"complete", "completes", "end", "ends", "finish", "finishes"}
    for index, token in enumerate(tokens):
        if token not in result_words:
            continue
        window = tokens[index + 1 : min(len(tokens), index + 5)]
        if "and" in window and any(item in terminal_words for item in window):
            return True
    return False


def _has_awkward_visible_result_action(tokens: tuple[str, ...]) -> bool:
    result_words = {"consequence", "outcome", "readout", "reflection", "result", "summary", "view"}
    for index, token in enumerate(tokens[:-1]):
        if token in {"reach", "use"} and any(item in result_words for item in tokens[index + 1 : min(len(tokens), index + 5)]):
            return True
    return False


def _has_meta_loop_outcome(tokens: tuple[str, ...]) -> bool:
    for index, token in enumerate(tokens):
        if token not in {"loop", "path", "journey", "flow", "pattern"}:
            continue
        window = tokens[index + 1 : min(len(tokens), index + 16)]
        if _has_ordered_terms(window, ("smallest", "version", "whole", "product"), max_gap=2):
            return True
        if _has_ordered_terms(window, ("working", "end", "to", "end"), max_gap=1):
            return True
    return False


def _has_malformed_component_responsibility(tokens: tuple[str, ...]) -> bool:
    malformed_verbs = {"continue", "keep", "maintain", "sustain"}
    for index, token in enumerate(tokens[:-1]):
        if token == "maintains" and tokens[index + 1] in malformed_verbs:
            return True
    return False


def _concept_tuple_hits(tokens: tuple[str, ...], concepts: tuple[tuple[str, ...], ...]) -> int:
    return sum(1 for concept in concepts if _has_ordered_terms(tokens, concept, max_gap=1))


def _has_ordered_terms(tokens: tuple[str, ...], terms: tuple[str, ...], *, max_gap: int) -> bool:
    if not terms:
        return False
    for start, token in enumerate(tokens):
        if token != terms[0]:
            continue
        if _ordered_terms_from(tokens, terms, start=start, max_gap=max_gap):
            return True
    return False


def _ordered_terms_from(tokens: tuple[str, ...], terms: tuple[str, ...], *, start: int, max_gap: int) -> bool:
    index = 1
    position = start
    while index < len(terms):
        search_limit = min(len(tokens), position + max_gap + 2)
        next_position = -1
        for candidate in range(position + 1, search_limit):
            if tokens[candidate] == terms[index]:
                next_position = candidate
                break
        if next_position < 0:
            return False
        position = next_position
        index += 1
    return True


def _word_tokens(value: str) -> tuple[str, ...]:
    tokens: list[str] = []
    current: list[str] = []
    for char in str(value or ""):
        if char.isalnum() or char == "'":
            current.append(char)
            continue
        if current:
            tokens.append("".join(current).strip("'"))
            current = []
    if current:
        tokens.append("".join(current).strip("'"))
    return tuple(token for token in tokens if token)


def _text_quality_units(value: Any) -> tuple[str, ...]:
    units: list[str] = []
    _append_text_quality_units(units, value)
    return unique_text(units)


def _append_text_quality_units(units: list[str], value: Any) -> None:
    if value is None:
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            _append_text_quality_units(units, nested)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            _append_text_quality_units(units, nested)
        return
    current: list[str] = []
    for char in str(value or ""):
        if char in ".!?\n\r;":
            _append_quality_chunk(units, current)
            current = []
        else:
            current.append(char)
    _append_quality_chunk(units, current)


def _append_quality_chunk(units: list[str], chars: list[str]) -> None:
    text = clean_text("".join(chars)).strip(" -#*_`|")
    if text:
        units.append(text)


_ABSTRACT_INPUT_CONCEPTS = (
    ("actor", "identity"),
    ("user", "identity"),
    ("validation", "context"),
    ("routing", "context"),
    ("source", "context"),
    ("upstream", "handoff"),
    ("source", "handoff"),
    ("intake", "handoff"),
)
_ABSTRACT_OUTPUT_CONCEPTS = (
    ("blocker", "signal"),
    ("error", "signal"),
    ("review", "rationale"),
    ("reviewer", "rationale"),
    ("downstream", "handoff"),
    ("delivery", "handoff"),
    ("handoff", "evidence"),
)


__all__ = ["GeneratedCopyFinding", "generated_public_copy_issues"]
