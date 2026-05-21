"""Artifact-native projections from the domain intelligence graph.

Domain intelligence is source substrate. It should shape Radar, Registry,
Atlas, Casebook, Compass, Project, and Tribunal records in each artifact's
native language instead of being pasted into every artifact as a generic
``Domain Intelligence`` section.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


@dataclass(frozen=True)
class DomainIntelligenceGraph:
    family: str
    primary_lens: str
    state_objects: tuple[str, ...]
    actors: tuple[str, ...]
    operators: tuple[str, ...]
    approvers: tuple[str, ...]
    risk_owners: tuple[str, ...]
    proof_standards: tuple[str, ...]
    invariants: tuple[str, ...]
    workflows: tuple[str, ...]
    exception_paths: tuple[str, ...]
    evidence_types: tuple[str, ...]
    validation_obligations: tuple[str, ...]
    glossary: tuple[str, ...]
    maturity_and_origin: tuple[str, ...]


@dataclass(frozen=True)
class ArtifactEnrichment:
    radar_sections: dict[str, str]
    registry_contract: dict[str, tuple[str, ...]]
    atlas_contract: dict[str, tuple[str, ...]]
    plan_contract: dict[str, tuple[str, ...]]
    casebook_contract: dict[str, tuple[str, ...]]
    compass_contract: dict[str, tuple[str, ...]]
    project_contract: dict[str, tuple[str, ...]]
    tribunal_actors: tuple[dict[str, str], ...]


def build_artifact_enrichment(
    *,
    row: Mapping[str, Any],
    proposal: Mapping[str, Any] | None = None,
) -> ArtifactEnrichment:
    """Project one workstream's domain graph into artifact-native payloads."""

    graph = domain_graph_from_workstream(row.get("domain_intelligence"), row=row, proposal=proposal or {})
    return ArtifactEnrichment(
        radar_sections=radar_enrichment_sections(row=row, graph=graph),
        registry_contract=registry_projection(graph),
        atlas_contract=atlas_projection(graph),
        plan_contract=technical_plan_projection(graph),
        casebook_contract=casebook_projection(graph),
        compass_contract=compass_projection(graph),
        project_contract=project_projection(graph),
        tribunal_actors=tribunal_actor_projection(proposal or {"backlog": [row]}),
    )


def domain_graph_from_workstream(
    value: Any,
    *,
    row: Mapping[str, Any] | None = None,
    proposal: Mapping[str, Any] | None = None,
) -> DomainIntelligenceGraph:
    """Normalize existing workstream intelligence into the shared graph shape."""

    data = value if isinstance(value, Mapping) else {}
    intent = (proposal or {}).get("intent") if isinstance(proposal, Mapping) else {}
    title = clean_text((row or {}).get("title")) or clean_text(
        intent.get("title") if isinstance(intent, Mapping) else ""
    )
    family = clean_text(data.get("family")) or "general_project"
    glossary = _layer(data, "ontology")
    proof = unique_text([*_layer(data, "evidence_model"), *_layer(data, "evidence")])
    validation = _layer(data, "validation_obligations")
    explicit_actors = _layer(data, "actors")
    owners = _layer(data, "owners")
    authority = _layer(data, "authority")
    risks = _layer(data, "risks")
    constraints = _layer(data, "constraints")
    operators = _layer(data, "operators")
    state = _layer(data, "state")
    source_truth = _layer(data, "source_of_truth_map")
    invariants = _layer(data, "invariants")
    invalidation = _layer(data, "invalidation_rules")
    conflicts = _layer(data, "conflict_model")

    return DomainIntelligenceGraph(
        family=family,
        primary_lens=_primary_lens(family=family, title=title, glossary=glossary),
        state_objects=tuple(_pick_state_objects(glossary, state)),
        actors=tuple(unique_text([*explicit_actors, *_pick_actor_rows([*owners, *authority, *operators, *glossary])])[:8]),
        operators=tuple(operators),
        approvers=tuple(_pick_approval_rows([*authority, *operators, *validation])),
        risk_owners=tuple(unique_text([*risks, *authority, *owners])[:8]),
        proof_standards=tuple(unique_text([*proof, *validation])[:10]),
        invariants=tuple(invariants),
        workflows=tuple(unique_text([*_layer(data, "intent"), *state, *operators])[:12]),
        exception_paths=tuple(unique_text([*constraints, *risks, *invalidation, *conflicts])[:10]),
        evidence_types=tuple(unique_text([*proof, *source_truth])[:10]),
        validation_obligations=tuple(validation),
        glossary=tuple(glossary),
        maturity_and_origin=tuple(unique_text([*constraints, *_layer(data, "assumptions"), *source_truth])[:8]),
    )


