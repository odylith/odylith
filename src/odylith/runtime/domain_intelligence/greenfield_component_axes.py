"""Derived semantic axes for greenfield component differentiation.

The greenfield generator cannot carry a baked catalog of product domains.
Component axes are therefore derived from the accepted intent/component text at
runtime and use only generic ownership primitives.
"""

from __future__ import annotations

from dataclasses import dataclass

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.domain_intelligence.greenfield_component_terms import domain_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import term_phrase


@dataclass(frozen=True)
class ComponentAxis:
    key: str
    triggers: tuple[str, ...]
    owned_state: str
    accepted_inputs: str
    produced_outputs: str
    states_or_transitions: str
    outside_boundary: str
    local_proof: tuple[str, ...]
    unique_failure: str


COMPONENT_AXES: tuple[ComponentAxis, ...] = ()

_GENERIC_TERMS = {
    "accepted",
    "actor",
    "adapter",
    "admin",
    "administrator",
    "application",
    "boundary",
    "candidate",
    "component",
    "contract",
    "coordinator",
    "customer",
    "domain",
    "engine",
    "evidence",
    "first",
    "greenfield",
    "handoff",
    "input",
    "internal",
    "local",
    "output",
    "planned",
    "product",
    "project",
    "proof",
    "record",
    "release",
    "review",
    "reviewer",
    "service",
    "source",
    "state",
    "system",
    "user",
    "validation",
    "view",
    "workflow",
}


def component_axis_key_for_label(label_text: str) -> str:
    """Return a stable axis key derived from the label itself."""

    terms = domain_terms(label_text, noise_terms=_GENERIC_TERMS)
    if not terms:
        return ""
    return f"derived_{slugify('-'.join(terms[:5]))}"


def component_axis_for_label(label_text: str) -> ComponentAxis | None:
    """Resolve a component label to a derived semantic ownership axis."""

    return derive_component_axis(label_text=label_text)


def derive_component_axis(*, label_text: str, context_text: str = "") -> ComponentAxis | None:
    """Build a generic component axis from local text.

    The returned contract is intentionally conservative: it names local state,
    input, output, blocker, handoff, and proof obligations without importing
    vocabulary from another product type.
    """

    label_terms = domain_terms(label_text, noise_terms=_GENERIC_TERMS)
    context_terms = domain_terms(context_text, noise_terms=_GENERIC_TERMS)
    terms = dedupe_strings([*label_terms, *context_terms])
    if not terms:
        return None
    primary = term_phrase(label_terms[:4]) or term_phrase(terms[:4]) or "component"
    detail = term_phrase([term for term in terms if term not in label_terms][:5]) or "accepted product context"
    input_focus = term_phrase(terms[4:8]) or detail
    output_focus = term_phrase(terms[8:12]) or detail
    states = dedupe_strings([*terms[:5], "requested", "validated", "blocked", "handed-off"])
    return ComponentAxis(
        key=component_axis_key_for_label(label_text) or f"derived_{slugify(primary)}",
        triggers=tuple(terms),
        owned_state=f"{primary} state, {detail}, local blockers, and recovery context",
        accepted_inputs=f"{primary} command, {input_focus} context, authorized actor, prior state, and validation notes",
        produced_outputs=f"{primary} result, {output_focus} update, blocked-state explanation, and next-step context",
        states_or_transitions=", ".join(states[:9]),
        outside_boundary=(
            "adjacent component state owned elsewhere; "
            "original input facts and upstream source truth; "
            "release approval and broader rollout decisions"
        ),
        local_proof=(
            f"{primary} proof covers required inputs, owned state, produced outputs, and recovery context.",
            f"Missing, stale, or invalid {input_focus} context blocks the {primary} result.",
            f"{primary} keeps sibling-owned state separate while preserving its own proof trail.",
        ),
        unique_failure=(
            f"{primary} can look complete while required {detail} is missing, stale, "
            "or assigned to the wrong ownership boundary."
        ),
    )

__all__ = [
    "COMPONENT_AXES",
    "ComponentAxis",
    "component_axis_for_label",
    "component_axis_key_for_label",
    "derive_component_axis",
]
