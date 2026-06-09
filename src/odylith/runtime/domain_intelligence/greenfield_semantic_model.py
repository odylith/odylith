"""Typed semantic model for confirmed greenfield governance generation."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.domain_intelligence.greenfield_component_axes import component_axis_key_for_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import release_scope_for_component
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import actor_signature
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
    state_label = _clean(state_object) or f"{_clean(title) or 'Product'} state"
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
                path_contract.visible_result or proof_boundary,
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
    events = tuple(_first_path_events(model.steps, actor=actor, state_object=state_object, human_actors=human_actors))
    contract_actor = events[0].actor if events and events[0].actor else actor
    return FirstPathContract(
        actor=contract_actor,
        action=_action_label(material),
        entity=state_object,
        mutation=material,
        required_fields=required_fields,
        persistence=f"{state_object} must remain replayable after the accepted first path changes it.",
        visible_result=visible_result or "the first-path result",
        recovery_path=_clean(model.recovery_action) or "Blocked or corrected path state stays visible.",
        deferred_scope=tuple(_clean(row) for row in non_goals if _clean(row)),
        capability=first_path_capability_phrase(first_path, gerund=True),
        raw_path=_clean(first_path),
        events=events,
    )


def _first_path_events(
    steps: Sequence[str],
    *,
    actor: str,
    state_object: str,
    human_actors: Sequence[str],
) -> list[FirstPathEvent]:
    events: list[FirstPathEvent] = []
    current_actor = actor
    for index, step in enumerate(steps, start=1):
        text = _clean(step)
        event_actor = _event_actor(text, human_actors=human_actors, fallback=current_actor or actor)
        current_actor = event_actor or current_actor
        action = _action_label(text)
        target = _event_target(text, state_object=state_object)
        events.append(
            FirstPathEvent(
                index=index,
                actor=event_actor or actor,
                action=action,
                target_entity=target,
                mutation=text,
                visible_result=_is_visible_result(text),
                recovery_path=_is_recovery_path(text),
                text=text,
            )
        )
    return events


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
            claim=f"{first_path_contract.actor} can complete {first_path_contract.capability}.",
            required_evidence=(
                f"Fixture covers required fields {', '.join(first_path_contract.required_fields[:6]) or first_path_contract.entity}, "
                f"mutation `{first_path_contract.mutation}`, persistence, visible result, and recovery behavior."
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
        proof = component.proof_obligations[0] if component.proof_obligations else "Local proof covers owned state, inputs, outputs, blockers, and handoff."
        obligations.append(
            ProofObligation(
                key=f"component_{component.component_id}",
                claim=f"{component.label} preserves its local ownership boundary.",
                required_evidence=proof,
            )
        )
    return tuple(obligations)


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
            clipped = _clip_clause(clause, 88)
            return f"visible outcome proof: {clipped}" if clipped else "visible outcome proof"
    return f"visible outcome proof: {state_label} validation, replay evidence, blockers, and release decision"


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
    terms = ordered_terms(step, stopwords=_SEMANTIC_MODEL_TERM_STOPWORDS)
    if terms:
        return " ".join(terms[:4])
    return state_object


def _is_visible_result(value: str) -> bool:
    return bool(
        re.search(
            r"\b(?:available|choose|chooses|display|displays|highlight|highlights|inspect|inspects|present|presents|produce|produces|ready|render|renders|return|returns|see|sees|select|selects|show|shows|view|views|review|reviews|receive|receives|publish|publishes|restored)\b",
            value,
            re.IGNORECASE,
        )
        or re.search(
            r"\b(?:card|dashboard|indicator|readout|result|summary|timeline|trend|view)\b",
            value,
            re.IGNORECASE,
        )
    )


def _is_recovery_path(value: str) -> bool:
    return bool(re.search(r"\b(?:block|blocks|blocked|edit|edits|correct|corrects|recover|recovers|retry|retries|revise|revises)\b", value, re.IGNORECASE))


def _action_label(value: str) -> str:
    match = re.search(
        r"\b(adds?|adjusts?|approves?|captures?|checks?|chooses?|compares?|completes?|creates?|displays?|edits?|enters?|exports?|imports?|logs?|opens?|produces?|publishes?|ranks?|records?|renders?|returns?|reviews?|saves?|sees?|shows?|stores?|submits?|tracks?|updates?|views?)\b",
        _clean(value),
        re.IGNORECASE,
    )
    return match.group(1).casefold() if match else "advance"


def _actor_label(values: Sequence[str], *, fallback: str) -> str:
    for value in values:
        text = _clean(value).split("—", 1)[0].split(":", 1)[0].strip(" .")
        if text:
            return text
    return fallback


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
