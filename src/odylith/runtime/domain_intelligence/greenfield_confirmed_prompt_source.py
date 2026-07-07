"""Recover clean first-path source text from operator prompt wrappers."""

from __future__ import annotations

from dataclasses import dataclass

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_actor_terms import word_has_actor_role_signal
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import strip_requirement_control_tail
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import strip_trailing_requirement_control_steps
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import REQUEST_REPORTING_VERBS
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import strip_request_reporting_custody_tail
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import word_sense_tail_starts_content_clause


_REQUEST_TITLE_MAX_WORDS = 10
_REQUEST_COMMAND_WORDS = frozenset(
    {
        "build",
        "create",
        "design",
        "draft",
        "generate",
        "make",
        "plan",
        "propose",
        "scaffold",
        "write",
    }
)
_REQUEST_PRODUCT_WORDS = frozenset(
    {
        "app",
        "application",
        "board",
        "builder",
        "dashboard",
        "desk",
        "experience",
        "console",
        "controller",
        "engine",
        "executor",
        "hub",
        "manager",
        "monitor",
        "notebook",
        "plan",
        "platform",
        "planner",
        "portal",
        "product",
        "project",
        "room",
        "service",
        "coach",
        "cockpit",
        "coordination",
        "studio",
        "system",
        "tool",
        "tracker",
        "journal",
        "logbook",
        "workbench",
        "workspace",
    }
)
_REQUEST_HELPER_WORDS = frozenset({"allow", "allows", "enable", "enables", "help", "helps", "let", "lets"})
_REQUEST_ACTOR_PURPOSE_TOKENS = frozenset({"people", "person", "rep", "reps", "staff", "team", "teams", "user", "users"})
_REQUEST_ACTOR_ROLE_SUFFIXES = ("ant", "ants", "ent", "ents", "er", "ers", "ian", "ians", "ist", "ists", "or", "ors", "owner", "owners")
_NON_HUMAN_SUBJECT_TERMS = frozenset(
    {
        "approval",
        "case",
        "claim",
        "decision",
        "evidence",
        "finding",
        "handoff",
        "note",
        "notes",
        "proof",
        "recommendation",
        "record",
        "report",
        "result",
        "review",
        "state",
        "status",
        "summary",
        "view",
        "workflow",
    }
)
_REQUEST_LEAD_CONNECTORS = ("where", "that", "who", "so", "for", "to")
_PATH_GRANT_PATH_MODIFIERS = frozenset(
    {
        "a",
        "an",
        "the",
        "clear",
        "complete",
        "end-to-end",
        "first",
        "full",
        "governed",
        "guided",
        "one",
        "review-ready",
        "single",
    }
)
_DIRECT_TITLE_BOUNDARY_CONNECTORS = frozenset({"where", "that", "who", "so"})
_ORIGINAL_INTENT_BOUNDARY_HEADINGS = frozenset(
    {
        "next step",
        "confirmed cli after confirmation",
        "visible format contract",
        "write in chat",
        "do not",
    }
)
_RELEASE_PROOF_ACTION_WORDS = frozenset(
    {
        "complete",
        "completes",
        "completed",
        "pass",
        "passes",
        "prove",
        "proves",
        "proved",
        "succeed",
        "succeeds",
        "succeeded",
    }
)
@dataclass(frozen=True)
class PromptIntentSource:
    """Operator prompt interpretation before confirmed-intent recovery."""

    title: str
    first_path: str
    command_led: bool
    actor: str = ""


def prompt_first_path_source(value: str) -> str:
    """Return product-path text without a host command or product wrapper."""

    return prompt_intent_source(value).first_path


def prompt_project_title_source(value: str) -> str:
    """Return the product noun phrase from an operator request."""

    return prompt_intent_source(value).title


def prompt_intent_source(value: str) -> PromptIntentSource:
    """Return shared title and first-path sources for thin prompt recovery."""

    text = _strip_trailing_operator_instruction_sentences(
        clean_markdown_text(_operator_original_intent_block(value) or value).strip(" .")
    )
    words = _request_words(text)
    start, command_led = _request_content_start(words)
    grant_actor, grant_first_path = _path_grant_actor_action(text)
    workflow_actor, workflow_first_path = _workflow_where_actor_action(text)
    actor, actor_led_first_path = _actor_led_relative_clause(text)
    first_path_source = grant_first_path or workflow_first_path or actor_led_first_path or _first_path_source_from_text(text)
    return PromptIntentSource(
        title=_project_title_source_from_words(words, start=start, command_led=command_led),
        first_path=_strip_release_proof_tail(first_path_source),
        command_led=command_led,
        actor=grant_actor or workflow_actor or actor,
    )


