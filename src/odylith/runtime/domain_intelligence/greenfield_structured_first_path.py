"""Compile typed prompt fields into a validated ordered first-path contract."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from dataclasses import replace
import re
from typing import Any

from odylith.runtime.common.prose_grammar import action_token_form
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import base_gerund_clause
from odylith.runtime.common.prose_grammar import past_action_verb
from odylith.runtime.common.prose_grammar import strip_leading_action_modal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import word_has_actor_role_signal
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import sentence_fragments
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text
from odylith.runtime.domain_intelligence.greenfield_text import clean_text


_PATH_START_RE = re.compile(
    r"^(?:(?:the\s+)?first\s+path|it)?\s*(?:is\s+fixed\s*)?(?::\s*)?"
    r"(?:begins?|starts?)\s+with\s*(?P<start>.*)$",
    flags=re.IGNORECASE,
)
_PATH_CONTROL_RE = re.compile(
    r"^(?:(?:the\s+)?first\s+path|it)\s+is\s+fixed\s*$",
    flags=re.IGNORECASE,
)
_PATH_NOMINAL_RESULT_RE = re.compile(
    r"^(?:the\s+)?first(?:\s+[A-Za-z0-9'-]+){0,3}\s+path\s+is\s+(?P<result>.+)$",
    flags=re.IGNORECASE,
)
_NEGATED_SCOPE_RE = re.compile(
    r"(?:\b(?:not|never|cannot|can't|won't|shouldn't|mustn't)\b|"
    r"\b(?:forbidden|prohibited|barred|disallowed)\s+to\b|"
    r"\bnot\s+(?:allowed|permitted)\s+to\b)",
    flags=re.IGNORECASE,
)
_OUTPUT_ACTION_RE = re.compile(
    r"^(?:create|creates|export|exports|generate|generates|issue|issues|prepare|prepares|"
    r"produce|produces|provide|provides|publish|publishes|receive|receives|record|records|"
    r"release|releases|return|returns|save|saves|show|shows|display|displays|get|gets)\b",
    flags=re.IGNORECASE,
)
_STRUCTURED_LABEL_RE = re.compile(
    r"(?:^|[,;{])\s*[\"']?(?:actor|action|first\s+path|output)[\"']?\s*:",
    flags=re.IGNORECASE,
)
_IDENTITY_ARTICLES = frozenset({"a", "an", "the"})
_IDENTITY_CONNECTORS = frozenset({"and", "finally", "then", "they"})
_PASSIVE_AUXILIARIES = frozenset({"are", "be", "been", "being", "is", "was", "were"})


@dataclass(frozen=True)
class StructuredPathEvent:
    """One source-scoped event accepted from a typed prompt field."""

    kind: str
    source_text: str
    action_text: str
    identity: tuple[str, ...]
    valid: bool
    render: bool = True
    rendered_text: str = ""


@dataclass(frozen=True)
class StructuredFirstPathContract:
    """Typed first-path facts plus their concise public projection."""

    actor: str
    actor_is_human: bool
    events: tuple[StructuredPathEvent, ...]
    text: str
    invalid_reasons: tuple[str, ...] = ()
    explicit_output: bool = False

    @property
    def primary_actor_action(self) -> str:
        """Return the first validated user-owned action in source order."""

        return next(
            (
                event.action_text
                for event in self.events
                if event.kind in {"action", "start"} and event.valid
            ),
            "",
        )

    @property
    def primary_state_action(self) -> str:
        """Return the first validated mutation action, excluding a path-entry step."""

        action = next(
            (
                event.action_text
                for event in self.events
                if event.kind == "action" and event.valid
            ),
            self.primary_actor_action,
        )
        return _without_system_context(action)

    @property
    def actor_subject(self) -> str:
        """Return the grammatical subject for this contract's typed actor."""

        return structured_actor_subject(self.actor)

    @property
    def actor_label(self) -> str:
        """Return a stable UI label without sentence-only appositive punctuation."""

        return self.actor_subject.rstrip(" ,")

    @property
    def actor_aliases(self) -> tuple[str, ...]:
        """Return source-safe aliases that can own additional ordered path rows."""

        return structured_actor_aliases(self.actor)

    def actor_owned_path_from_rows(self, rows: Sequence[str]) -> str:
        """Merge ordered rows only when the typed actor owns them and all events remain covered."""

        owned = [row.strip(" .") for row in rows if self._actor_owns_row(row)]
        candidate = ". ".join(dict.fromkeys(row for row in owned if row))
        if not candidate:
            return ""
        candidate_terms = set(re.findall(r"[A-Za-z0-9][A-Za-z0-9'/-]*", candidate.casefold()))
        required_events = tuple(event for event in self.events if event.render and event.valid)
        if not all(set(event.identity) <= candidate_terms for event in required_events):
            return ""
        model = first_path_model(candidate)
        if not model.material_action or not model.visible_outcome:
            return ""
        return candidate

    def actor_handoff_path_from_rows(self, rows: Sequence[str], *, actor: str) -> str:
        """Preserve an actor entry followed by ordered product or system handoff rows."""

        aliases = structured_actor_aliases(actor)
        start = next(
            (
                index
                for index, row in enumerate(rows)
                if _row_starts_with_actor_alias(row, aliases=aliases)
            ),
            -1,
        )
        if start < 0:
            return ""
        required_events = tuple(event for event in self.events if event.render and event.valid)
        output_events = tuple(
            event
            for event in self.events
            if self.explicit_output and event.kind == "output" and event.valid
        )
        selected: list[str] = []
        candidate = ""
        for row in rows[start:]:
            path_row = row.strip(" .")
            if not path_row or not first_path_model(path_row).material_action:
                continue
            if path_row not in selected:
                selected.append(path_row)
            candidate = ". ".join(selected)
            candidate_terms = set(re.findall(r"[A-Za-z0-9][A-Za-z0-9'/-]*", candidate.casefold()))
            model = first_path_model(candidate)
            output_covered = bool(output_events) and all(
                set(event.identity) <= candidate_terms for event in output_events
            )
            if output_covered:
                if all(set(event.identity) <= candidate_terms for event in required_events):
                    break
                return ""
        if not candidate:
            return ""
        model = first_path_model(candidate)
        candidate_terms = set(re.findall(r"[A-Za-z0-9][A-Za-z0-9'/-]*", candidate.casefold()))
        return candidate if (
            model.material_action
            and model.visible_outcome
            and all(set(event.identity) <= candidate_terms for event in required_events)
        ) else ""

    def _actor_owns_row(self, value: str) -> bool:
        return _row_starts_with_actor_alias(value, aliases=self.actor_aliases)

    @property
    def output_only(self) -> bool:
        """Return whether typed evidence supplies a result without a path action."""

        return bool(self.events) and all(event.kind == "output" for event in self.events)

    @property
    def complete(self) -> bool:
        actions = tuple(event for event in self.events if event.kind in {"action", "start"})
        outputs = tuple(event for event in self.events if event.kind == "output")
        model = first_path_model(self.text)
        return bool(
            self.actor_is_human
            and actions
            and outputs
            and all(event.valid for event in self.events)
            and not self.invalid_reasons
            and model.material_action
            and model.visible_outcome
        )


