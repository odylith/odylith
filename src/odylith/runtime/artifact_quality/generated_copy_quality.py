"""Generated-copy quality classifiers for public greenfield artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
import re
from typing import Any

from odylith.runtime.artifact_quality.generated_copy_quality_units import raw_text_units
from odylith.runtime.artifact_quality.generated_copy_quality_units import text_quality_units
from odylith.runtime.common.prose_grammar import action_token_form
from odylith.runtime.common.prose_grammar import coordinated_action_form_after_connector
from odylith.runtime.domain_intelligence.greenfield_generated_prose_shape import actor_led_finite_action_inside_user_can
from odylith.runtime.domain_intelligence.greenfield_generated_prose_shape import gerund_actor_role_finite_action_splice
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


@dataclass(frozen=True)
class GeneratedCopyFinding:
    category: str
    message: str


@dataclass(frozen=True)
class _WordToken:
    text: str
    separator_before: str = ""
    hyphen_before: bool = False
    hyphen_after: bool = False


_INLINE_ROLE_TERMS = (
    "Admin",
    "Administrator",
    "Actor",
    "Applicant",
    "Coordinator",
    "Customer",
    "Lead",
    "Manager",
    "Operator",
    "Owner",
    "Participant",
    "Reviewer",
    "User",
)
_INLINE_ROLE_HEAD_STOPWORDS = frozenset(
    {
        "a",
        "and",
        "an",
        "as",
        "at",
        "by",
        "each",
        "for",
        "from",
        "if",
        "in",
        "include",
        "includes",
        "involve",
        "involves",
        "is",
        "list",
        "lists",
        "of",
        "one",
        "or",
        "show",
        "shows",
        "so",
        "that",
        "the",
        "this",
        "to",
        "treat",
        "treating",
        "with",
        "when",
        "where",
        "whether",
        "while",
    }
)


def generated_public_copy_findings(scope: str, value: Any) -> tuple[GeneratedCopyFinding, ...]:
    """Return public-copy failures classified by generated-prose shape."""

    findings: list[GeneratedCopyFinding] = []
    for unit in raw_text_units(value):
        if unit.text_kind in {"metadata"}:
            continue
        text = unit.text
        if _has_malformed_punctuation_sequence(text):
            findings.append(GeneratedCopyFinding("malformed_punctuation", f"{scope} leaked malformed punctuation"))
    for unit in text_quality_units(value):
        if unit.text_kind in {"command", "metadata"}:
            continue
        text = unit.text
        tokens = _word_tokens(text)
        token_rows = _word_token_rows(text)
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
        if actor_led_finite_action_inside_user_can(text):
            findings.append(GeneratedCopyFinding("actor_led_modal_splice", f"{scope} leaked actor-led finite action inside user-can prose"))
        if gerund_actor_role_finite_action_splice(text):
            findings.append(GeneratedCopyFinding("gerund_actor_role_splice", f"{scope} leaked gerundized actor-role action prose"))
        if _has_terminal_result_chain(lowered):
            findings.append(GeneratedCopyFinding("terminal_result_chain", f"{scope} leaked terminal action inside result prose"))
        if _has_adjacent_duplicate_word(token_rows):
            findings.append(GeneratedCopyFinding("adjacent_duplicate_word", f"{scope} leaked adjacent duplicate word prose"))
        if _has_clipped_terminal_public_copy(lowered):
            findings.append(GeneratedCopyFinding("clipped_public_copy", f"{scope} leaked clipped or dangling public copy"))
        if _has_awkward_visible_result_action(token_rows):
            findings.append(GeneratedCopyFinding("awkward_visible_result_action", f"{scope} leaked awkward visible-result action prose"))
        if _has_presentational_action_splice(text.casefold()):
            findings.append(GeneratedCopyFinding("presentational_action_splice", f"{scope} leaked presentational verb/action splice prose"))
        if _has_mixed_adverbial_action_inflection(text):
            findings.append(GeneratedCopyFinding("mixed_action_inflection", f"{scope} leaked mixed finite/base action prose"))
        if _has_mixed_compact_action_inflection(text):
            findings.append(GeneratedCopyFinding("compact_action_inflection", f"{scope} leaked compact path mixed action prose"))
        if unit.text_kind == "mermaid_label" and _has_mixed_label_action_coordination(lowered):
            findings.append(
                GeneratedCopyFinding(
                    "mixed_label_action_inflection",
                    f"{scope} leaked mixed finite/base action in visible label",
                )
            )
        if _has_saved_destination_result_slop(text):
            findings.append(GeneratedCopyFinding("saved_destination_result", f"{scope} leaked saved-destination result prose"))
        if _has_possessive_result_list_slop(text):
            findings.append(GeneratedCopyFinding("possessive_result_list", f"{scope} leaked possessive result-list prose"))
        if _has_scope_prefix_label_slop(text):
            findings.append(GeneratedCopyFinding("scope_prefix_label", f"{scope} leaked scope prefix as a system label"))
        if _has_template_slice_prefix(lowered):
            findings.append(GeneratedCopyFinding("template_slice_prefix", f"{scope} leaked repetitive implementation-slice template prose"))
        if _has_meta_loop_outcome(lowered):
            findings.append(GeneratedCopyFinding("meta_loop_outcome", f"{scope} leaked meta loop summary as product outcome"))
        if _has_malformed_component_responsibility(lowered):
            findings.append(GeneratedCopyFinding("malformed_component_responsibility", f"{scope} leaked malformed component responsibility prose"))
        if _has_malformed_relative_clause_split(lowered):
            findings.append(GeneratedCopyFinding("malformed_relative_clause_split", f"{scope} leaked malformed relative-clause split prose"))
        if _has_malformed_relation_phrase(text):
            findings.append(GeneratedCopyFinding("malformed_relation_phrase", f"{scope} leaked malformed relation phrase"))
        if _has_malformed_punctuation_sequence(text):
            findings.append(GeneratedCopyFinding("malformed_punctuation", f"{scope} leaked malformed punctuation"))
        if _has_unbalanced_quote_span(text):
            findings.append(GeneratedCopyFinding("unbalanced_quote", f"{scope} leaked unbalanced quoted text"))
        if _has_mixed_lower_title_role_fragment(text):
            findings.append(GeneratedCopyFinding("mixed_role_case", f"{scope} leaked mixed actor-role casing"))
        if _has_prepositional_visible_result_splice(text):
            findings.append(GeneratedCopyFinding("prepositional_visible_result", f"{scope} leaked prepositional visible-result splice"))
    return _unique_findings(findings)


def generated_public_copy_issues(scope: str, value: Any) -> tuple[str, ...]:
    """Return public-copy failure messages for generated prose."""

    return unique_text(finding.message for finding in generated_public_copy_findings(scope, value))


def _has_malformed_punctuation_sequence(value: str) -> bool:
    text = str(value or "")
    if _looks_like_key_value_context(text):
        return False
    return bool(re.search(r"[,;:]\s*[.!?]|\.\s*,", text))


def _looks_like_key_value_context(value: str) -> bool:
    text = clean_text(value)
    return bool(";" in text and re.search(r"\b[a-z][a-z0-9_]{1,40}=", text))


def _unique_findings(findings: Sequence[GeneratedCopyFinding]) -> tuple[GeneratedCopyFinding, ...]:
    seen: set[str] = set()
    result: list[GeneratedCopyFinding] = []
    for finding in findings:
        key = finding.message.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return tuple(result)


def has_inline_role_casing_drift(value: Any) -> bool:
    """Return true for sentence text like ``the station Lead``."""

    pattern = "|".join(re.escape(term) for term in _INLINE_ROLE_TERMS)
    for match in re.finditer(
        rf"\b(?i:the|a|an|this|that)\s+(?P<head>[a-z][a-z0-9'-]*)\s+(?P<role>{pattern})\b",
        str(value or ""),
    ):
        if match.start("head") > 0 and str(value or "")[match.start("head") - 1] == "-":
            continue
        if match.group("head").casefold() in _INLINE_ROLE_HEAD_STOPWORDS:
            continue
        if _continues_title_after_role(value, match.end()):
            continue
        return True
    return False


def _has_mixed_lower_title_role_fragment(value: str) -> bool:
    text = str(value or "")
    pattern = (
        r"\b(?P<head>[a-z][a-z0-9'-]+)\s+(?P<title>[A-Z][a-z][A-Za-z0-9'-]*)\s+"
        r"(?:can|cannot|needs?|picks?|chooses?|selects?|starts?|opens?|enters?|uploads?|runs?|sees?|views?|receives?|reviews?)\b"
    )
    for match in re.finditer(pattern, text):
        if match.start("head") > 0 and text[match.start("head") - 1] == "-":
            continue
        if match.group("head").casefold() in _INLINE_ROLE_HEAD_STOPWORDS:
            continue
        previous = text[: match.start()].rstrip().rsplit(" ", 1)[-1].casefold()
        if previous in {"a", "an", "the", "this", "that"}:
            continue
        return True
    return False


def _has_prepositional_visible_result_splice(value: str) -> bool:
    text = str(value or "")
    return bool(
        re.search(r"\b(?:reach|reaches|reaching|see|sees|seeing)\s+With\b", text)
        or re.search(r"\b(?:reach|reaches|reaching)\s+with\s+(?:a|an|the)\b", text, flags=re.IGNORECASE)
    )


def _has_unbalanced_quote_span(value: str) -> bool:
    text = str(value or "")
    return (
        text.count('"') % 2 == 1
        or text.count("“") != text.count("”")
        or bool(re.search(r"(?:^|\s)'[A-Za-z][^']*$", text))
    )


def _continues_title_after_role(value: Any, offset: int) -> bool:
    tail = str(value or "")[offset:].lstrip()
    if re.match(r"^[/&]\s+[A-Z]", tail):
        return True
    match = re.match(r"([A-Za-z][A-Za-z0-9'-]*)\b", tail)
    return bool(match and match.group(1)[:1].isupper())


def _has_mechanical_actor_path_clause(tokens: tuple[str, ...]) -> bool:
    return _has_ordered_terms(tokens, ("can", "act", "accepted", "path", "requires"), max_gap=3)


def _has_malformed_relation_phrase(value: str) -> bool:
    return bool(
        re.search(
            r"\b(?:entities|entity)\s+"
            r"[a-z0-9][a-z0-9 '-]{1,80}?\s+"
            r"(?:attach(?:es|ed)?|belong(?:s|ed)?|connect(?:s|ed)?|link(?:s|ed)?|map(?:s|ped)?|relate(?:s|d)?)\s+"
            r"(?:against|around|for|from|into|to|toward|towards|with)\b",
            clean_text(value).casefold(),
        )
    )


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
        if _result_word_is_captured_object(tokens, index):
            continue
        window = tokens[index + 1 : min(len(tokens), index + 5)]
        if "and" in window and any(item in terminal_words for item in window):
            return True
    return False


def _result_word_is_captured_object(tokens: tuple[str, ...], index: int) -> bool:
    capture_verbs = {
        "add",
        "adds",
        "capture",
        "captures",
        "enter",
        "enters",
        "record",
        "records",
        "save",
        "saves",
        "submit",
        "submits",
        "write",
        "writes",
    }
    left = tokens[max(0, index - 5) : index]
    return any(token in capture_verbs for token in left)


def _has_adjacent_duplicate_word(tokens: tuple[_WordToken, ...]) -> bool:
    previous = ""
    for token in tokens:
        current = token.text.casefold().strip(".,;:")
        if (
            current
            and len(current) > 2
            and previous == current
            and not token.hyphen_before
            and not token.separator_before.strip()
        ):
            return True
        previous = current
    return False


def _has_clipped_terminal_public_copy(tokens: tuple[str, ...]) -> bool:
    if len(tokens) < 5:
        return False
    return tokens[-1] in {
        "include",
        "includes",
        "keep",
        "keeps",
        "remain",
        "remains",
        "return",
        "returns",
        "with",
    }


def _has_awkward_visible_result_action(tokens: tuple[_WordToken, ...]) -> bool:
    result_words = {"consequence", "outcome", "readiness", "readout", "reflection", "result", "summary", "view"}
    lowered = tuple(token.text.casefold() for token in tokens)
    for index, token in enumerate(tokens[:-1]):
        if token.hyphen_before or token.hyphen_after:
            continue
        if _token_is_title_label_word(tokens, index):
            continue
        if token.text.casefold() in {"reach", "use"} and any(
            item in result_words for item in lowered[index + 1 : min(len(lowered), index + 5)]
        ):
            return True
    return False


def _token_is_title_label_word(tokens: tuple[_WordToken, ...], index: int) -> bool:
    if index <= 0 or index >= len(tokens):
        return False
    token = tokens[index].text.strip("'")
    if not token[:1].isupper():
        return False
    previous = tokens[index - 1].text.strip("'") if index > 0 else ""
    next_token = tokens[index + 1].text.strip("'") if index + 1 < len(tokens) else ""
    return _looks_like_title_token(previous) or _looks_like_title_token(next_token)


def _looks_like_title_token(value: str) -> bool:
    text = str(value or "").strip("'")
    if len(text) <= 1:
        return False
    return text[:1].isupper() or text.isupper()


_PRESENTATIONAL_VERBS = {"display", "displays", "present", "presents", "show", "showing", "shown", "shows"}
_PRESENTATIONAL_SPLICE_ACTIONS = {
    "add",
    "choose",
    "complete",
    "create",
    "enter",
    "log",
    "make",
    "open",
    "pick",
    "reach",
    "record",
    "review",
    "select",
    "submit",
    "use",
}
_ARTIFACT_MODIFIER_FOLLOWERS = {
    "account",
    "accounts",
    "action",
    "actions",
    "answer",
    "answers",
    "area",
    "areas",
    "case",
    "cases",
    "change",
    "changes",
    "check",
    "checks",
    "context",
    "contexts",
    "decision",
    "decisions",
    "detail",
    "details",
    "entry",
    "entries",
    "event",
    "events",
    "evidence",
    "fact",
    "facts",
    "field",
    "fields",
    "flow",
    "flows",
    "history",
    "input",
    "inputs",
    "item",
    "items",
    "ledger",
    "ledgers",
    "limit",
    "limits",
    "list",
    "lists",
    "note",
    "notes",
    "option",
    "options",
    "output",
    "outputs",
    "packet",
    "packets",
    "path",
    "paths",
    "plan",
    "plans",
    "proof",
    "proofs",
    "question",
    "questions",
    "readiness",
    "record",
    "records",
    "result",
    "results",
    "route",
    "routes",
    "state",
    "states",
    "status",
    "statuses",
    "step",
    "steps",
    "summary",
    "summaries",
    "view",
    "views",
}


def _has_presentational_action_splice(text: str) -> bool:
    tokens = tuple(token.casefold() for token in _word_tokens(text))
    for index, token in enumerate(tokens[:-1]):
        if token not in _PRESENTATIONAL_VERBS:
            continue
        action = tokens[index + 1]
        if action not in _PRESENTATIONAL_SPLICE_ACTIONS:
            continue
        follower = tokens[index + 2] if index + 2 < len(tokens) else ""
        if _looks_like_artifact_modifier(action, follower):
            continue
        return True
    return False


def _looks_like_artifact_modifier(action: str, follower: str) -> bool:
    if action == "open" and follower.endswith("s"):
        return True
    return follower in _ARTIFACT_MODIFIER_FOLLOWERS


def _has_mixed_adverbial_action_inflection(text: str) -> bool:
    pattern = re.compile(
        r"\b(?P<modifier>[a-z]+ly)\s+"
        r"(?P<finite>adds|captures|chooses|creates|enters|logs|marks|notes|opens|records|reviews|saves|selects|submits|updates)\b"
        r"(?P<tail>[^.!?;]{0,160}\b(?:and|or)\s+"
        r"(?:add|capture|choose|create|enter|log|mark|note|open|record|review|save|select|submit|update)\b)",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        if _looks_like_adjective_noun_action_false_positive(text, match):
            continue
        return True
    return False


def _has_mixed_compact_action_inflection(text: str) -> bool:
    pattern = re.compile(
        r"\b(?:can|must|prove|proves|proving|to)\s+"
        r"(?:choose|connect|create|enter|open|pick|select|start|submit)\b"
        r"[^.!?;]{0,90},\s+(?:and\s+)?"
        r"(?:adds|chooses|connects|creates|drives|enters|keeps|marks|opens|picks|records|saves|selects|starts|submits)\b",
        flags=re.IGNORECASE,
    )
    return bool(pattern.search(text))


def _has_mixed_label_action_coordination(tokens: tuple[str, ...]) -> bool:
    if len(tokens) < 3:
        return False
    for index, token in enumerate(tokens):
        if token not in {"and", "or"}:
            continue
        right_form = coordinated_action_form_after_connector(tokens, index)
        if not right_form:
            continue
        left_form = _left_action_form_before_label_connector(tokens, index)
        if left_form and left_form != right_form:
            return True
    return False


def _left_action_form_before_label_connector(tokens: tuple[str, ...], connector_index: int) -> str:
    first_form = action_token_form(tokens[0])
    if first_form:
        return first_form
    for index in range(connector_index - 1, max(-1, connector_index - 6), -1):
        token = tokens[index]
        if _label_connector_filler(token):
            continue
        form = action_token_form(token)
        if form:
            return form
    return ""


def _label_connector_filler(token: str) -> bool:
    return token in {"then"} or token.endswith("ly")


def _has_saved_destination_result_slop(text: str) -> bool:
    pattern = re.compile(
        r"\b(?:session|entry|record|result|item)\s+to\s+(?:history|log|ledger|journal|timeline|archive)\b",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        if _saved_destination_target_continues_as_component_label(text, match.end()):
            continue
        return True
    return False


def _saved_destination_target_continues_as_component_label(text: str, end_index: int) -> bool:
    tail = str(text or "")[end_index:]
    match = re.match(r"\s+[A-Z][A-Za-z0-9'-]+(?:\s+[A-Z][A-Za-z0-9'-]+){0,3}\b", tail)
    return bool(match)


def _has_possessive_result_list_slop(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:history|record|entry|summary|report|view|timeline|log|ledger)\s+with\s+its\s+",
            text,
            flags=re.IGNORECASE,
        )
    )


def _has_scope_prefix_label_slop(text: str) -> bool:
    return bool(
        re.search(r'\["(?:Optional|Deferred|Future|Later)"\]', text)
        or re.search(r"<br/>(?:Optional|Deferred|Future|Later)\b", text)
        or re.fullmatch(r"(?:Optional|Deferred|Future|Later)", text.strip())
    )


def _looks_like_adjective_noun_action_false_positive(text: str, match: re.Match[str]) -> bool:
    """Avoid treating noun phrases like "daily notes" as finite action clauses."""

    modifier = match.group("modifier").casefold()
    finite = match.group("finite").casefold()
    if modifier not in {
        "daily",
        "hourly",
        "monthly",
        "nightly",
        "quarterly",
        "weekly",
        "yearly",
    }:
        return False
    if finite not in {"logs", "marks", "notes", "records", "reviews"}:
        return False
    tail_after_finite = text[match.end("finite") : match.end()]
    return bool(re.match(r"\s+(?:about|against|as|at|by|for|from|in|into|of|on|to|with|without)\b", tail_after_finite))


def _has_template_slice_prefix(tokens: tuple[str, ...]) -> bool:
    return _has_ordered_terms(tokens, ("start", "with", "this", "implementation", "slice"), max_gap=0)


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


def _has_malformed_relative_clause_split(tokens: tuple[str, ...]) -> bool:
    for index, token in enumerate(tokens[:-1]):
        if token == "can" and tokens[index + 1] in {"that", "who"}:
            return True
        if token == "to" and tokens[index + 1] == "who":
            return True
        if index + 3 >= len(tokens):
            continue
        if token.endswith("s") and tokens[index + 1 : index + 4] == ("are", "meant", "to"):
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


def _word_token_rows(value: str) -> tuple[_WordToken, ...]:
    rows: list[_WordToken] = []
    current: list[str] = []
    token_start = 0
    previous_token_end = 0
    text = str(value or "")
    for index, char in enumerate(text):
        if char.isalnum() or char == "'":
            if not current:
                token_start = index
            current.append(char)
            continue
        if current:
            token = "".join(current).strip("'")
            if token:
                rows.append(
                    _WordToken(
                        token,
                        separator_before=text[previous_token_end:token_start],
                        hyphen_before=token_start > 0 and text[token_start - 1] == "-",
                        hyphen_after=index < len(text) and char == "-",
                    )
                )
                previous_token_end = index
            current = []
    if current:
        token = "".join(current).strip("'")
        if token:
            rows.append(
                _WordToken(
                    token,
                    separator_before=text[previous_token_end:token_start],
                    hyphen_before=token_start > 0 and text[token_start - 1] == "-",
                    hyphen_after=False,
                )
            )
    return tuple(rows)


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


__all__ = [
    "GeneratedCopyFinding",
    "generated_public_copy_findings",
    "generated_public_copy_issues",
    "has_inline_role_casing_drift",
]