def _first_path_source_from_text(value: str) -> str:
    raw_text = _strip_trailing_operator_instruction_sentences(clean_markdown_text(value).strip(" ."))
    text = _strip_operator_request_wrapper(raw_text)
    grant_actor, grant_first_path = _path_grant_actor_action(raw_text)
    if grant_actor and word_count(grant_first_path) >= 8 and _looks_like_recoverable_first_path(grant_first_path):
        return _strip_release_proof_tail(grant_first_path)
    workflow_actor, workflow_first_path = _workflow_where_actor_action(raw_text)
    if workflow_actor and word_count(workflow_first_path) >= 8 and _looks_like_recoverable_first_path(workflow_first_path):
        return _strip_release_proof_tail(workflow_first_path)
    actor_led_candidate = _actor_led_relative_clause_source(raw_text)
    if word_count(actor_led_candidate) >= 8 and _looks_like_recoverable_first_path(actor_led_candidate):
        return _strip_release_proof_tail(actor_led_candidate)
    release_candidate = _release_action_sentence_source(raw_text) or _release_action_sentence_source(text)
    if word_count(release_candidate) >= 8 and _looks_like_recoverable_first_path(release_candidate):
        return _strip_release_proof_tail(release_candidate)
    for marker in ("where", "that", "for", "who"):
        candidate = _tail_after_word(raw_text, marker)
        if not candidate:
            continue
        candidate = _strip_operator_request_wrapper(candidate)
        if word_count(candidate) >= 8 and _looks_like_recoverable_first_path(candidate):
            return _strip_release_proof_tail(candidate)
    if _looks_like_recoverable_first_path(text):
        return _strip_release_proof_tail(text)
    for marker in ("so",):
        candidate = _tail_after_word(raw_text, marker)
        if not candidate:
            continue
        candidate = _strip_operator_request_wrapper(candidate)
        if word_count(candidate) >= 8 and _looks_like_recoverable_first_path(candidate):
            return _strip_release_proof_tail(candidate)
    return _strip_release_proof_tail(text)


def _request_content_start(words: list[str]) -> tuple[int, bool]:
    command_led = len(words) >= 3 and words[0].casefold() in _REQUEST_COMMAND_WORDS
    start = 1 if command_led else 0
    if start < len(words) and words[start].casefold() in {"a", "an", "the"}:
        start += 1
    if command_led:
        start = _skip_proposal_wrapper(words, start)
    return start, command_led


def _project_title_source_from_words(words: list[str], *, start: int, command_led: bool) -> str:
    if start >= len(words):
        return ""
    lowered = [word.casefold().strip(",:;") for word in words]
    for index in range(start + 1, len(words)):
        connector = lowered[index]
        if connector not in _REQUEST_LEAD_CONNECTORS:
            continue
        if not command_led and connector not in _DIRECT_TITLE_BOUNDARY_CONNECTORS:
            tail = " ".join(words[index + 1 :]).strip(" .")
            if not _looks_like_recoverable_first_path(tail):
                continue
        lead = _lead_before_sentence_boundary(words[start:index]) or words[start:index]
        if _looks_like_product_title_phrase(lead):
            return " ".join(lead).strip(" .")
        tail = " ".join(words[index + 1 :]).strip(" .")
        if command_led and _looks_like_explicit_title_before_workflow_context(lead, tail=tail):
            return " ".join(lead).strip(" .")
        if command_led and _looks_like_target_focus_phrase(lead, tail=tail):
            return " ".join(lead).strip(" .")
    sentence_title = _project_title_before_sentence_boundary(words, start=start, command_led=command_led)
    if sentence_title:
        return sentence_title
    lead = words[start:]
    if _looks_like_product_title_phrase(lead):
        return " ".join(lead).strip(" .")
    return ""


def _lead_before_sentence_boundary(words: list[str]) -> list[str]:
    lead: list[str] = []
    for word in words:
        cleaned = str(word or "").strip()
        if not cleaned:
            continue
        lead.append(cleaned.strip(".,:;"))
        if cleaned.endswith((".", "!", "?")):
            break
    return lead if lead and len(lead) < len(words) else []