def compile_structured_first_path(
    *,
    actor: str,
    actor_is_human: bool,
    path_value: Any,
    action_value: Any,
    output_value: Any,
    actor_owned_action: bool = False,
) -> StructuredFirstPathContract:
    """Preserve typed start, action, and output fields without prose reclassification."""

    path_rows, path_errors = _field_clauses(path_value)
    action_rows, action_errors = _field_clauses(action_value)
    output_rows, output_errors = _field_clauses(output_value)
    invalid = [*path_errors, *action_errors, *output_errors]
    events: list[StructuredPathEvent] = []
    path_results: list[str] = []
    for path in path_rows:
        start_matched, start = _path_start_source(path)
        path_result = _path_nominal_result(path)
        if start_matched:
            if start:
                events.append(_event("start", path, f"complete {start}"))
            else:
                invalid.append("explicit path start has no action")
        elif _PATH_CONTROL_RE.fullmatch(path):
            continue
        elif path_result:
            path_results.append(path_result)
        else:
            events.append(_event("action", path, path))
    for index, action in enumerate(action_rows):
        owned_action = path_entry_action(action) if actor_owned_action and index == 0 else action
        events.append(_event("action", action, owned_action))
    for output in (*path_results, *output_rows):
        if is_negated_output_scope(output):
            continue
        output_event = _output_event(output)
        if not output_event.valid:
            invalid.append("typed output is not a usable positive result")
            continue
        covered = any(
            _action_event_covers_output(event, output_event=output_event)
            for event in events
        )
        events.append(replace(output_event, render=not covered))
    supplied_output = bool(output_rows or path_results)
    if not supplied_output and not any(event.kind == "output" for event in events):
        inferred_text = _render_events(actor=actor, events=events)
        outcome = first_path_model(inferred_text).visible_outcome
        if outcome:
            events.append(
                StructuredPathEvent(
                    kind="output",
                    source_text=outcome,
                    action_text=f"receive {outcome}",
                    identity=_event_identity(outcome),
                    valid=bool(_event_identity(outcome)),
                    render=False,
                )
            )
    text = _render_events(actor=actor, events=events)
    return StructuredFirstPathContract(
        actor=_clean(actor).strip(" ."),
        actor_is_human=actor_is_human,
        events=tuple(events),
        text=text,
        invalid_reasons=tuple(dict.fromkeys(invalid)),
        explicit_output=supplied_output,
    )


