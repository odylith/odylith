"""Typed semantic model for confirmed greenfield governance generation."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.common.prose_grammar import base_gerund_clause
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_component_axes import component_axis_key_for_label
from odylith.runtime.domain_intelligence.greenfield_component_terms import object_clause_focus
from odylith.runtime.domain_intelligence.greenfield_component_terms import strip_action
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import normalize_action_clause
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import object_reference_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import release_scope_for_component
from odylith.runtime.domain_intelligence.greenfield_actor_led_prefix import looks_like_actor_led_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import actor_signature
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import visible_result_object
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import clip_text_at_word_boundary
from odylith.runtime.domain_intelligence.greenfield_text import text_values

_SEMANTIC_MODEL_TERM_STOPWORDS = {
    "accepted",
    "action",
    "after",
    "before",
    "boundary",
    "complete",
    "create",
    "created",
    "enter",
    "entered",
    "enters",
    "first",
    "greenfield",
    "least",
    "path",
    "person",
    "product",
    "proven",
    "proof",
    "record",
    "recorded",
    "release",
    "state",
    "succeed",
    "succeeds",
    "system",
    "that",
    "their",
    "then",
    "this",
    "user",
    "view",
    "viewed",
    "views",
    "when",
    "with",
}
_ACTION_VERB_PATTERN = action_verb_pattern()
_NOUN_LIKE_ACTION_TOKENS = frozenset({"record", "report", "surface", "view"})


@dataclass(frozen=True)
class FirstPathEvent:
    index: int
    actor: str
    action: str
    target_entity: str
    mutation: str
    visible_result: bool
    recovery_path: bool
    text: str


@dataclass(frozen=True)
class FirstPathContract:
    actor: str
    action: str
    entity: str
    mutation: str
    required_fields: tuple[str, ...]
    persistence: str
    visible_result: str
    recovery_path: str
    deferred_scope: tuple[str, ...]
    capability: str
    raw_path: str
    events: tuple[FirstPathEvent, ...]


@dataclass(frozen=True)
class DomainOntology:
    product_title: str
    state_object: str
    proof_boundary: str
    human_actors: tuple[str, ...]
    internal_systems: tuple[str, ...]
    external_systems: tuple[str, ...]
    non_goals: tuple[str, ...]
    domain_terms: tuple[str, ...]


@dataclass(frozen=True)
class ComponentContractRef:
    component_id: str
    label: str
    semantic_axis: str
    release_scope: str
    owned_state: str
    accepted_inputs: str
    produced_outputs: str
    proof_obligations: tuple[str, ...]


@dataclass(frozen=True)
class WorkstreamContractRef:
    title: str
    component_ids: tuple[str, ...]
    local_problem: str
    first_slice: str
    proof: str


@dataclass(frozen=True)
class DiagramEventGraph:
    events: tuple[FirstPathEvent, ...]
    component_sequence: tuple[str, ...]
    proof_checkpoint: str


@dataclass(frozen=True)
class ProofObligation:
    key: str
    claim: str
    required_evidence: str


@dataclass(frozen=True)
class GreenfieldSemanticModel:
    schema_version: str
    first_path_contract: FirstPathContract
    domain_ontology: DomainOntology
    components: tuple[ComponentContractRef, ...]
    workstreams: tuple[WorkstreamContractRef, ...]
    diagram_event_graph: DiagramEventGraph
    proof_obligations: tuple[ProofObligation, ...]


def build_greenfield_semantic_model(
    *,
    title: str,
    state_object: str,
    first_path: str,
    proof_boundary: str,
    components: Sequence[Mapping[str, Any]],
    human_actors: Sequence[str] = (),
    internal_systems: Sequence[str] = (),
    external_systems: Sequence[str] = (),
    non_goals: Sequence[str] = (),
    workstreams: Sequence[Mapping[str, Any]] = (),
) -> GreenfieldSemanticModel:
    """Build the canonical semantic model that renderers must preserve."""

    first_actor = _actor_label(human_actors, fallback=f"{_clean(title) or 'Product'} user")
    raw_state = _clean(state_object)
    state_label = domain_object_label(raw_state, fallback="") or raw_state or f"{_clean(title) or 'Product'} state"
    path_contract = _first_path_contract(
        actor=first_actor,
        state_object=state_label,
        first_path=first_path,
        proof_boundary=proof_boundary,
        non_goals=non_goals,
        human_actors=human_actors,
    )
    component_refs = tuple(
        _component_ref(
            row,
            first_path=first_path,
            proof_boundary=proof_boundary,
            non_goals=non_goals,
        )
        for row in components
    )
    component_labels = tuple(_clean(row.get("label")) for row in components if isinstance(row, Mapping) and _clean(row.get("label")))
    ontology = DomainOntology(
        product_title=_clean(title),
        state_object=state_label,
        proof_boundary=_clean(proof_boundary),
        human_actors=tuple(_clean(row) for row in human_actors if _clean(row)),
        internal_systems=component_labels or tuple(_clean(row) for row in internal_systems if _clean(row)),
        external_systems=tuple(_clean(row) for row in external_systems if _clean(row)),
        non_goals=tuple(_clean(row) for row in non_goals if _clean(row)),
        domain_terms=tuple(
            sorted(
                ordered_terms(
                    " ".join([title, state_object, first_path, proof_boundary]),
                    stopwords=_SEMANTIC_MODEL_TERM_STOPWORDS,
                )
            )
        ),
    )
    return GreenfieldSemanticModel(
        schema_version="odylith.greenfield.semantic_model.v1",
        first_path_contract=path_contract,
        domain_ontology=ontology,
        components=component_refs,
        workstreams=tuple(_workstream_ref(row) for row in workstreams if isinstance(row, Mapping)),
        diagram_event_graph=DiagramEventGraph(
            events=path_contract.events,
            component_sequence=tuple(ref.component_id for ref in component_refs if _is_first_release_scope(ref.release_scope)),
            proof_checkpoint=_proof_checkpoint(
                _proof_checkpoint_source(path_contract) or proof_boundary,
                state_label=state_label,
            ),
        ),
        proof_obligations=_proof_obligations(
            first_path_contract=path_contract,
            proof_boundary=proof_boundary,
            components=component_refs,
        ),
    )


def semantic_model_mapping(model: GreenfieldSemanticModel) -> dict[str, Any]:
    """Return a JSON-ready dictionary for proposal validation and traceability."""

    return _json_ready(asdict(model))


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(nested) for nested in value]
    return value


def _first_path_contract(
    *,
    actor: str,
    state_object: str,
    first_path: str,
    proof_boundary: str,
    non_goals: Sequence[str],
    human_actors: Sequence[str],
) -> FirstPathContract:
    model = first_path_model(first_path)
    required_fields = tuple(_required_fields(model.steps, state_object=state_object))
    material = _clean(model.material_action) or (model.steps[0] if model.steps else "")
    visible_result = first_path_outcome_phrase(
        first_path,
        proof_boundary=proof_boundary,
        fallback=_clean(model.visible_outcome) or "the first-path result",
    )
    initial_visible_result = visible_result
    events = tuple(
        _first_path_events(
            model.steps,
            actor=actor,
            state_object=state_object,
            human_actors=human_actors,
            visible_result=visible_result,
        )
    )
    visible_result = _reconciled_visible_result(visible_result, model_visible=model.visible_outcome, events=events)
    if visible_result != initial_visible_result:
        events = tuple(
            _first_path_events(
                model.steps,
                actor=actor,
                state_object=state_object,
                human_actors=human_actors,
                visible_result=visible_result,
            )
        )
    contract_actor = events[0].actor if events and events[0].actor else actor
    state_reference = object_reference_phrase(domain_object_label(state_object, fallback=state_object)) or _clean(state_object)
    return FirstPathContract(
        actor=contract_actor,
        action=_action_label(material),
        entity=state_object,
        mutation=material,
        required_fields=required_fields,
        persistence=f"{state_reference} must remain replayable after the accepted first path changes it.",
        visible_result=visible_result or "the first-path result",
        recovery_path=_clean(model.recovery_action) or "Blocked or corrected path state stays visible.",
        deferred_scope=tuple(_clean(row) for row in non_goals if _clean(row)),
        capability=first_path_capability_phrase(first_path, gerund=True),
        raw_path=_clean(first_path),
        events=events,
    )


def _reconciled_visible_result(
    visible_result: str,
    *,
    model_visible: str,
    events: Sequence[FirstPathEvent],
) -> str:
    current = _clean(visible_result)
    terminal = next((event for event in reversed(events) if event.visible_result), None)
    if terminal is None:
        return current
    terminal_result = visible_result_object(terminal.text) or _clean(model_visible)
    terminal_result = _clean(terminal_result).strip(" .")
    if not terminal_result or len(ordered_terms(terminal_result, stopwords=_SEMANTIC_MODEL_TERM_STOPWORDS)) < 2:
        return current
    if not current:
        return terminal_result
    if _is_supporting_evidence_result(terminal_result) and not _is_supporting_evidence_result(current):
        return current
    if _accepted_result_matches_step(terminal.text, current):
        return current
    matched_event = next((event for event in events if _accepted_result_matches_step(event.text, current)), None)
    if matched_event and terminal.index > matched_event.index:
        return terminal_result
    if terminal.index == len(events) and len(ordered_terms(current, stopwords=_SEMANTIC_MODEL_TERM_STOPWORDS)) <= 4:
        return terminal_result
    return current


def _is_supporting_evidence_result(value: str) -> bool:
    text = _clean(value).casefold()
    if not text:
        return False
    if any(term in text for term in ("summary", "report", "decision", "recommendation", "route", "result", "view")):
        return False
    return bool(
        re.search(
            r"\b(?:audit\s+trail|comparison\s+evidence|evidence\s+packet|evidence\s+record|proof\s+record|replay\s+output)\b",
            text,
        )
        or re.search(r"\b(?:audit|evidence|proof|replay)\b", text)
    )


def _first_path_events(
    steps: Sequence[str],
    *,
    actor: str,
    state_object: str,
    human_actors: Sequence[str],
    visible_result: str = "",
) -> list[FirstPathEvent]:
    events: list[FirstPathEvent] = []
    current_actor = actor
    visible_result_text = _clean(visible_result)
    step_count = len(steps)
    for index, step in enumerate(steps, start=1):
        text = _clean(step)
        is_visible = _is_visible_result(
            text,
            visible_result=visible_result_text,
            is_last=index == step_count,
        )
        event_text = text
        event_actor = _event_actor(text, human_actors=human_actors, fallback=current_actor or actor)
        current_actor = event_actor or current_actor
        action = _action_label(text)
        target = _event_target(event_text, state_object=state_object)
        events.append(
            FirstPathEvent(
                index=index,
                actor=event_actor or actor,
                action=action,
                target_entity=target,
                mutation=event_text,
                visible_result=is_visible,
                recovery_path=_is_recovery_path(text),
                text=event_text,
            )
        )
    return _ensure_first_path_event_floor(
        events,
        actor=current_actor or actor,
        state_object=state_object,
        visible_result=visible_result_text,
    )


def _ensure_first_path_event_floor(
    events: list[FirstPathEvent],
    *,
    actor: str,
    state_object: str,
    visible_result: str,
) -> list[FirstPathEvent]:
    if len(events) >= 3:
        return events
    rows = list(events)
    while len(rows) < 3:
        if visible_result and not any(event.visible_result for event in rows):
            text = f"Review {visible_result[:1].lower()}{visible_result[1:]}"
            is_visible = True
        elif visible_result:
            text = _unique_visible_result_review(rows, visible_result)
            is_visible = True
        else:
            text = "Review blockers, evidence, and next step"
            is_visible = False
        rows.append(
            FirstPathEvent(
                index=len(rows) + 1,
                actor=actor,
                action=_action_label(text),
                target_entity=_event_target(text, state_object=state_object),
                mutation=text,
                visible_result=is_visible,
                recovery_path=False,
                text=text,
            )
        )
    return rows


def _unique_visible_result_review(events: list[FirstPathEvent], visible_result: str) -> str:
    target = visible_result[:1].lower() + visible_result[1:]
    candidates = (
        f"Review evidence for {target}",
        f"Confirm proof for {target}",
        f"Keep {target} visible for review",
    )
    existing = {_clean(event.text).casefold().strip(" .") for event in events}
    for candidate in candidates:
        if _clean(candidate).casefold().strip(" .") not in existing:
            return candidate
    return candidates[-1]


def _event_actor(value: str, *, human_actors: Sequence[str], fallback: str) -> str:
    signature = actor_signature(value)
    if not signature:
        return fallback
    signature_terms = set(ordered_terms(signature, stopwords=_SEMANTIC_MODEL_TERM_STOPWORDS))
    if not signature_terms:
        return fallback
    candidates: list[tuple[int, int, str]] = []
    for row in human_actors:
        label = _actor_label([row], fallback="")
        label_terms = set(ordered_terms(label, stopwords=_SEMANTIC_MODEL_TERM_STOPWORDS))
        overlap = len(signature_terms & label_terms)
        if overlap:
            candidates.append((overlap, -len(label_terms), label))
    if not candidates:
        return fallback
    candidates.sort(reverse=True)
    return candidates[0][2]


def _component_ref(
    row: Mapping[str, Any],
    *,
    first_path: str,
    proof_boundary: str,
    non_goals: Sequence[str],
) -> ComponentContractRef:
    contract = row.get("component_contract") if isinstance(row.get("component_contract"), Mapping) else {}
    label = _clean(row.get("label") or row.get("component_id"))
    scope = _clean(row.get("release_scope")) or release_scope_for_component(
        row,
        first_path=first_path,
        proof_boundary=proof_boundary,
        non_goals=non_goals,
    )
    return ComponentContractRef(
        component_id=_clean(row.get("component_id")) or label,
        label=label,
        semantic_axis=component_axis_key_for_label(
            " ".join([label, _clean(row.get("source_system_description")), _clean(row.get("responsibility"))])
        ),
        release_scope=scope,
        owned_state=_clean(contract.get("owned_state") or row.get("responsibility")),
        accepted_inputs=_clean(contract.get("accepted_inputs")),
        produced_outputs=_clean(contract.get("produced_outputs")),
        proof_obligations=tuple(_clean(text) for text in text_values(contract.get("local_proof")) if _clean(text)),
    )


def _is_first_release_scope(value: str) -> bool:
    return _clean(value).casefold() not in {"deferred", "external", "out_of_scope"}


def _workstream_ref(row: Mapping[str, Any]) -> WorkstreamContractRef:
    return WorkstreamContractRef(
        title=_clean(row.get("title")),
        component_ids=tuple(_clean(value) for value in text_values(row.get("component_focus")) if _clean(value)),
        local_problem=_clean(row.get("problem")),
        first_slice=_clean(row.get("recommended_first_slice")),
        proof=" ".join(_clean(value) for value in text_values(row.get("validation")) if _clean(value)),
    )


def _proof_obligations(
    *,
    first_path_contract: FirstPathContract,
    proof_boundary: str,
    components: Sequence[ComponentContractRef],
) -> tuple[ProofObligation, ...]:
    obligations = [
        ProofObligation(
            key="first_path_contract",
            claim=_first_path_contract_claim(first_path_contract),
            required_evidence=(
                f"Fixture includes required fields: {', '.join(first_path_contract.required_fields[:6]) or first_path_contract.entity}; "
                f"mutation evidence for {first_path_contract.action or 'the first action'}, persistence, visible result, and recovery behavior."
            ),
        ),
        ProofObligation(
            key="release_boundary",
            claim=_clean(proof_boundary) or "Release proof stays inside the accepted boundary.",
            required_evidence="Release review links first-path output, state replay, validation result, deferred scope, and decision.",
        ),
    ]
    for component in components:
        if component.release_scope == "out_of_scope":
            continue
        proof = component.proof_obligations[0] if component.proof_obligations else "Local proof includes owned state, inputs, outputs, blockers, and handoff."
        obligations.append(
            ProofObligation(
                key=f"component_{component.component_id}",
                claim=f"{component.label} preserves its local ownership boundary.",
                required_evidence=proof,
            )
        )
    return tuple(obligations)


def _first_path_contract_claim(first_path_contract: FirstPathContract) -> str:
    capability = clean_text(first_path_contract.capability).strip(" .") or "complete the first path"
    action = _actor_led_base_action_phrase(capability) or base_gerund_clause(capability) or normalize_action_clause(capability)
    if action and looks_like_action_clause(action):
        return f"{first_path_contract.actor} can {action}."
    return f"{first_path_contract.actor} can complete {capability}."


def _actor_led_base_action_phrase(value: str) -> str:
    words = clean_text(value).strip(" .").split()
    for index in range(1, min(len(words), 6)):
        prefix = " ".join(words[:index]).strip(" .")
        if not looks_like_actor_led_subject_prefix(prefix, value):
            continue
        candidate = " ".join(words[index:]).strip(" .")
        if looks_like_finite_action(candidate):
            return normalize_action_clause(candidate)
    return ""

def _proof_checkpoint(value: str, *, state_label: str) -> str:
    text = _clean(value)
    text = re.sub(r"^release\s+[A-Za-z0-9_.-]+\s+succeeds\s+(?:only\s+)?when\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^release\s+[A-Za-z0-9_.-]+\s+is\s+trusted\s+only\s+when\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^the\s+release\s+succeeds\s+(?:only\s+)?when\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^the\s+first\s+release\s+works\s+when\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:the\s+)?accepted\s+path\s+can\s+be\s+replayed\s+from\s+", "replay ", text, flags=re.IGNORECASE)
    text = re.sub(r"^the\s+first\s+proof\s+is\s+", "", text, flags=re.IGNORECASE)
    text = re.split(r"\bwhat\s+must\s+not\s+be\s+claimed\s+yet\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
    clauses = [
        clause.strip(" .")
        for clause in re.split(r";\s+|(?<=[.!?])\s+", text)
        if clause.strip(" .")
    ]
    for clause in clauses:
        if word_count(clause) >= 4:
            clipped = _clip_clause(_nominal_proof_checkpoint_clause(clause), 88)
            return f"visible outcome proof: {clipped}" if clipped else "visible outcome proof"
    return f"visible outcome proof: {state_label} validation, replay evidence, blockers, and release decision"


def _proof_checkpoint_source(contract: FirstPathContract) -> str:
    visible_result = _clean(contract.visible_result)
    for event in reversed(contract.events):
        text = _clean(event.text)
        if event.visible_result and text and not _is_synthetic_visible_result_event(text, visible_result):
            return text
    return visible_result


def _is_synthetic_visible_result_event(text: str, visible_result: str) -> bool:
    if not visible_result:
        return False
    normalized = _clean(text).casefold().strip(" .")
    visible = _clean(visible_result).casefold().strip(" .")
    return normalized in {
        f"review {visible}",
        f"review evidence for {visible}",
        f"confirm proof for {visible}",
        f"keep {visible} visible for review",
    }


def _nominal_proof_checkpoint_clause(value: str) -> str:
    text = _clean(value).strip(" .")
    action = re.match(
        r"^(?:(?:a|an|the)\s+)?(?:[A-Za-z][A-Za-z0-9/&'-]*\s+){0,5}"
        r"(?P<verb>captures?|confirms?|exports?|publishes?|records?|saves?|submits?)\s+"
        r"(?P<object>(?:a|an|the|one)\s+.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not action:
        return text
    verb = action.group("verb").casefold()
    past = {
        "capture": "captured",
        "captures": "captured",
        "confirm": "confirmed",
        "confirms": "confirmed",
        "export": "exported",
        "exports": "exported",
        "publish": "published",
        "publishes": "published",
        "record": "recorded",
        "records": "recorded",
        "save": "saved",
        "saves": "saved",
        "submit": "submitted",
        "submits": "submitted",
    }.get(verb)
    obj = re.sub(r"^(?:a|an|the|one)\s+", "", _clean(action.group("object")), flags=re.IGNORECASE)
    return f"{past} {obj}".strip() if past and obj else text


def _clip_clause(value: str, limit: int) -> str:
    text = _clean(value).strip(" .,:;")
    if len(text) <= limit:
        return text
    clipped = clip_text_at_word_boundary(text, limit=limit)
    return _strip_dangling_tail(clipped) or text


def _strip_dangling_tail(value: str) -> str:
    text = _clean(value).rstrip(" ,;:.")
    while True:
        cleaned = re.sub(
            r"\b(?:a|an|and|as|at|because|before|by|can|for|from|if|in|into|must|of|on|or|should|the|through|to|until|when|while|with|without)$",
            "",
            text,
            flags=re.IGNORECASE,
        ).rstrip(" ,;:.")
        if cleaned == text:
            return cleaned
        text = cleaned


def _required_fields(steps: Sequence[str], *, state_object: str) -> list[str]:
    terms = [
        term
        for term in ordered_terms(
            " ".join([state_object, *steps]),
            stopwords=_SEMANTIC_MODEL_TERM_STOPWORDS,
        )
        if len(term) > 3
    ]
    priority = ["identity", "source", "timestamp", "status", "value", "rationale", "evidence"]
    ordered = [term for term in priority if term in terms]
    ordered.extend(term for term in terms if term not in ordered)
    return ordered[:10]


def _event_target(step: str, *, state_object: str) -> str:
    object_text = _target_object_text(strip_action(object_clause_focus(step)))
    terms = ordered_terms(object_text, stopwords=_SEMANTIC_MODEL_TERM_STOPWORDS)
    if terms:
        return " ".join(terms[:4])
    terms = ordered_terms(step, stopwords=_SEMANTIC_MODEL_TERM_STOPWORDS)
    if terms:
        return " ".join(terms[:4])
    return state_object


def _target_object_text(value: str) -> str:
    words = _clean(value).strip(" .,;:").split()
    relation_terms = {"after", "before", "because", "through", "unless", "until", "using", "when", "while", "with", "without"}
    for index, word in enumerate(words):
        if word.casefold().strip(".,;:") not in relation_terms:
            continue
        return " ".join(words[:index] or words[index + 1 :]).strip(" .,;:")
    return " ".join(words).strip(" .,;:")


def _is_visible_result(value: str, *, visible_result: str = "", is_last: bool = True) -> bool:
    text = _clean(value)
    accepted_result = _clean(visible_result)
    if accepted_result:
        if _accepted_result_matches_step(text, accepted_result):
            return True
        if not is_last:
            return False
    if not is_last:
        return False
    return bool(
        re.search(
            r"\b(?:available|choose|chooses|compare|compares|display|displays|find|finds|highlight|highlights|inspect|inspects|keep|keeps|present|presents|produce|produces|ready|recompute|recomputes|report|reports|render|renders|return|returns|save|saves|see|sees|select|selects|show|shows|store|stores|update|updates|view|views|review|reviews|receive|receives|publish|publishes|restored|viewable)\b",
            text,
            re.IGNORECASE,
        )
        or re.search(
            r"\b(?:card|dashboard|indicator|projection|readout|result|saved|summary|timeline|trend|view)\b",
            text,
            re.IGNORECASE,
        )
    )


def _accepted_result_matches_step(step: str, accepted_result: str) -> bool:
    step_key = _event_text_key(step)
    result_key = _event_text_key(accepted_result)
    if not step_key or not result_key:
        return False
    if step_key == result_key or result_key in step_key or step_key in result_key:
        return True
    step_terms = set(ordered_terms(step_key, stopwords=_SEMANTIC_MODEL_TERM_STOPWORDS))
    result_terms = set(ordered_terms(result_key, stopwords=_SEMANTIC_MODEL_TERM_STOPWORDS))
    if len(result_terms) < 2:
        return False
    overlap = step_terms & result_terms
    return len(overlap) >= 2 and len(overlap) / max(1, len(result_terms)) >= 0.6


def _event_text_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean(value).casefold()).strip()


def _is_recovery_path(value: str) -> bool:
    return bool(re.search(r"\b(?:block|blocks|blocked|edit|edits|correct|corrects|recover|recovers|retry|retries|revise|revises)\b", value, re.IGNORECASE))


def _action_label(value: str) -> str:
    text = _clean(value)
    for match in re.finditer(rf"\b({_ACTION_VERB_PATTERN})\b", text, re.IGNORECASE):
        token = match.group(1).casefold()
        if token in _NOUN_LIKE_ACTION_TOKENS and re.match(rf"\s+(?:{_ACTION_VERB_PATTERN})\b", text[match.end() :], re.IGNORECASE):
            continue
        return token
    return "advance"


def _actor_label(values: Sequence[str], *, fallback: str) -> str:
    for value in values:
        text = _clean(value).split("—", 1)[0].split(":", 1)[0].strip(" .")
        if text:
            return _sentence_safe_actor_label(text)
    return _sentence_safe_actor_label(fallback)


def _sentence_safe_actor_label(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text or not re.search(r"\b(?:and|or)\b", text, flags=re.IGNORECASE):
        return text
    words = [word.strip(".,;:()[]{}") for word in text.split() if word.strip(".,;:()[]{}")]
    if any(any(char.isdigit() for char in word) or (word.isupper() and len(word) > 1) for word in words):
        return text
    if not all(word[:1].isupper() or word.casefold() in {"and", "or"} for word in words):
        return text
    lowered = text.casefold()
    return f"{lowered[:1].upper()}{lowered[1:]}"


def _clean(value: Any) -> str:
    return clean_markdown_text(value)


__all__ = [
    "ComponentContractRef",
    "DiagramEventGraph",
    "DomainOntology",
    "FirstPathContract",
    "FirstPathEvent",
    "GreenfieldSemanticModel",
    "ProofObligation",
    "WorkstreamContractRef",
    "build_greenfield_semantic_model",
    "semantic_model_mapping",
]