def _operator_original_intent_block(value: str) -> str:
    rows = str(value or "").splitlines()
    collected: list[str] = []
    collecting = False
    for row in rows:
        key = _heading_key(row)
        if collecting and key in _ORIGINAL_INTENT_BOUNDARY_HEADINGS:
            break
        if collecting:
            collected.append(row)
            continue
        if key == "original user intent":
            collecting = True
            if ":" in row:
                tail = row.split(":", 1)[1].strip()
                if tail:
                    collected.append(tail)
    return clean_markdown_text("\n".join(collected)).strip(" .")


def _heading_key(value: str) -> str:
    text = str(value or "").strip()
    while text and text[0] in "#-* ":
        text = text[1:].strip()
    return text.rstrip(":").strip().casefold()


def _project_title_before_sentence_boundary(words: list[str], *, start: int, command_led: bool = False) -> str:
    lead: list[str] = []
    tail_start = start
    for offset, raw in enumerate(words[start:], start=start):
        tail_start = offset + 1
        token = raw.strip()
        cleaned = token.strip(".,:;")
        if cleaned.casefold() in _REQUEST_LEAD_CONNECTORS:
            return ""
        if cleaned:
            lead.append(cleaned)
        if token.endswith((".", "!", "?")):
            break
    if _looks_like_product_title_phrase(lead):
        return " ".join(lead).strip(" .")
    if command_led and _looks_like_explicit_title_before_workflow_context(
        lead,
        tail=" ".join(words[tail_start:]).strip(" ."),
    ):
        return " ".join(lead).strip(" .")
    if command_led and _looks_like_target_focus_phrase(lead, tail=" ".join(words[tail_start:]).strip(" .")):
        return " ".join(lead).strip(" .")
    return ""


def _skip_proposal_wrapper(words: list[str], start: int) -> int:
    index = start
    saw_request_wrapper = False
    while index < len(words) and words[index].casefold().strip(",:;") in {"greenfield", "new", "product-first"}:
        saw_request_wrapper = True
        index += 1
    if index < len(words) and words[index].casefold().strip(",:;") in {"proposal", "product"}:
        index += 1
    elif (
        index < len(words)
        and words[index].casefold().strip(",:;") == "project"
        and (
            saw_request_wrapper
            or (index + 1 < len(words) and words[index + 1].casefold().strip(",:;") == "for")
        )
    ):
        index += 1
    if index < len(words) and words[index].casefold().strip(",:;") == "for":
        index += 1
    if (
        index + 1 < len(words)
        and words[index].casefold().strip(",:;") == "product"
        and words[index + 1].casefold().strip(",:;") == "for"
    ):
        index += 2
    if index < len(words) and words[index].casefold().strip(",:;") in {"a", "an", "the"}:
        index += 1
    return index


def _tail_after_word(value: str, marker: str) -> str:
    words = _request_words(value)
    for index, word in enumerate(words[:-1]):
        if word.casefold().strip(".,:;") != marker:
            continue
        return " ".join(words[index + 1 :]).strip(" .")
    return ""


def _actor_led_relative_clause_source(value: str) -> str:
    _actor, first_path = _actor_led_relative_clause(value)
    return first_path


def _workflow_where_actor_action(value: str) -> tuple[str, str]:
    words = _request_words(value)
    lowered = [_word_key(word) for word in words]
    for marker_index, token in enumerate(lowered[:-3]):
        if token != "where":
            continue
        tail_words = words[marker_index + 1 :]
        for action_index in range(min(len(tail_words), 5), 0, -1):
            actor_words = tail_words[:action_index]
            action_words = tail_words[action_index:]
            actor_words, action_words = _trim_actor_action_split(actor_words, action_words)
            if not action_words or not _looks_like_actor_split_left(actor_words, allow_bounded_workflow_phrase=True):
                continue
            action_source = _smooth_request_first_path_clause(" ".join(action_words))
            if not _looks_like_direct_transformation_workflow_action(action_source):
                continue
            if not looks_like_action_clause(action_source):
                continue
            action = base_action_clause(action_source, force_leading_finite=True).strip(" .") or action_source
            if action and _looks_like_recoverable_first_path(action):
                actor = _strip_leading_actor_article(" ".join(actor_words))
                return actor, f"{actor} {action}".strip(" .")
    return "", ""