def compile_temporal_first_path(
    *,
    events: tuple[tuple[str, str], ...],
    output_value: Any,
) -> StructuredFirstPathContract:
    """Compile already ordered actor-owned rule events without changing their subjects."""

    rows: list[StructuredPathEvent] = []
    for actor, action in events:
        subject = structured_actor_subject(actor)
        rendered = f"{subject} {base_action_clause(action)}".strip(" .")
        rows.append(_event("action", rendered, action, rendered_text=rendered))
    output_rows, invalid = _field_clauses(output_value)
    for output in output_rows:
        if is_negated_output_scope(output):
            continue
        output_event = _output_event(output)
        covered = any(_action_event_covers_output(event, output_event=output_event) for event in rows)
        rows.append(
            replace(
                output_event,
                render=not covered,
                rendered_text=f"The product shows {_article_output(output)}",
            )
        )
    text = ". ".join(event.rendered_text or event.action_text for event in rows if event.render)
    actor = events[0][0] if events else ""
    return StructuredFirstPathContract(
        actor=actor,
        actor_is_human=bool(actor),
        events=tuple(rows),
        text=f"{text.rstrip(' .')}." if text else "",
        invalid_reasons=invalid,
        explicit_output=bool(output_rows),
    )


def path_start_source(value: str) -> str:
    """Return the unrendered source action named by an explicit path-start field."""

    matched, source = _path_start_source(value)
    return source if matched else ""


def path_start_action(value: str) -> str:
    """Return the display action named by an explicit path-start field."""

    source = path_start_source(value)
    return f"complete {source}" if source else ""


def explicit_path_start_value(value: str) -> str:
    """Return one explicit natural-language path-start sentence from evidence."""

    for sentence in sentence_fragments(_clean(value)):
        matched, source = _path_start_source(sentence)
        if matched and source:
            return sentence.strip(" .")
    return ""


def is_negated_output_scope(value: str) -> bool:
    """Return whether one already segmented output clause is negative."""

    return bool(_NEGATED_SCOPE_RE.search(_clean(value)))