def radar_enrichment_sections(
    *,
    row: Mapping[str, Any],
    graph: DomainIntelligenceGraph,
) -> dict[str, str]:
    """Return Radar-native sections shaped by domain intelligence."""

    first_slice = clean_text(row.get("recommended_first_slice")) or _first(graph.validation_obligations)
    sections: dict[str, str] = {}

    first_path = _bullets(
        [
            _sentence("First path", first_slice),
            _sentence("State object", _first(graph.state_objects)),
            _sentence("Boundary", _first(_layer(row, "scope")) or _first(graph.maturity_and_origin)),
        ]
    )
    if first_path:
        sections["First Path And Boundary"] = first_path

    proof = _bullets(
        [
            *_labelled_rows("Proof", graph.proof_standards[:4]),
            *_labelled_rows("Gate", graph.validation_obligations[:5]),
        ]
    )
    if proof:
        sections["Proof And Acceptance Gates"] = proof

    ownership = _bullets(
        [
            *_labelled_rows("Owner", graph.actors[:3]),
            *_labelled_rows("Risk", graph.risk_owners[:3]),
            *_labelled_rows("Control", graph.exception_paths[:3]),
        ]
    )
    if ownership:
        sections["Ownership And Risk"] = ownership

    return sections


def registry_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return component-spec shaping hints from the domain graph."""

    return {
        "boundaries": _tuple_limit([*graph.state_objects, *graph.invariants], 6),
        "interfaces": _tuple_limit(graph.operators, 5),
        "failure_modes": _tuple_limit(graph.exception_paths, 6),
        "proof_obligations": _tuple_limit(graph.proof_standards, 6),
    }


def atlas_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return diagram-shaping hints from the domain graph."""

    return {
        "actors": _tuple_limit(graph.actors, 6),
        "state_objects": _tuple_limit(graph.state_objects, 6),
        "flows": _tuple_limit(graph.workflows, 8),
        "controls": _tuple_limit([*graph.approvers, *graph.exception_paths], 8),
        "evidence": _tuple_limit(graph.evidence_types, 6),
    }


def technical_plan_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return implementation-plan shaping hints from the domain graph."""

    return {
        "sequence": _tuple_limit(graph.workflows, 6),
        "validation": _tuple_limit(graph.validation_obligations, 6),
        "rollback_or_recovery": _tuple_limit(graph.exception_paths, 5),
        "release_gates": _tuple_limit([*graph.proof_standards, *graph.invariants], 6),
    }


def casebook_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return bug-record shaping hints from the domain graph."""

    return {
        "impact_model": _tuple_limit(graph.risk_owners, 6),
        "affected_actor": _tuple_limit(graph.actors, 4),
        "repro_evidence": _tuple_limit(graph.evidence_types, 6),
        "prevention_rules": _tuple_limit([*graph.invariants, *graph.exception_paths], 6),
    }