def _path_grant_actor_action(value: str) -> tuple[str, str]:
    words = _request_words(value)
    lowered = [_word_key(word) for word in words]
    for grant_index, token in enumerate(lowered[:-4]):
        if token not in {"give", "gives", "grant", "grants", "provide", "provides"}:
            continue
        actor, action = _path_grant_tail_parts(words[grant_index + 1 :])
        if actor and action:
            return actor, f"{actor} {action}".strip(" .")
    return "", ""


def _path_grant_tail_parts(words: list[str]) -> tuple[str, str]:
    lowered = [_word_key(word) for word in words]
    for path_index, token in enumerate(lowered[:-1]):
        if token != "path":
            continue
        actor_stop = _path_grant_actor_stop(words, path_index)
        if actor_stop <= 0:
            continue
        actor_words = words[:actor_stop]
        if not _looks_like_actor_purpose_left(actor_words):
            continue
        action_start = path_index + 1
        if action_start < len(words) and _word_key(words[action_start]) == "to":
            action_start += 1
        action_words = words[action_start:]
        if not action_words:
            continue
        action_source = _smooth_request_first_path_clause(" ".join(action_words))
        action = base_action_clause(action_source, force_leading_finite=True).strip(" .") or action_source
        if action and _looks_like_recoverable_first_path(action):
            return _strip_leading_actor_article(" ".join(actor_words)), action
    return "", ""


def _path_grant_actor_stop(words: list[str], path_index: int) -> int:
    stop = path_index
    while stop > 0 and _word_key(words[stop - 1]) in _PATH_GRANT_PATH_MODIFIERS:
        stop -= 1
    return stop


def _actor_led_relative_clause(value: str) -> tuple[str, str]:
    words = _request_words(value)
    lowered = [word.casefold().strip(".,:;") for word in words]
    for for_index, token in enumerate(lowered[:-3]):
        if token != "for":
            continue
        for connector_index in range(for_index + 2, len(words) - 1):
            if lowered[connector_index] not in {"that", "who"}:
                continue
            raw_tail_words = words[connector_index + 1 :]
            embedded_actor, embedded_action = _helper_relative_actor_action(raw_tail_words)
            if embedded_actor and embedded_action:
                return embedded_actor, f"{embedded_actor} {embedded_action}".strip(" .")
            actor_words = _actor_role_suffix(words[for_index + 1 : connector_index])
            actor_words, moved_action_words = _trim_actor_action_split(actor_words, [])
            tail_words = raw_tail_words
            if moved_action_words:
                tail_words = [*moved_action_words, *tail_words]
            if not actor_words or not tail_words or not _looks_like_actor_purpose_left(actor_words):
                continue
            use_actor, use_action = _use_to_actor_action(tail_words)
            if use_actor and use_action:
                return use_actor, f"{use_actor} {use_action}".strip(" .")
            action = base_action_clause(_smooth_request_first_path_clause(" ".join(tail_words)), force_leading_finite=True)
            if action:
                actor = " ".join(actor_words).strip(" .")
                connector = lowered[connector_index]
                if connector == "who":
                    return actor, f"{actor} {connector} {action}".strip(" .")
                return actor, f"{actor} {action}".strip(" .")
    return "", ""


def _actor_role_suffix(words: list[str]) -> list[str]:
    """Prefer the role-bearing suffix when a product title wraps a for-who clause."""

    for index, word in enumerate(words[:-1]):
        if _word_key(word) != "for":
            continue
        suffix = words[index + 1 :]
        if suffix and _looks_like_actor_purpose_left(suffix):
            return suffix
    return words


def _trim_actor_action_split(actor_words: list[str], action_words: list[str]) -> tuple[list[str], list[str]]:
    words = list(actor_words)
    tokens = [_word_key(word) for word in words]
    for index, token in enumerate(tokens[1:], start=1):
        if token in {"who", "that", "where"}:
            break
        if not (
            _looks_like_actor_purpose_left(words[:index])
            or _looks_like_bounded_workflow_actor_phrase(words[:index])
        ):
            continue
        action_tail = " ".join(words[index:]).strip(" .")
        if looks_like_action_clause(action_tail):
            return words[:index], [*words[index:], *action_words]
    return actor_words, action_words