def structured_actor_subject(value: str) -> str:
    """Render one typed actor label as a sentence subject."""

    actor = _clean(value).strip(" .")
    if not actor:
        return ""
    if "," not in actor:
        words = actor.split()
        if (
            len(words) >= 2
            and words[-1][:1].isupper()
            and not words[-1].isupper()
            and any(
                word.islower() and word.casefold() not in _IDENTITY_ARTICLES | _IDENTITY_CONNECTORS
                for word in words[:-1]
            )
            and any(word_has_actor_role_signal(word) for word in words[:-1])
        ):
            return f"{words[-1]}, {_indefinite_role(' '.join(words[:-1]))},"
        return actor[:1].upper() + actor[1:]
    name, role = (part.strip() for part in actor.split(",", 1))
    role = re.sub(r"^(?:a|an|the)\s+", "", role, flags=re.IGNORECASE).strip()
    return f"{name}, {_indefinite_role(role)}," if name and role else actor.replace(",", "")


def named_actor_phrase(*, name: str, role: str) -> str:
    """Return one grammatical named-person role phrase from explicit source fields."""

    person = _clean(name).strip(" .,")
    role_text = re.sub(r"^(?:a|an|the)\s+", "", _clean(role), flags=re.IGNORECASE).strip(" .,")
    return f"{person}, {_indefinite_role(role_text)}" if person and role_text else ""


def path_entry_action(value: str) -> str:
    """Return the material action from an explicit starts/begins-by clause."""

    text = _clean(value).strip(" .")
    match = re.match(r"^(?:starts?|begins?)\s+by\s+(?P<action>.+)$", text, flags=re.IGNORECASE)
    if not match:
        return text
    action = match.group("action").strip(" .")
    return base_gerund_clause(action).strip(" .") or base_action_clause(action).strip(" .") or action


def actor_owned_action_from_text(value: str, *, actor: str) -> str:
    """Return the first source sentence action owned by a known typed actor."""

    aliases = sorted(structured_actor_aliases(actor), key=len, reverse=True)
    for sentence in sentence_fragments(_clean(value)):
        text = sentence.strip(" .")
        lowered = text.casefold()
        alias = next(
            (
                candidate
                for candidate in aliases
                if lowered == candidate
                or lowered.startswith(f"{candidate} ")
                or lowered.startswith(f"{candidate},")
            ),
            "",
        )
        if not alias:
            continue
        action = text[len(alias) :].strip(" ,.;:")
        action = strip_leading_action_modal(action).strip(" .")
        if action:
            return path_entry_action(action)
    return ""


def passive_event_parts(value: str) -> tuple[str, str]:
    """Return the affected subject and active-form action from a passive event."""

    text = _clean(value).strip(" .")
    spans = tuple(re.finditer(r"[A-Za-z0-9][A-Za-z0-9'/-]*", text))
    for index in range(1, min(6, len(spans) - 1)):
        auxiliary = spans[index].group(0).casefold()
        predicate = spans[index + 1].group(0)
        if auxiliary not in _PASSIVE_AUXILIARIES:
            continue
        action = past_action_verb(predicate)
        subject = text[: spans[index].start()].strip(" ,.;:")
        if not subject or not action:
            continue
        context = text[spans[index + 1].end() :].strip(" ,.;:")
        subject_words = subject.split(maxsplit=1)
        active_subject = subject
        if subject_words[0].casefold() in _IDENTITY_ARTICLES:
            active_subject = " ".join([subject_words[0].casefold(), *subject_words[1:]])
        active = f"{action} {active_subject}"
        if context:
            active = f"{active} {context}"
        return subject, active
    return "", ""


