"""Derived semantic axes for greenfield component differentiation.

The greenfield generator cannot carry a baked catalog of product domains.
Component axes are therefore derived from the accepted intent/component text at
runtime and use only generic ownership primitives.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_text import normalize_domain_token


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

    terms = _content_terms(label_text)
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

    label_terms = _content_terms(label_text)
    context_terms = _content_terms(context_text)
    terms = _unique([*label_terms, *context_terms])
    if not terms:
        return None
    primary = _phrase(label_terms[:4]) or _phrase(terms[:4]) or "component"
    detail = _phrase([term for term in terms if term not in label_terms][:5]) or "accepted product context"
    input_focus = _phrase(terms[4:8]) or detail
    output_focus = _phrase(terms[8:12]) or detail
    states = _unique([*terms[:5], "requested", "validated", "blocked", "handed-off"])
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


def _content_terms(value: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", _normalize_axis_text(value).casefold()):
        token = _term_token(raw)
        if token and token not in seen:
            seen.add(token)
            terms.append(token)
    return terms


def _term_token(value: str) -> str:
    return normalize_domain_token(value, stopwords=_GENERIC_TERMS)


def _phrase(values: list[str] | tuple[str, ...]) -> str:
    return " ".join(str(value).strip() for value in values if str(value).strip())


def _unique(values: list[str] | tuple[str, ...]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _normalize_axis_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ")).strip()


__all__ = [
    "COMPONENT_AXES",
    "ComponentAxis",
    "component_axis_for_label",
    "component_axis_key_for_label",
    "derive_component_axis",
]