def _use_to_actor_action(words: list[str]) -> tuple[str, str]:
    for use_index, word in enumerate(words[:-2]):
        if _word_key(word) not in {"use", "uses", "used"} or _word_key(words[use_index + 1]) != "to":
            continue
        actor_words = words[:use_index]
        action_words = words[use_index + 2 :]
        if not actor_words or not action_words or not _looks_like_use_to_actor_left(actor_words):
            continue
        action = base_action_clause(_smooth_request_first_path_clause(" ".join(action_words)), force_leading_finite=True)
        if action:
            return _strip_leading_actor_article(" ".join(actor_words)), action
    return "", ""


def _looks_like_use_to_actor_left(words: list[str]) -> bool:
    if _looks_like_actor_purpose_left(words):
        return True
    tail = _actor_purpose_tail(words)
    if not tail or len(tail) > 4:
        return False
    last = tail[-1].casefold().strip(".,:;")
    return len(last) > 3 and last.endswith("s") and last not in _REQUEST_PRODUCT_WORDS


def _looks_like_actor_split_left(words: list[str], *, allow_bounded_workflow_phrase: bool = False) -> bool:
    if _looks_like_non_human_subject(words):
        return False
    if not _looks_like_actor_purpose_left(words) and not (
        allow_bounded_workflow_phrase and _looks_like_bounded_workflow_actor_phrase(words)
    ):
        return False
    tokens = [_word_key(word) for word in words if _word_key(word)]
    if any(any(mark in str(word) for mark in (",", ";", ":")) for word in words):
        return False
    if any(token in {"and", "or", "then"} for token in tokens):
        return False
    return not looks_like_action_clause(" ".join(words))


def _looks_like_non_human_subject(words: list[str]) -> bool:
    content = [_word_key(word) for word in words if _word_key(word)]
    if not content:
        return False
    if _looks_like_actor_purpose_left(words):
        return False
    return bool(set(content) & _NON_HUMAN_SUBJECT_TERMS)


def _looks_like_bounded_workflow_actor_phrase(words: list[str]) -> bool:
    content = [_word_key(word) for word in words if _word_key(word)]
    while content and content[0] in {"a", "an", "the", "one"}:
        content = content[1:]
    if not 2 <= len(content) <= 4:
        return False
    if any(token in {"and", "or", "then"} for token in content):
        return False
    if any(token in _REQUEST_COMMAND_WORDS for token in content):
        return False
    if set(content) <= _REQUEST_PRODUCT_WORDS:
        return False
    if looks_like_action_clause(" ".join(content)):
        return False
    return any(token not in {"case", "context", "record", "request", "review", "workflow"} for token in content)


def _looks_like_direct_transformation_workflow_action(value: str) -> bool:
    words = _request_words(value)
    if not words:
        return False
    action = _word_key(words[0])
    if action in {"capture", "captures", "record", "records", "register", "registers"}:
        return len(first_path_model(value).steps) == 1
    if action in {"convert", "converts", "transform", "transforms", "translate", "translates", "turn", "turns"}:
        return " into " in f" {clean_markdown_text(value).casefold()} "
    model = first_path_model(value)
    return looks_like_action_clause(value) and len(model.steps) == 1 and bool(
        model.material_action or model.visible_outcome
    )


def _helper_relative_actor_action(words: list[str]) -> tuple[str, str]:
    if len(words) < 3 or _word_key(words[0]) not in _REQUEST_HELPER_WORDS:
        return "", ""
    tail_words = words[1:]
    if tail_words and _word_key(tail_words[0]) == "to":
        tail_words = tail_words[1:]
    for split_index in range(min(len(tail_words), 5), 0, -1):
        actor_words = tail_words[:split_index]
        action_words = tail_words[split_index:]
        if not action_words or not _looks_like_actor_split_left(actor_words, allow_bounded_workflow_phrase=True):
            continue
        action_source = _smooth_request_first_path_clause(" ".join(action_words))
        if not looks_like_action_clause(action_source):
            continue
        action = base_action_clause(action_source, force_leading_finite=True)
        if action:
            return _strip_leading_actor_article(" ".join(actor_words)), action
    return "", ""


def _strip_leading_actor_article(value: str) -> str:
    words = _request_words(value)
    if words and _word_key(words[0]) in {"a", "an", "the"}:
        words = words[1:]
    return " ".join(words).strip(" .")