def structured_actor_aliases(value: str) -> tuple[str, ...]:
    """Return canonical and named aliases for one typed actor phrase."""

    actor = _clean(value).strip(" .")
    subject = structured_actor_subject(actor).rstrip(" ,")
    name, separator, _role = subject.partition(",")
    values = [actor, subject]
    coordinated_actor = actor.split(",", 1)[0]
    coordinated_roles = tuple(
        role.strip()
        for role in re.split(r"\s+(?:and|or)\s+", coordinated_actor, flags=re.IGNORECASE)
        if role.strip()
    )
    if len(coordinated_roles) > 1:
        values.extend(coordinated_roles)
    if separator and len(name.split()) == 1:
        values.append(name)
        role = re.sub(r"^(?:a|an|the)\s+", "", _role.strip(), flags=re.IGNORECASE)
        if role:
            values.extend((role, role.split()[-1]))
    actor_words = actor.split()
    if (
        len(actor_words) >= 2
        and actor_words[-1][:1].isupper()
        and not actor_words[-1].isupper()
        and any(
            word.islower() and word.casefold() not in _IDENTITY_ARTICLES | _IDENTITY_CONNECTORS
            for word in actor_words[:-1]
        )
    ):
        values.append(actor_words[-1])
        role = " ".join(actor_words[:-1]).strip()
        if role:
            values.extend((role, role.split()[-1]))
    return tuple(dict.fromkeys(item.casefold() for item in values if item))


def _row_starts_with_actor_alias(value: str, *, aliases: Sequence[str]) -> bool:
    row = _clean(value).strip(" .").casefold()
    articleless_row = re.sub(r"^(?:a|an|the)\s+", "", row, flags=re.IGNORECASE)
    return any(
        candidate == alias or candidate.startswith(f"{alias} ") or candidate.startswith(f"{alias},")
        for alias in aliases
        for candidate in (row, articleless_row)
    )


def _event(
    kind: str,
    source: str,
    action: str,
    *,
    rendered_text: str = "",
) -> StructuredPathEvent:
    source_text = _clean(source).strip(" .")
    action_text = _clean(action).strip(" .")
    identity = _event_identity(action_text)
    return StructuredPathEvent(
        kind=kind,
        source_text=source_text,
        action_text=action_text,
        identity=identity,
        valid=bool(source_text and action_text and identity and not is_negated_output_scope(source_text)),
        rendered_text=rendered_text,
    )


def _output_event(value: str) -> StructuredPathEvent:
    output = _clean(value).strip(" .")
    direct = strip_leading_action_modal(output)
    action = base_action_clause(direct) if _OUTPUT_ACTION_RE.match(direct) else f"receive {output}"
    return _event("output", output, action)


def _action_event_covers_output(
    event: StructuredPathEvent,
    *,
    output_event: StructuredPathEvent,
) -> bool:
    if event.kind not in {"action", "start"} or not event.identity or not output_event.identity:
        return False
    output_terms = set(output_event.identity)
    if not output_terms <= set(event.identity):
        return False
    return any(
        _OUTPUT_ACTION_RE.match(clause) and _event_identity(clause) == output_event.identity
        for clause in _coordinated_action_clauses(event.action_text)
    )


def _coordinated_action_clauses(value: str) -> tuple[str, ...]:
    return tuple(
        strip_leading_action_modal(clause).strip(" .")
        for clause in re.split(r"\s*,\s*(?:and\s+)?|\s+(?:and|then)\s+", _clean(value), flags=re.IGNORECASE)
        if clause.strip(" .")
    )


def _render_events(*, actor: str, events: list[StructuredPathEvent]) -> str:
    visible = [event for event in events if event.render and event.valid]
    if not visible:
        return ""
    subject = structured_actor_subject(actor)
    if subject and "," not in subject and len(visible) > 1 and all(not event.rendered_text for event in visible):
        compact = _compact_structured_path(subject=subject, events=visible)
        model = first_path_model(compact)
        if len(model.steps) == len(visible) and model.material_action and model.visible_outcome:
            return compact
    rows: list[str] = []
    followup_subject = _followup_actor_subject(actor)
    for index, event in enumerate(visible):
        if event.rendered_text:
            rows.append(event.rendered_text)
            continue
        direct = base_action_clause(strip_leading_action_modal(event.action_text))
        if not rows and subject:
            rows.append(f"{subject} can {direct}".strip(" ."))
        elif subject:
            rows.append(f"{followup_subject} can {direct}".strip(" ."))
        else:
            rows.append(direct)
    return ". ".join(rows).strip(" .")