def compass_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return current-work narration hints from the domain graph."""

    return {
        "work_language": _tuple_limit(graph.workflows, 5),
        "decision_language": _tuple_limit([*graph.approvers, *graph.operators], 5),
        "proof_boundary": _tuple_limit(graph.proof_standards, 5),
        "open_risk": _tuple_limit(graph.exception_paths, 5),
    }


def project_projection(graph: DomainIntelligenceGraph) -> dict[str, tuple[str, ...]]:
    """Return Project-tab shaping hints from the domain graph."""

    return {
        "lens": (graph.primary_lens,),
        "participants": _tuple_limit(graph.actors, 8),
        "state_objects": _tuple_limit(graph.state_objects, 6),
        "first_path": _tuple_limit(graph.workflows, 6),
        "proof": _tuple_limit(graph.proof_standards, 6),
        "unknowns": _tuple_limit(graph.exception_paths, 6),
    }


def tribunal_actor_projection(proposal: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    """Return domain-specific visible Tribunal actors for a proposal."""

    first_graph = _first_domain_graph(proposal)
    actor_names = _domain_actor_names(first_graph, proposal=proposal)
    responsibilities = {
        "beneficiary_advocate": "Protects the person or team receiving the value.",
        "domain_operator": "Checks that the workflow is operationally coherent.",
        "risk_owner": "Owns loss, harm, compliance, safety, or operational exposure.",
        "evidence_owner": "Decides what proof is strong enough to trust.",
        "implementation_owner": "Owns source paths, interfaces, and build sequence.",
        "release_owner": "Owns release boundary, rollback, and promotion readiness.",
    }
    return tuple(
        {
            "stable_role": role,
            "visible_actor": actor_names[role],
            "responsibility": responsibilities[role],
        }
        for role in _TRIBUNAL_STABLE_ROLES
    )


def _first_domain_graph(proposal: Mapping[str, Any]) -> DomainIntelligenceGraph:
    rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    for row in rows:
        intelligence = row.get("domain_intelligence")
        if isinstance(intelligence, Mapping):
            return domain_graph_from_workstream(intelligence, row=row, proposal=proposal)
    return domain_graph_from_workstream({}, row=rows[0] if rows else {}, proposal=proposal)


_TRIBUNAL_STABLE_ROLES = (
    "beneficiary_advocate",
    "domain_operator",
    "risk_owner",
    "evidence_owner",
    "implementation_owner",
    "release_owner",
)


def _domain_actor_names(graph: DomainIntelligenceGraph, *, proposal: Mapping[str, Any]) -> dict[str, str]:
    compact = _compact_lens_name(graph)
    proposal_actors = _proposal_actor_candidates(proposal)
    actors = _role_candidates([*proposal_actors, *graph.actors])
    operators = _role_specific_candidates(
        [*proposal_actors, *graph.operators, *graph.actors],
        ("operator", "ops", "workflow", "maintainer", "coordinator", "lead"),
        ownerish_fallback=False,
    )
    approvers = _role_candidates(graph.approvers)
    risk_owners = _role_specific_candidates([*graph.risk_owners, *graph.actors], ("risk", "safety", "compliance", "loss"))
    evidence_owners = _role_specific_candidates(
        [*graph.evidence_types, *graph.proof_standards, *graph.actors],
        ("proof", "evidence", "validation"),
    )
    implementation_owners = _role_specific_candidates(
        [*proposal_actors, *graph.invariants, *graph.validation_obligations, *graph.actors],
        ("build", "builder", "implementation", "source", "engineer"),
    ) or _role_specific_candidates(
        [*proposal_actors, *graph.invariants, *graph.validation_obligations, *graph.actors],
        ("maintainer",),
    )
    return {
        "beneficiary_advocate": _actor_label(actors, fallback=f"{compact} beneficiary advocate"),
        "domain_operator": _actor_label(operators, fallback=actors[1] if len(actors) > 1 else f"{compact} operator"),
        "risk_owner": _actor_label(risk_owners, fallback=f"{compact} risk reviewer"),
        "evidence_owner": _actor_label(
            evidence_owners,
            fallback=_derived_role_label(
                [*implementation_owners, *actors],
                explicit_tokens=("proof", "evidence", "validation"),
                fallback_lens=compact,
                role_suffix="proof reviewer",
            ),
        ),
        "implementation_owner": _actor_label(implementation_owners, fallback=f"{compact} build owner"),
        "release_owner": _derived_role_label(
            [
                *implementation_owners,
                *evidence_owners,
                *risk_owners,
                *operators,
                *actors,
            ],
            explicit_tokens=("release", "promotion", "readiness", "rollback", "launch", "delivery"),
            fallback_lens=compact,
            role_suffix="release reviewer",
        ),
    }


def _proposal_actor_candidates(proposal: Mapping[str, Any]) -> tuple[str, ...]:
    """Prefer accepted project actors over internal role fallbacks."""

    values: list[str] = []
    for item in proposal.get("backlog", []):
        if not isinstance(item, Mapping):
            continue
        intelligence = item.get("domain_intelligence")
        if isinstance(intelligence, Mapping):
            values.extend(_actor_segments(intelligence.get("actors")))
    project = proposal.get("project_intelligence")
    if isinstance(project, Mapping):
        for key in ("actors", "owners", "operators"):
            values.extend(_actor_segments(project.get(key)))
    for item in proposal.get("backlog", []):
        if not isinstance(item, Mapping):
            continue
        values.extend(_actor_segments(item.get("customer")))
    return unique_text(_actor_candidate_label(value) for value in values if value)


def _actor_segments(value: Any) -> tuple[str, ...]:
    rows: list[str] = []
    for raw in text_values(value, split_scalar=True, strip_bullets=True):
        text = clean_text(raw).strip(" .")
        if not text:
            continue
        head, sep, tail = text.partition(":")
        if sep and "actor" in head.casefold() and tail.strip():
            text = tail.strip(" .")
        rows.extend(text_values(text, split_scalar=True, strip_bullets=True))
    return unique_text(rows)


def _actor_candidate_label(value: str) -> str:
    text = clean_text(value).strip(" .")
    if not text:
        return ""
    for separator in (" — ", " – ", " - ", ":"):
        head, sep, _body = text.partition(separator)
        if sep and head.strip():
            text = head.strip(" .")
            break
    lowered = text.casefold()
    for marker in (
        " who ",
        " that ",
        " using ",
        " with ",
        " needing ",
        " responsible for ",
        " accountable for ",
        " receiving ",
        " reviewing ",
        " deciding ",
    ):
        head, sep, _tail = lowered.partition(marker)
        if sep and head.strip():
            text = text[: len(head)].strip(" .")
            break
    if len(text.split()) > 6:
        role_phrase = _role_phrase_label(text)
        if role_phrase:
            return role_phrase
    return text


def _role_phrase_label(label: str) -> str:
    role_words = {
        "advocate",
        "builder",
        "coordinator",
        "engineer",
        "lead",
        "maintainer",
        "manufacturer",
        "operator",
        "owner",
        "reviewer",
        "user",
    }
    connectors = {"and", "or", "/", "&"}
    words = [word.strip(".,;:()") for word in clean_text(label).replace("/", " / ").split()]
    for index, word in enumerate(words):
        if word.casefold() not in role_words:
            continue
        start = index
        if index > 0 and words[index - 1].casefold() not in connectors:
            start = index - 1
        end = index + 1
        if end + 1 < len(words) and words[end].casefold() in connectors and words[end + 1].casefold() in role_words:
            end += 2
        phrase = " ".join(words[start:end]).strip()
        if phrase.casefold() in role_words:
            return ""
        return phrase
    return ""


def _primary_lens(*, family: str, title: str, glossary: Sequence[str]) -> str:
    family_label = clean_text(family).replace("_", " ")
    if family_label and family_label not in {"general project", "host reasoned project"}:
        return family_label
    for row in glossary:
        first = clean_text(row).split(":", 1)[0].strip()
        if first and first.casefold() not in {"actor", "state object", "evidence record", "release gate"}:
            return first
    return slugify(title).replace("-", " ") or "project workflow"


def _compact_lens_name(graph: DomainIntelligenceGraph) -> str:
    label = clean_text(graph.primary_lens).split(":", 1)[0].strip()
    if not label:
        return "Project"
    words = label.replace("_", " ").split()
    return " ".join(word[:1].upper() + word[1:] for word in words[:3])


def _role_candidates(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    for value in values:
        label = _actor_candidate_label(value)
        if label:
            rows.append(label)
    return unique_text(rows)


def _ownerish_candidates(values: Sequence[str]) -> list[str]:
    candidates = []
    for value in values:
        label = _actor_candidate_label(value)
        if not label:
            continue
        lowered = label.casefold()
        if any(token in lowered for token in ("owner", "reviewer", "operator", "maintainer", "lead")):
            candidates.append(label)
    return unique_text(candidates)


def _role_specific_candidates(
    values: Sequence[str],
    tokens: Sequence[str],
    *,
    ownerish_fallback: bool = True,
) -> list[str]:
    candidates = []
    for value in values:
        source = clean_text(value)
        label = _actor_candidate_label(source)
        if not label:
            continue
        lowered = source.casefold()
        if any(token in lowered for token in tokens):
            candidates.append(label)
    return unique_text(candidates) or (_ownerish_candidates(values) if ownerish_fallback else [])


def _derived_role_label(
    values: Sequence[str],
    *,
    explicit_tokens: Sequence[str],
    fallback_lens: str,
    role_suffix: str,
) -> str:
    explicit = _role_specific_candidates(values, explicit_tokens, ownerish_fallback=False)
    label = _actor_label(explicit, fallback="")
    if label:
        return label
    for value in values:
        candidate = _actor_candidate_label(value)
        label = _actor_label([candidate], fallback="")
        if label:
            return label
    for value in values:
        candidate = _actor_candidate_label(value)
        prefix = _actor_label_prefix(candidate)
        if prefix:
            return f"{prefix} {role_suffix}"
    return f"{fallback_lens} {role_suffix}"


def _actor_label_prefix(label: str) -> str:
    text = clean_text(label).strip(" .")
    if not text:
        return ""
    role_words = {
        "advocate",
        "beneficiary",
        "builder",
        "coordinator",
        "engineer",
        "lead",
        "maintainer",
        "manufacturer",
        "operator",
        "owner",
        "reviewer",
        "team",
        "user",
    }
    words = text.replace("/", " ").split()
    while words and words[-1].strip(".,;:()").casefold() in role_words:
        words.pop()
    return " ".join(words[:4]).strip()


def _actor_label(values: Sequence[str], *, fallback: str) -> str:
    for value in values:
        label = clean_text(value)
        if (
            label
            and label.casefold()
            not in {
                "actor",
                "actors",
                "human actors",
                "main human actors",
                "maintainer",
                "owner",
                "reviewer",
                "state object",
                "team",
                "user",
                "evidence record",
                "release gate",
                "the first-release actors are",
                "actors involved in the first release are",
                "build owner",
                "domain operator",
                "evidence owner",
                "implementation owner",
                "proof owner",
                "proof reviewer",
                "release owner",
                "release reviewer",
                "risk owner",
                "risk reviewer",
                "workflow operator",
                "check",
                "confirm",
                "prove",
                "review",
                "test",
                "validate",
                "verify",
            }
            and len(label.split()) <= 6
        ):
            return label
    return fallback


def _pick_state_objects(glossary: Sequence[str], state: Sequence[str]) -> list[str]:
    rows = []
    for value in [*glossary, *state]:
        if not _looks_like_state_object(value):
            continue
        lowered = value.casefold()
        if any(
            token in lowered
            for token in (
                "object",
                "state",
                "subject",
                "record",
                "workflow item",
                "tracked item",
            )
        ):
            rows.append(value)
    fallback = [value for value in [*glossary, *state] if _looks_like_state_object(value)]
    return unique_text(rows)[:5] or unique_text(fallback)[:3]


def _looks_like_state_object(value: str) -> bool:
    text = clean_text(value)
    lowered = text.casefold()
    if not text:
        return False
    actor_markers = (
        "human actor",
        "actors include",
        "actor:",
        "first-release actor",
        "operator",
        "reviewer",
        "owner",
        "maintainer",
        "lead",
        "user:",
    )
    if any(marker in lowered for marker in actor_markers):
        return False
    return True


def _pick_actor_rows(values: Sequence[str]) -> list[str]:
    rows = [
        value
        for value in values
        if any(
            token in value.casefold()
            for token in (
                "actor",
                "advocate",
                "operator",
                "owner",
                "lead",
                "maintainer",
                "reviewer",
                "coordinator",
                "approver",
            )
        )
    ]
    return unique_text(rows)[:8]


def _pick_approval_rows(values: Sequence[str]) -> list[str]:
    rows = [
        value
        for value in values
        if any(token in value.casefold() for token in ("approve", "review", "decision", "gate", "authority"))
    ]
    return unique_text(rows)[:6]


def _layer(value: Any, key: str | None = None) -> list[str]:
    target = value.get(key) if key and isinstance(value, Mapping) else value
    return [item for item in text_values(target) if clean_text(item)]


def _first(values: Sequence[str]) -> str:
    return clean_text(values[0]) if values else ""


def _sentence(label: str, value: str) -> str:
    text = _without_existing_label(label=label, value=clean_text(value))
    return f"{label}: {text}" if text else ""


def _without_existing_label(*, label: str, value: str) -> str:
    text = clean_text(value)
    if not text:
        return ""
    label_text = clean_text(label).casefold()
    lowered = text.casefold()
    prefix = f"{label_text}:"
    if lowered.startswith(prefix):
        return clean_text(text[len(prefix) :])
    return text


def _labelled_rows(label: str, values: Sequence[str]) -> list[str]:
    return [_sentence(label, value) for value in values if clean_text(value)]


def _bullets(values: Sequence[str]) -> str:
    rows = [clean_text(value) for value in values if clean_text(value)]
    return "\n".join(f"- {row}" for row in rows)


def _tuple_limit(values: Sequence[str], limit: int) -> tuple[str, ...]:
    return tuple(unique_text(clean_text(value) for value in values if clean_text(value))[:limit])


def _dedupe_model_rows(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        text = clean_text(value)
        if not text:
            continue
        pieces = [piece.strip() for piece in text.split(":") if piece.strip()]
        concept = pieces[1] if len(pieces) >= 2 else pieces[0]
        key = concept.casefold()
        if key in seen:
            continue
        seen.add(key)
        rows.append(text)
    return rows


__all__ = [
    "ArtifactEnrichment",
    "DomainIntelligenceGraph",
    "atlas_projection",
    "build_artifact_enrichment",
    "casebook_projection",
    "compass_projection",
    "domain_graph_from_workstream",
    "project_projection",
    "radar_enrichment_sections",
    "registry_projection",
    "technical_plan_projection",
    "tribunal_actor_projection",
]