def _strip_operator_request_wrapper(value: str) -> str:
    text = clean_markdown_text(value).strip(" .")
    if not text:
        return ""
    for candidate in _operator_request_tail_candidates(text):
        smoothed = _smooth_request_first_path_clause(_strip_leading_helper_word(candidate))
        if word_count(smoothed) >= 4 and _looks_like_recoverable_first_path(smoothed):
            return smoothed
    return _smooth_request_first_path_clause(_strip_leading_helper_word(text))


def _release_action_sentence_source(value: str) -> str:
    for sentence in _sentence_fragments(value):
        candidate = _strip_release_helper_prefix(sentence)
        if candidate != clean_markdown_text(sentence).strip(" ."):
            return candidate
    return ""


def _sentence_fragments(value: str) -> list[str]:
    words = _request_words(value)
    rows: list[str] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if word.endswith((".", "!", "?")):
            rows.append(" ".join(current).strip(" ."))
            current = []
    if current:
        rows.append(" ".join(current).strip(" ."))
    return [row for row in rows if row]


def _strip_trailing_operator_instruction_sentences(value: str) -> str:
    rows = _sentence_fragments(value)
    if len(rows) <= 1:
        return clean_markdown_text(value).strip(" .")
    kept = list(rows)
    while len(kept) > 1 and _looks_like_trailing_operator_instruction(kept[-1]):
        kept.pop()
    return clean_markdown_text(". ".join(kept)).strip(" .")


def _looks_like_trailing_operator_instruction(value: str) -> bool:
    text = clean_markdown_text(value).strip(" .")
    if not text:
        return False
    normalized = _strip_leading_instruction_adverb(text).casefold()
    words = [_word_key(word) for word in _request_words(normalized)]
    if not words:
        return False
    command = words[0]
    control_text = " ".join(words)
    if normalized.startswith(("do not ", "don't ", "make sure ", "ensure ")):
        return True
    if command not in _REQUEST_COMMAND_WORDS | {"run", "execute", "install", "commit", "push", "edit", "reject"}:
        return False
    control_terms = {
        "after confirmation",
        "artifact",
        "artifacts",
        "command",
        "commands",
        "confirm",
        "greenfield",
        "implementation plan",
        "intent file",
        "next step",
        "post confirm",
        "post-confirm",
        "proposal",
    }
    return any(term in normalized or term in control_text for term in control_terms)


def _strip_leading_instruction_adverb(value: str) -> str:
    words = _request_words(value)
    if words and _word_key(words[0]) in {"also", "then", "next", "please"}:
        return " ".join(words[1:]).strip(" .")
    return clean_markdown_text(value).strip(" .")


def _strip_release_helper_prefix(value: str) -> str:
    words = _request_words(value)
    lowered = [_word_key(word) for word in words]
    for index, token in enumerate(lowered):
        if token not in _REQUEST_HELPER_WORDS:
            continue
        prefix = set(lowered[:index])
        if not (prefix & {"first", "product", "release", "should", "version"}):
            continue
        tail = words[index + 1 :]
        if tail and tail[0].casefold() == "to":
            tail = tail[1:]
        return _smooth_request_first_path_clause(" ".join(tail))
    return clean_markdown_text(value).strip(" .")


def _operator_request_tail_candidates(value: str) -> tuple[str, ...]:
    words = _request_words(value)
    if len(words) < 3:
        return ()
    lowered = [word.casefold() for word in words]
    start = 1 if lowered[0] in _REQUEST_COMMAND_WORDS else 0
    if start < len(lowered) and lowered[start] in {"a", "an", "the"}:
        start += 1
    if start >= len(words):
        return ()
    command_led = lowered[0] in _REQUEST_COMMAND_WORDS
    candidates: list[str] = []
    lead_words = lowered[start:]
    for index in range(start, len(words) - 1):
        connector = lowered[index].strip(",:;")
        if connector not in _REQUEST_LEAD_CONNECTORS:
            continue
        lead = lead_words[: max(0, index - start)]
        if not command_led and not (set(lead) & _REQUEST_PRODUCT_WORDS):
            continue
        tail = " ".join(words[index + 1 :]).strip(" ,.;:")
        if tail:
            candidates.append(tail)
    if command_led:
        candidates.append(" ".join(words[start:]))
    return tuple(dict.fromkeys(candidates))