def _compact_structured_path(*, subject: str, events: list[StructuredPathEvent]) -> str:
    actions = [event.action_text for event in events]
    return f"{subject} can {base_action_clause(_join_actions(actions))}".strip(" .")


def _followup_actor_subject(value: str) -> str:
    subject = structured_actor_subject(value).rstrip(" ,")
    name, separator, _role = subject.partition(",")
    return name.strip() if separator and name.strip() else subject


def _path_start_source(value: str) -> tuple[bool, str]:
    match = _PATH_START_RE.fullmatch(_clean(value).strip(" ."))
    if not match:
        return False, ""
    rows = sentence_fragments(match.group("start"))
    return True, rows[0].strip(" .") if rows else ""


def _path_nominal_result(value: str) -> str:
    match = _PATH_NOMINAL_RESULT_RE.fullmatch(_clean(value).strip(" ."))
    return match.group("result").strip(" .") if match else ""


def _field_clauses(value: Any) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if isinstance(value, Mapping):
        return (), ("structured field contains an object instead of text",)
    items = value if isinstance(value, (list, tuple)) else (value,)
    clauses: list[str] = []
    invalid: list[str] = []
    for item in items:
        if isinstance(item, Mapping) or isinstance(item, (list, tuple)):
            nested, errors = _field_clauses(item)
            clauses.extend(nested)
            invalid.extend(errors)
            continue
        text = _clean(item).strip(" .")
        if not text:
            continue
        if _STRUCTURED_LABEL_RE.search(text):
            invalid.append("structured field contains serialized field labels")
            continue
        for sentence in sentence_fragments(text):
            clauses.extend(
                clause.strip(" .")
                for clause in re.split(r"\s*(?:;|->)\s*", sentence)
                if clause.strip(" .")
            )
    return tuple(clauses), tuple(dict.fromkeys(invalid))


def _event_identity(value: str) -> tuple[str, ...]:
    text = _without_system_context(strip_leading_action_modal(_clean(value).strip(" .")))
    words = [word.casefold() for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9'/-]*", text)]
    if words and (action_token_form(words[0]) or _OUTPUT_ACTION_RE.fullmatch(words[0]) or words[0] == "complete"):
        words.pop(0)
    return tuple(word for word in words if word not in _IDENTITY_ARTICLES | _IDENTITY_CONNECTORS)


def _without_system_context(value: str) -> str:
    return re.sub(
        r"\s+in\s+(?:the\s+)?[A-Z][A-Za-z0-9'/-]*(?:\s+[A-Z][A-Za-z0-9'/-]*){0,4}$",
        "",
        value,
    )


def _article_output(value: str) -> str:
    output = _clean(value).strip(" .")
    return output if output.casefold().startswith(("a ", "an ", "the ")) else f"the {output}"


def _indefinite_role(value: str) -> str:
    role = _clean(value).strip(" .")
    first = role.split(maxsplit=1)[0].casefold() if role else ""
    consonant_vowel_prefix = re.match(r"^(?:ewe|euro|one|uni(?:form|que|t|vers)|use|user)", first)
    article = "an" if first[:1] in {"a", "e", "i", "o", "u"} and not consonant_vowel_prefix else "a"
    return f"{article} {role}".strip()


def _join_actions(actions: list[str]) -> str:
    if len(actions) == 1:
        return actions[0]
    if len(actions) == 2:
        return f"{actions[0]} and {actions[1]}"
    return f"{', '.join(actions[:-1])}, and {actions[-1]}"


def _clean(value: object) -> str:
    return clean_text(clean_markdown_text(value))


__all__ = [
    "StructuredFirstPathContract",
    "StructuredPathEvent",
    "compile_structured_first_path",
    "compile_temporal_first_path",
    "explicit_path_start_value",
    "is_negated_output_scope",
    "actor_owned_action_from_text",
    "named_actor_phrase",
    "passive_event_parts",
    "path_entry_action",
    "path_start_action",
    "path_start_source",
    "structured_actor_aliases",
    "structured_actor_subject",
]