def _strip_leading_helper_word(value: str) -> str:
    words = _request_words(value)
    if len(words) < 2:
        return clean_markdown_text(value).strip(" .")
    if words[0].casefold() not in _REQUEST_HELPER_WORDS:
        return clean_markdown_text(value).strip(" .")
    tail_words = words[1:]
    if tail_words and tail_words[0].casefold() == "to":
        tail_words = tail_words[1:]
    return " ".join(tail_words).strip(" .")


def _smooth_request_first_path_clause(value: str) -> str:
    normalized = _normalize_request_reporting_product_clauses(value)
    words = _request_words(strip_trailing_requirement_control_steps(normalized))
    if not words:
        return ""
    while words and words[0].casefold() == "to":
        words = words[1:]
    words = _drop_relative_use_to_action(words)
    if len(words) < 3:
        return " ".join(words).strip(" .")
    smoothed: list[str] = []
    for index, word in enumerate(words):
        token = word.casefold().strip(".,:;")
        next_word = words[index + 1] if index + 1 < len(words) else ""
        previous = smoothed[-1].casefold().strip(".,:;") if smoothed else ""
        if (
            token == "to"
            and previous in _REQUEST_HELPER_WORDS
            and next_word
            and looks_like_action_clause(f"{next_word} result")
        ):
            smoothed.append("can")
            continue
        if (
            token == "to"
            and next_word
            and looks_like_action_clause(f"{next_word} result")
            and _looks_like_actor_purpose_left(smoothed)
        ):
            smoothed.append("can")
            continue
        smoothed.append(word)
    return " ".join(smoothed).strip(" .")


def _normalize_request_reporting_product_clauses(value: str) -> str:
    rows = _sentence_fragments(clean_markdown_text(value).strip(" ."))
    if not rows:
        return ""
    normalized: list[str] = []
    for row in rows:
        product_clause = _request_reporting_product_clause(row)
        if product_clause and any(_looks_like_recoverable_first_path(previous) for previous in normalized):
            continue
        normalized.append(product_clause or row)
    return ". ".join(row for row in normalized if row).strip(" .")


def _request_reporting_product_clause(value: str) -> str:
    words = _request_words(value)
    if len(words) < 5:
        return ""
    lowered = [_word_key(word) for word in words]
    subject_index = 1 if lowered[0] in {"a", "an", "the", "this", "that"} else 0
    if subject_index + 2 >= len(lowered):
        return ""
    if lowered[subject_index] not in {"instruction", "instructions", "prompt", "request"}:
        return ""
    if lowered[subject_index + 1] not in REQUEST_REPORTING_VERBS:
        return ""
    tail_words = words[subject_index + 2 :]
    if tail_words and _word_key(tail_words[0]) == "that":
        tail_words = tail_words[1:]
    tail_keys = [_word_key(word) for word in tail_words]
    if not word_sense_tail_starts_content_clause(tail_keys):
        return ""
    return strip_request_reporting_custody_tail(clean_markdown_text(" ".join(tail_words))).strip(" .")


def _drop_relative_use_to_action(words: list[str]) -> list[str]:
    for index, word in enumerate(words[:-2]):
        token = word.casefold().strip(".,:;")
        next_token = words[index + 1].casefold().strip(".,:;")
        if token not in {"use", "uses", "used"} or next_token != "to":
            continue
        actor_words = words[:index]
        action_words = words[index + 2 :]
        if not actor_words or not action_words:
            continue
        if looks_like_action_clause(" ".join(action_words)):
            return [*actor_words, *action_words]
    return words


def _looks_like_actor_purpose_left(words: list[str]) -> bool:
    tail = _actor_purpose_tail(words)
    if not tail:
        return False
    last = tail[-1].casefold().strip(".,:;")
    singular = last[:-1] if last.endswith("s") else last
    return (
        last in _REQUEST_ACTOR_PURPOSE_TOKENS
        or singular in _REQUEST_ACTOR_PURPOSE_TOKENS
        or word_has_actor_role_signal(last)
        or word_has_actor_role_signal(singular)
        or any(last.endswith(suffix) or singular.endswith(suffix) for suffix in _REQUEST_ACTOR_ROLE_SUFFIXES)
    )


def _actor_purpose_tail(words: list[str]) -> list[str]:
    start = 0
    for index, word in enumerate(words):
        token = word.casefold().strip(".,:;")
        if token in {"and", "or", "then"}:
            start = index + 1
    return [word for word in words[start:] if word.strip(".,:;")]


def _strip_release_proof_tail(value: str) -> str:
    words = _request_words(value)
    if len(words) < 5:
        return strip_requirement_control_tail(strip_trailing_requirement_control_steps(clean_markdown_text(value).strip(" .")))
    lowered = [_word_key(word) for word in words]
    for index, word in enumerate(lowered[:-2]):
        if word not in {"before", "until", "when"}:
            continue
        if lowered[index + 1] not in {"release", "version"}:
            continue
        action_index = index + 2
        if action_index < len(words) and _looks_like_release_selector(words[action_index]):
            action_index += 1
        if _release_proof_tail_starts(lowered[action_index:]):
            return strip_requirement_control_tail(strip_trailing_requirement_control_steps(" ".join(words[:index]).strip(" ,.;:")))
    return strip_requirement_control_tail(strip_trailing_requirement_control_steps(clean_markdown_text(value).strip(" .")))


def _release_proof_tail_starts(words: list[str]) -> bool:
    if not words:
        return False
    if words[0] in _RELEASE_PROOF_ACTION_WORDS:
        return True
    return len(words) >= 2 and words[0] == "is" and words[1] in {"complete", "completed", "ready"}


def _looks_like_release_selector(value: str) -> bool:
    token = str(value or "").strip(".,:;")
    return bool(token) and all(char.isalnum() or char in "._-" for char in token)


def _word_key(value: str) -> str:
    return str(value or "").casefold().strip(".,:;")


def _request_words(value: str) -> list[str]:
    return [
        word.strip("()[]{}\"'")
        for word in clean_markdown_text(value).replace("/", " ").split()
        if word.strip("()[]{}\"'")
    ]


def _looks_like_product_title_phrase(words: list[str]) -> bool:
    if not words or len(words) > _REQUEST_TITLE_MAX_WORDS:
        return False
    lowered = [word.casefold().strip(".,:;") for word in words]
    if set(lowered) <= {"new", "simple", "small", "greenfield"} | _REQUEST_PRODUCT_WORDS:
        return False
    return bool(set(lowered) & _REQUEST_PRODUCT_WORDS) or any(word.isupper() and len(word) <= 6 for word in words)


def _looks_like_target_focus_phrase(words: list[str], *, tail: str) -> bool:
    if len(words) < 2 or len(words) > _REQUEST_TITLE_MAX_WORDS:
        return False
    lowered = [word.casefold().strip(".,:;") for word in words]
    if set(lowered) <= {"new", "simple", "small", "greenfield"}:
        return False
    if set(lowered) & _REQUEST_COMMAND_WORDS:
        return False
    if set(lowered) & set(_REQUEST_LEAD_CONNECTORS):
        return False
    text = " ".join(words).strip(" .")
    if looks_like_action_clause(text):
        return False
    return _has_recoverable_first_path_context(tail)


def _looks_like_explicit_title_before_workflow_context(words: list[str], *, tail: str) -> bool:
    if len(words) < 2 or len(words) > _REQUEST_TITLE_MAX_WORDS:
        return False
    lowered = [word.casefold().strip(".,:;") for word in words]
    if set(lowered) <= {"new", "simple", "small", "greenfield"} | _REQUEST_PRODUCT_WORDS:
        return False
    if set(lowered) & set(_REQUEST_LEAD_CONNECTORS):
        return False
    return _has_recoverable_first_path_context(tail)


def _has_recoverable_first_path_context(value: str) -> bool:
    text = clean_markdown_text(value).strip(" .")
    if not text:
        return False
    if _looks_like_recoverable_first_path(text):
        return True
    source = _first_path_source_from_text(text)
    return bool(
        source
        and source.casefold() != text.casefold()
        and word_count(source) >= 8
        and _looks_like_recoverable_first_path(source)
    )


def _looks_like_recoverable_first_path(value: str) -> bool:
    model = first_path_model(value)
    return len(model.steps) >= 2 or bool(model.material_action or model.visible_outcome)


__all__ = ["PromptIntentSource", "prompt_first_path_source", "prompt_intent_source", "prompt_project_title_source"]
