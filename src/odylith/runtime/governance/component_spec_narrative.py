"""Narrative Registry spec renderer for greenfield component contracts."""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common import display_text
from odylith.runtime.common.prose_grammar import contains_finite_action
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.common.prose_grammar import repair_modal_base_form_drift
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import collapse_adjacent_duplicate_terms
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import RELATION_TAIL_WORDS
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import normalize_action_splice_phrase
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import normalize_artifact_tail
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import relation_object_phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import action_object_artifact_phrases
from odylith.runtime.domain_intelligence.greenfield_component_narrative_view import ComponentNarrativeView
from odylith.runtime.domain_intelligence.greenfield_component_narrative_view import component_narrative_view
from odylith.runtime.domain_intelligence.greenfield_component_narrative_view import narrative_items
from odylith.runtime.domain_intelligence.greenfield_component_narrative_view import phrases_too_similar
from odylith.runtime.domain_intelligence.greenfield_text import clean_text, text_values, unique_text

_PRONOUN_OBJECT_PRECEDERS = frozenset(
    {
        "accept",
        "accepts",
        "apply",
        "applies",
        "check",
        "checks",
        "compare",
        "compares",
        "consume",
        "consumes",
        "inspect",
        "inspects",
        "mutate",
        "mutates",
        "read",
        "reads",
        "review",
        "reviews",
        "rewrite",
        "rewrites",
        "see",
        "sees",
        "trust",
        "trusts",
        "use",
        "uses",
        "validate",
        "validates",
        "view",
        "views",
    }
)


def build_narrative_component_spec(
    *,
    component_id: str,
    label: str,
    path: str,
    kind: str,
    status: str,
    sources: Sequence[str],
    workstreams: Sequence[str],
    diagrams: Sequence[str] = (),
    responsibility: str = "",
    implementation_handoff: Mapping[str, Any] | None = None,
    component_contract: Mapping[str, Any],
) -> str:
    """Render a greenfield component contract as a readable implementation brief."""

    handoff = implementation_handoff or {}
    owns = _contract_items(component_contract, "owned_state")
    accepts = _contract_items(component_contract, "accepted_inputs")
    produces = _contract_items(component_contract, "produced_outputs")
    transitions = _contract_items(component_contract, "states_or_transitions")
    outside = _contract_items(component_contract, "outside_boundary")
    proofs = _proof_items(component_contract.get("local_proof"))
    upstream = _entity_text(component_contract.get("upstream_truth"))
    downstream = _entity_text(component_contract.get("downstream_consumers"))
    failure = _sentence(_failure_fragment(component_contract.get("unique_failure")))
    accepted_intent = _accepted_intent_sentence(responsibility, label=label)

    focus = _fallback_phrase(owns, label)
    input_focus = _fallback_phrase(accepts, "the inputs required for this boundary")
    output_focus = _fallback_phrase(produces, "the output that downstream work depends on")
    first_workstream = _handoff_text(handoff, "workstream_id") or _first(workstreams)
    first_workstream_title = _handoff_text(handoff, "workstream_title")
    first_slice = _sentence(_handoff_text(handoff, "first_slice"))
    release_selector = _handoff_text(handoff, "release_selector")
    wave_label = _handoff_text(handoff, "wave_label")
    source_boundary = path or "selected by the first implementation plan"
    view = component_narrative_view(
        label=label,
        owns=owns,
        accepts=accepts,
        produces=produces,
        transitions=transitions,
        outside=outside,
        proofs=proofs,
    )
    role = view.role
    transition_focus = _calculation_transition_focus(view.concrete_transition_items or view.transition_items)

    lines = [
        f"# {label}",
        "",
        _planning_note(label=label, sources=sources, path=path, workstreams=workstreams, diagrams=diagrams),
        "",
        _opening_narrative(
            label=label,
            kind=kind,
            role=role,
            focus=focus,
            input_focus=input_focus,
            output_focus=output_focus,
            transition_focus=transition_focus,
            accepted_intent=accepted_intent,
        ),
        "",
        _narrative_section(
            "State and Ownership",
            _state_narrative(
                label=label,
                role=role,
                view=view,
            ),
        ),
        "",
        _narrative_section(
            "Boundary and Handoff",
            _boundary_narrative(
                label=label,
                role=role,
                upstream=upstream,
                downstream=downstream,
                input_focus=input_focus,
                output_focus=output_focus,
                outside=outside,
            ),
        ),
        "",
        _narrative_section("Proof and Risk Controls", _proof_narrative(label=label, role=role, failure=failure, proofs=proofs)),
        "",
        _narrative_section(
            "Implementation Handoff",
            _implementation_narrative(
                label=label,
                role=role,
                source_boundary=source_boundary,
                first_workstream=first_workstream,
                first_workstream_title=first_workstream_title,
                first_slice=first_slice,
                release_selector=release_selector,
                wave_label=wave_label,
            ),
        ),
        "",
        "## Feature History",
        "",
        f"- {dt.date.today().isoformat()}: Registered {label} as a {status or 'planned'} {kind or 'component'} from user intent{_plan_link(first_workstream)}.",
        "",
    ]
    return _finalize_narrative_spec_text("\n".join(line for line in lines if line is not None))


def _narrative_section(title: str, narrative: str) -> str:
    """Render dense generated narrative as a scan-friendly component section."""

    rows = _sentence_rows(narrative)
    if not rows:
        return f"## {title}"
    return "\n".join([f"## {title}", "", *(f"- {row}" for row in rows)])


def _sentence_rows(value: str) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    rows: list[str] = []
    for sentence in text.split(". "):
        row = sentence.strip()
        if row:
            rows.append(row if row.endswith(".") else f"{row}.")
    return rows


def _planning_note(
    *,
    label: str,
    sources: Sequence[str],
    path: str,
    workstreams: Sequence[str],
    diagrams: Sequence[str],
) -> str:
    evidence = "user-stated intent" if any(str(item).strip() == "user_intent" for item in sources) else "governance evidence"
    source = f" Source boundary: {path}." if path else " Source boundary waits for the first implementation plan."
    workstream_text = _identifier_list(workstreams)
    diagram_text = _identifier_list(diagrams)
    trace = []
    if workstream_text:
        trace.append(f"workstreams {workstream_text}")
    if diagram_text:
        trace.append(f"diagrams {diagram_text}")
    trace_text = f" Trace links for {label}: {'; '.join(trace)}." if trace else ""
    return f"> Planned from {evidence}.{source}{trace_text}"


def _opening_narrative(
    *,
    label: str,
    kind: str,
    role: str,
    focus: str,
    input_focus: str,
    output_focus: str,
    transition_focus: str,
    accepted_intent: str,
) -> str:
    noun = _kind_noun(kind)
    raw_focus = focus
    raw_input_focus = input_focus
    raw_output_focus = output_focus
    focus = _compact_opening_focus(focus, fallback_noun="state")
    input_focus = _compact_opening_focus(input_focus, fallback_noun="input")
    output_focus = _compact_opening_focus(output_focus, fallback_noun="output")
    if role == "entry":
        lead = f"{label} is responsible for the first product information this boundary must make reliable."
        body = f"It keeps {focus} together so the next product step can move forward without another boundary guessing what the user meant or what is still missing."
    elif role == "decision":
        lead = f"{label} turns prepared evidence into a product outcome with an explanation."
        body = (
            f"{label} should keep {output_focus} reviewable, because downstream work needs the decision result, "
            "its rationale, and any blocked-state detail before it can trust the next step."
        )
    elif role == "calculation":
        lead = f"{label} carries the product logic that interprets accepted inputs before anyone treats the result as true."
        calculation_focus = _calculation_focus(
            focus=raw_focus,
            output_focus=raw_output_focus,
            transition_focus=transition_focus,
            label=label,
        )
        has_calculation_result = bool(
            _preferred_calculation_result(_calculation_parts(transition_focus))
            or _preferred_calculation_result(_calculation_parts(raw_output_focus))
            or _preferred_calculation_result(_calculation_parts(raw_focus))
        )
        if has_calculation_result or phrases_too_similar(raw_input_focus, raw_output_focus):
            calculation_subject = _calculation_subject(calculation_focus)
            body = (
                f"It should explain how {calculation_subject} "
                f"{_present_verb(calculation_focus, singular='is', plural='are')} calculated, "
                "which facts were used, and why the result is safe to show."
            )
        else:
            body = f"It should make {input_focus} traceable to {output_focus}, with the rule or calculation context visible enough to review."
    elif role == "reference":
        lead = f"{label} is the source for product reference information used by this release."
        body = f"It should keep {focus} reviewable, explain the source of those facts, and stay separate from user-specific decisions."
    elif role == "configuration":
        lead = f"{label} exists so product rules can change intentionally instead of being hidden in implementation code."
        body = f"It protects {focus} and makes those settings available to the runtime path without turning configuration into a release-review shortcut."
    elif role == "guardrail":
        lead = f"{label} protects the first path when an unsafe, invalid, or blocked condition appears."
        body = f"It should make {focus} explicit enough that the product can stop, recover, or explain the next safe step without hiding the reason."
    elif role == "validation":
        lead = f"{label} checks whether the next product step has the conditions it needs to proceed."
        body = f"It should connect {input_focus} to {output_focus} so readiness is reviewable instead of assumed."
    elif role == "workflow":
        lead = f"{label} coordinates the ordered work that moves the first path forward."
        body = f"It should carry {focus} from one step to the next with blockers, handoffs, and visible progress explainable."
    elif role == "state_store":
        lead = f"{label} keeps the product record together after a participant provides or changes information."
        body = f"It should preserve {focus}, keep the explanation for that state close by, and make the result available without becoming responsible for downstream interpretation."
    elif role == "handoff":
        lead = f"{label} owns the moment work leaves one responsibility and becomes actionable for another actor or component."
        body = f"It keeps {output_focus} connected to the context that produced it, instead of receiving raw upstream details it should not own."
    elif role == "read_model":
        lead = f"{label} is the component that makes accepted product state understandable to a person."
        body = f"It should present {focus} from trusted inputs rather than becoming the owner of the source records it displays."
    elif role == "evidence":
        lead = f"{label} preserves the proof that makes the first release reviewable."
        body = _evidence_opening_body(label=label, focus=focus, output_focus=output_focus)
    elif role == "integration":
        lead = f"{label} is the seam between the product and an outside source or protocol."
        body = f"It should translate {input_focus} into {output_focus} without letting provider-specific behavior leak across the rest of the first release."
    elif role == "recovery":
        lead = f"{label} protects the path when the first attempt is incomplete, wrong, or blocked."
        body = f"It keeps {focus} recoverable so correction and review do not erase the evidence behind the current state."
    else:
        lead = f"{label} is a {noun} for {focus}."
        body = f"It works with {input_focus} and returns {output_focus} only when the local state is ready for the next step."
    intent = f" {accepted_intent}" if accepted_intent else ""
    return _opening_sentences(lead, body, intent.strip())


def _evidence_opening_body(*, label: str, focus: str, output_focus: str) -> str:
    evidence_focus = focus or "the first release"
    result_focus = output_focus or "the result a reviewer needs"
    if phrases_too_similar(evidence_focus, result_focus):
        return (
            f"{label} keeps {evidence_focus} reviewable so the proof can be inspected "
            "without making this component own the decision."
        )
    return (
        f"{label} ties {evidence_focus} to {result_focus} so reviewers can inspect the proof "
        "without making this component own the decision."
    )


def _compact_opening_focus(value: str, *, fallback_noun: str) -> str:
    text = clean_text(value).strip(" .")
    if not text:
        return ""
    parts: list[str] = []
    for part in text_values(text, split_scalar=True, split_commas=True):
        parts.extend(candidate.strip(" .") for candidate in part.split(" and ") if candidate.strip(" ."))
    material = [part for part in parts if len(part.split()) >= 2]
    if len(material) >= 3:
        return f"{material[0]} and related {fallback_noun}"
    return text


def _opening_sentences(*values: str) -> str:
    return "\n\n".join(_sentence(value) for value in values if clean_text(value)).strip()


def _accepted_intent_sentence(value: str, *, label: str) -> str:
    text = clean_text(display_text.strip_inline_markdown_emphasis_tokens(value)).strip(" .")
    if not text or len(text.split()) < 4:
        return ""
    if re.search(
        r"\b(?:component planning record|runtime ownership boundary|structured contract below|proposal text alone)\b",
        text,
        flags=re.I,
    ):
        return ""
    text = re.sub(r"\bFailure\s+avoided\s*:\s*.+$", "", text, flags=re.IGNORECASE).strip(" .")
    action_text = re.sub(r"\s+[—-]\s+", ": ", text, count=1)
    action_text = re.sub(r"\s+", " ", action_text).strip(" .")
    action_needs_structured_cleanup = bool(
        re.match(r"^keeps?\s+", action_text, flags=re.I)
        or re.search(r"\bwhile\s+keeping\b", action_text, flags=re.I)
    )
    if (
        not action_needs_structured_cleanup
        and not _accepted_intent_is_low_signal(action_text)
        and looks_like_finite_action(action_text)
    ):
        return _sentences(
            f"Accepted intent says {label} {_lower_first(action_text)}",
            _accepted_material_terms_sentence(action_text),
        )
    cleaned_fragment = _clean_fragment(text)
    if cleaned_fragment:
        text = cleaned_fragment
    if _accepted_intent_is_low_signal(text):
        return ""
    text = re.sub(r"\s+[—-]\s+", ": ", text, count=1)
    text = re.sub(r"\s+", " ", text).strip(" .")
    relation_sentence = _accepted_relation_sentence(text, label=label)
    if relation_sentence:
        return relation_sentence
    keeping_match = re.match(r"(?P<head>.+?)\s+while\s+keeping\s+(?P<tail>.+)$", text, flags=re.I)
    if keeping_match:
        head = _clean_fragment(keeping_match.group("head"))
        tail = _clean_fragment(keeping_match.group("tail"))
        if head and tail:
            head_sentence = (
                f"Accepted intent says {label} {_lower_first(head)}"
                if looks_like_finite_action(head)
                else f"Accepted intent centers {label} on {_lower_first(head)}"
            )
            return _sentences(
                head_sentence,
                f"It keeps {_lower_first(tail)}",
            )
    keep_match = re.match(r"^keeps?\s+(?P<body>.+)$", text, flags=re.I)
    if keep_match:
        body = _clean_fragment(keep_match.group("body"))
        return _sentence(f"Accepted intent assigns {label} to {_lower_first(body)}") if body else ""
    if looks_like_finite_action(text):
        return _sentences(
            f"Accepted intent says {label} {_lower_first(text)}",
            _accepted_material_terms_sentence(text),
        )
    return _sentences(
        f"Accepted intent centers {label} on {_lower_first(text)}",
        _accepted_material_terms_sentence(text),
    )


def _accepted_material_terms_sentence(value: str) -> str:
    rows = action_object_artifact_phrases(value)
    if not rows:
        return ""
    return f"Material contract terms include {'; '.join(rows[:8])}"


def _accepted_intent_is_low_signal(value: str) -> bool:
    text = clean_text(value).casefold()
    return bool(
        re.search(r"\buser actions?\b", text)
        or re.search(r"\bblocked states?\b", text)
        or re.search(r"\bblocked-case evidence links?\b", text)
        or re.search(r"\bhandoff boundaries for (?:the )?confirmed first path\b", text)
        or re.search(r"\brequired inputs\b.*\bhandoff boundaries\b", text)
        or re.search(r"\bnext-step context\b", text)
    )


def _accepted_relation_sentence(value: str, *, label: str) -> str:
    words = clean_text(value).casefold().strip(" .").split()
    if len(words) < 3 or words[-1].strip(".,;:") not in RELATION_TAIL_WORDS:
        return ""
    body = relation_object_phrase(value)
    if body and len(body.split()) >= 1 and not re.search(r"\b(?:thing|things|stuff)\b", body, flags=re.I):
        return _sentence(f"Accepted intent centers {label} on the stated relationship for {_lower_first(body)}")
    return _sentence(f"Accepted intent centers {label} on the stated relationship between product entities")


def _state_narrative(
    *,
    label: str,
    role: str,
    view: ComponentNarrativeView,
) -> str:
    owned_rows = view.owned_items
    owned = _human_join(owned_rows)
    material_state = _human_join(view.material_state_items)
    accepted_rows = view.accepted_items
    produced_rows = view.produced_items
    accepted = _human_join(accepted_rows)
    produced = _human_join(produced_rows)
    blocker_state = _human_join(view.blocker_state_items)
    transition_rows = view.transition_items
    state_path = _human_join(transition_rows)
    blocker = f"Specific missing or blocked inputs include {blocker_state}" if role in {"entry", "recovery"} and blocker_state else ""
    if role in {"entry", "recovery"}:
        first = f"It owns {owned}." if owned else f"{label} needs the first implementation plan to name its local state."
        second = f"The component can take in {accepted}, but it should only move forward after required values, corrections, or blockers are explicit." if accepted else ""
    elif role in {"decision", "calculation"}:
        if accepted and produced and not phrases_too_similar(accepted, produced):
            first = f"The useful state for {label} is the explanation that connects incoming {accepted} to {produced}."
        else:
            first = f"{label} must keep its input facts, calculation context, and visible result together."
        review_subject = produced or owned or f"{label} result"
        second = f"That link keeps {review_subject} explainable instead of turning the outcome into a black-box claim."
    elif role == "configuration":
        first = f"The owned state is {owned}, and changes to it should read like intentional product policy."
        second = f"The runtime can consume those settings, but configuration itself should not mutate downstream results."
    elif role == "guardrail":
        first = f"The guardrail state is {owned}." if owned else f"{label} needs the first implementation plan to name its stop and recovery state."
        second = f"It evaluates {accepted} and returns {produced} only after the stop, recovery, or safe-next-step reason is explicit." if accepted and produced else ""
    elif role == "validation":
        first = f"The readiness state is {owned}." if owned else f"{label} needs the first implementation plan to name the readiness state it owns."
        second = f"It checks {accepted} and returns {produced} only when the next step can trust the result." if accepted and produced else ""
    elif role == "workflow":
        first = f"The workflow state is {owned}." if owned else f"{label} needs the first implementation plan to name its local workflow state."
        second = f"It accepts {accepted} and produces {produced} as the first path moves forward." if accepted and produced else ""
    elif role == "state_store":
        state_owned = _state_store_owned_text(owned_rows) or owned
        first = f"The owned state is {state_owned}; it should stay close to the inputs and corrections that created it."
        second = f"It accepts {accepted} and returns {produced} only after required information is complete enough to trust."
    elif role == "handoff":
        handoff_state = produced or "the next-step output"
        source_context = accepted or "upstream context"
        first = (
            f"The next-step state is useful only when {handoff_state} "
            f"{_present_verb(handoff_state, singular='travels', plural='travel')} with enough context from {source_context}."
        )
        second = "Raw input fields should remain with their owner; this component should carry the context another participant needs."
    elif role == "read_model":
        first = f"The visible state should explain {owned} without pretending to own every source record."
        second = f"It can render {produced}, while stale, empty, or blocked states remain visible."
    elif role == "evidence":
        first = f"The evidence state should keep {owned} connected to the result being reviewed."
        second = f"It accepts {accepted} and returns {produced} only when the review trail remains explainable."
    else:
        first = f"The useful local state is {owned}."
        second = f"It accepts {accepted} and returns {produced} when the next product step can rely on it."
    material = _material_state_sentence(label=label, role=role, material_state=material_state)
    material_contract = _material_contract_sentence(label=label, view=view)
    transition = _transition_sentence(label=label, view=view, text=state_path)
    return _sentences(first, second, blocker, material, material_contract, transition)


def _material_contract_sentence(*, label: str, view: ComponentNarrativeView) -> str:
    rows = [row for row in (*view.blocker_state_items, *view.material_state_items) if row]
    rows = list(unique_text(rows))
    if not rows:
        return ""
    return f"{label} also needs material checks for {'; '.join(rows[:4])}"


def _transition_sentence(*, label: str, view: ComponentNarrativeView, text: str) -> str:
    if not text:
        return ""
    if len(view.transition_items) > 5 or text.count(",") >= 3 or len(text) > 180:
        transition_summary = _short_transition_summary(view.transition_items)
        if transition_summary:
            return f"The lifecycle for {label} includes {transition_summary}."
        return (
            f"The lifecycle for {label} should make accepted, blocked, corrected, completed, "
            "and handed-off states explicit before implementation expands."
        )
    if view.concrete_transition_items or view.material_transition_count >= 4:
        return f"The important lifecycle for {label} is {text}."
    if len(view.transition_items) > 7 or len(view.short_transition_items) >= max(4, len(view.transition_items) // 2):
        return (
            f"The lifecycle for {label} should make accepted, blocked, corrected, completed, "
            "and handed-off states explicit before implementation expands."
        )
    if len(text) <= 260:
        return f"The important lifecycle for {label} is {text}."
    return f"The important lifecycle for {label} is {text}."


def _short_transition_summary(values: Sequence[str]) -> str:
    rows = [clean_text(value).strip(" .") for value in values if clean_text(value).strip(" .")]
    if not rows:
        return ""
    selected = rows[:12]
    if sum(1 for row in selected if row.casefold().endswith(" state")) >= 2:
        return ""
    if any(len(row.split()) > 4 or len(row) > 48 for row in selected):
        return ""
    return "; ".join(selected)


def _boundary_narrative(
    *,
    label: str,
    role: str,
    upstream: str,
    downstream: str,
    input_focus: str,
    output_focus: str,
    outside: Sequence[str],
) -> str:
    upstream_text = _boundary_entity_text(re.sub(r"^The\s+next\b", "the next", upstream).strip())
    downstream_text = _boundary_entity_text(re.sub(r"^The\s+next\b", "the next", downstream).strip())
    kept = _outside_boundary_scope_items(outside)
    outside_text = _human_join(kept[:4])
    if upstream_text and downstream_text and _has_no_source_dependency(upstream_text):
        relation = (
            f"{label} has no claimed source dependency yet and prepares work for {downstream_text}. "
            f"The handoff from {label} to {downstream_text} keeps upstream ownership and downstream responsibility separate."
        )
    elif upstream_text and downstream_text:
        relation = (
            f"This boundary for {label} receives its trusted context from {upstream_text} and prepares work for {downstream_text}. "
            f"The handoff from {label} to {downstream_text} keeps upstream ownership and downstream responsibility separate."
        )
    elif upstream_text:
        relation = f"{label} starts from {upstream_text} and keeps that input relationship visible."
    elif downstream_text:
        relation = f"{label} prepares state for {downstream_text} and should not hide blockers from the next step."
    else:
        relation = f"{label} must keep its state, validation result, blocker state, and evidence together."
    if not kept:
        boundary = f"Unrelated input truth, release approval, and adjacent component state stay outside the {label} boundary."
    elif role == "configuration":
        boundary = f"{label} keeps {outside_text} outside the {label} boundary so administrative policy does not become hidden runtime authority."
    elif role == "state_store":
        boundary = f"{label} keeps {outside_text} outside the {label} boundary so this component stores the product record without taking over adjacent decisions."
    elif role == "read_model":
        boundary = f"{label} keeps {outside_text} outside the {label} boundary so display logic does not rewrite original input facts."
    else:
        boundary = f"{label} keeps {outside_text} outside the {label} boundary unless a later release explicitly assigns it here."
    upstream_separation = _upstream_handoff_separation_sentence(label=label, upstream=upstream_text, input_focus=input_focus)
    downstream_separation = _downstream_handoff_separation_sentence(label=label, downstream=downstream_text, output_focus=output_focus)
    return _sentences(relation, upstream_separation, downstream_separation, boundary)


_GENERIC_OUTSIDE_BOUNDARY_TERMS = frozenset(
    {
        "capture allowed command",
        "guide path",
        "release approval",
        "runtime implementation",
        "silent overwrite",
    }
)


def _outside_boundary_scope_items(outside: Sequence[str]) -> tuple[str, ...]:
    """Keep material sibling ownership while removing generic release-process noise."""

    rows: list[str] = []
    for item in outside:
        text = clean_text(item).strip(" .")
        if not text:
            continue
        candidates = _split_boundary_scope_item(text) if _has_generic_outside_boundary_term(text) else (text,)
        for candidate in candidates:
            cleaned = _clean_fragment(candidate)
            if cleaned and not _has_generic_outside_boundary_term(cleaned):
                rows.append(cleaned)
    return unique_text(rows)


def _has_generic_outside_boundary_term(value: str) -> bool:
    text = clean_text(value).casefold()
    return any(term in text for term in _GENERIC_OUTSIDE_BOUNDARY_TERMS)


def _split_boundary_scope_item(value: str) -> tuple[str, ...]:
    text = clean_text(value).strip(" .")
    if not text:
        return ()
    rows: list[str] = []
    for comma_part in text.split(","):
        rows.extend(part.strip(" .") for part in comma_part.split(" and ") if part.strip(" ."))
    return tuple(rows)


def _upstream_handoff_separation_sentence(*, label: str, upstream: str, input_focus: str) -> str:
    owner = re.sub(
        r"\s+ownership(?:\s+of\s+local\s+state)?\.?$",
        "",
        _boundary_entity_text(upstream).strip(" ."),
        flags=re.I,
    )
    subject = _primary_boundary_subject(input_focus)
    if not owner or not subject or _has_no_source_dependency(upstream):
        return ""
    return f"It can consume {subject} for {label} while leaving state ownership with {owner}."


def _downstream_handoff_separation_sentence(*, label: str, downstream: str, output_focus: str) -> str:
    consumer = _boundary_entity_text(downstream).strip(" .")
    subject = _primary_boundary_subject(output_focus)
    if not consumer or not subject:
        return ""
    if consumer.casefold() in {"release review", "the next product boundary and release proof review"}:
        return ""
    return f"{consumer} can consume {subject} while {label} keeps ownership of its state."


def _primary_boundary_subject(value: str) -> str:
    text = clean_text(value).strip(" .")
    if not text:
        return ""
    text = re.split(r",|\s+\band\b\s+", text, maxsplit=1, flags=re.I)[0].strip(" .")
    if text.casefold() in {"prior state", "explanation context", "validation context", "the inputs required for this boundary"}:
        return ""
    return text


_BOUNDARY_ENTITY_SUFFIXES = frozenset(
    {
        "adapter",
        "catalog",
        "check",
        "console",
        "controller",
        "dashboard",
        "engine",
        "ledger",
        "log",
        "model",
        "portal",
        "registry",
        "repository",
        "service",
        "store",
        "tracker",
        "view",
        "workflow",
    }
)
_BOUNDARY_ENTITY_CONNECTORS = frozenset({"a", "an", "and", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"})


def _boundary_entity_text(value: str) -> str:
    text = clean_text(value).strip(" .")
    if not text:
        return ""
    match = re.match(r"(?P<label>.+?)\s+(?P<tail>ownership(?:\s+of\s+local\s+state)?)$", text, flags=re.I)
    label = clean_text(match.group("label")) if match else text
    tail = f" {match.group('tail')}" if match else ""
    if not _looks_like_boundary_component_label(label):
        return text
    return f"{_component_label_text(label)}{tail}"


def _looks_like_boundary_component_label(value: str) -> bool:
    words = clean_text(value).split()
    if len(words) < 2:
        return False
    title_word_count = sum(1 for word in words if word[:1].isupper())
    last = words[-1].casefold().strip(".,;:")
    if last in _BOUNDARY_ENTITY_SUFFIXES and title_word_count >= 2:
        return True
    return title_word_count >= 2


def _component_label_text(value: str) -> str:
    words = clean_text(value).split()
    rendered: list[str] = []
    for index, word in enumerate(words):
        token = word.strip(".,;:")
        lowered = token.casefold()
        if 0 < index < len(words) - 1 and lowered in _BOUNDARY_ENTITY_CONNECTORS:
            rendered.append(lowered)
            continue
        rendered.append(_component_label_token(token))
    return " ".join(rendered)


def _component_label_token(value: str) -> str:
    if not value:
        return ""
    if value.isupper() or any(char.isdigit() for char in value):
        return value
    if "-" in value:
        return "-".join(_component_label_token(part) for part in value.split("-"))
    return value[:1].upper() + value[1:]


def _has_no_source_dependency(value: str) -> bool:
    text = clean_text(value).casefold()
    return "no source dependency" in text or "no live source dependency" in text


def _proof_narrative(*, label: str, role: str, failure: str, proofs: Sequence[str]) -> str:
    risk = (
        f"The product failure to guard against: {failure}"
        if failure
        else f"The product failure to guard against: treating the {label} as ready without local behavior proof"
    )
    selected = [
        _clean_proof_sentence(proof, label=label, index=index)
        for index, proof in enumerate(_selected_proof_rows(proofs), start=1)
    ]
    selected = [row for row in selected if row]
    if selected:
        proof_text = " ".join(selected)
    elif role == "read_model":
        proof_text = f"Promotion should show a normal view, an empty or stale view, and a blocked view with source context intact."
    elif role == "decision":
        proof_text = f"Promotion should show one accepted outcome, one blocked outcome, and one replay where the explanation still matches the inputs."
    else:
        proof_text = f"Promotion should show one accepted path, one blocked path, and one replay path before downstream work depends on {label}."
    return _sentences(risk, proof_text)


def _selected_proof_rows(proofs: Sequence[str]) -> tuple[str, ...]:
    rows = [clean_text(proof).strip() for proof in proofs if clean_text(proof).strip()]
    selected: list[str] = []
    for prefix in (
        "Successful path evidence",
        "Blocked input evidence",
        "Replay evidence",
        "Access evidence",
        "Freshness evidence",
        "Handoff evidence",
        "Proof boundary evidence",
    ):
        match = next((row for row in rows if row.casefold().startswith(prefix.casefold())), "")
        if match:
            selected.append(match)
    selected.extend(rows)
    return tuple(unique_text(selected)[:7])


def _implementation_narrative(
    *,
    label: str,
    role: str,
    source_boundary: str,
    first_workstream: str,
    first_workstream_title: str,
    first_slice: str,
    release_selector: str,
    wave_label: str,
) -> str:
    if role == "configuration":
        opening = f"Start with the smallest source boundary that can hold {label}'s policy state: {source_boundary}."
    elif role == "state_store":
        opening = f"Start with the smallest source boundary that can persist and validate {label}'s product record: {source_boundary}."
    elif role == "read_model":
        opening = f"Start where {label} can render trusted state without duplicating upstream ownership: {source_boundary}."
    else:
        opening = f"Start in {source_boundary}."
    parts = [opening]
    if first_workstream:
        title = f" ({first_workstream_title})" if first_workstream_title else ""
        parts.append(f"Implementation anchor for {label}: {first_workstream}{title}.")
    if first_slice:
        parts.append(first_slice)
    if wave_label:
        parts.append(f"Release wave: {wave_label}.")
    if release_selector:
        parts.append(f"Release target: {release_selector}.")
    return " ".join(_sentence(part) for part in parts if part).strip()


def _clean_proof_sentence(proof: str, *, label: str, index: int) -> str:
    canonical = _canonical_proof_sentence(proof)
    if canonical:
        return canonical
    text = _sentence(_naturalize_proof_carrier_hyphens(_clean_fragment(proof, proof=True))).rstrip(".")
    if not text:
        return ""
    text = re.sub(
        rf"^Run one {re.escape(label)} example with a clear explanation for (.+)$",
        rf"{label} shows \1 on a successful path with enough explanation for a reviewer to understand it",
        text,
        flags=re.I,
    )
    text = re.sub(
        rf"^Run one blocked {re.escape(label)} example where missing or malformed input explains what must change before the result can be trusted$",
        rf"When required input is missing or malformed, {label} stops before showing a trusted result and explains what must change",
        text,
        flags=re.I,
    )
    text = re.sub(
        rf"^Replay one {re.escape(label)} result and confirm the actor, input facts, status, and explanation still agree$",
        rf"A replay of {label} still connects the actor, input facts, status, and explanation",
        text,
        flags=re.I,
    )
    text = re.sub(
        rf"^Replay evidence for {re.escape(label)}:\s*actor,\s*input facts,\s*status,\s*explanation\b.*$",
        rf"Replay evidence for {label}: A replay of {label} still connects the actor, input facts, status, and explanation",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"\bmissing,\s*stale,\s*unauthorized,\s*or\s*malformed\s+input\b",
        "the named bad input",
        text,
        flags=re.I,
    )
    return _sentence(text)


def _contract_items(contract: Mapping[str, Any], key: str) -> tuple[str, ...]:
    values: list[str] = []
    for raw in text_values(contract.get(key), split_scalar=True, split_commas=True, strip_bullets=True):
        cleaned = _clean_transition_fragment(raw) if key == "states_or_transitions" else _clean_fragment(raw)
        if cleaned:
            values.append(cleaned)
    return unique_text(values)


def _clean_transition_fragment(value: Any) -> str:
    text = clean_text(display_text.strip_inline_markdown_emphasis_tokens(str(value or "")))
    text = normalize_action_splice_phrase(re.sub(r"\s+", " ", text).strip(" .;:,"))
    return _lower_first(text) if text else ""


def _proof_items(value: Any) -> tuple[str, ...]:
    values: list[str] = []
    for raw in text_values(value):
        canonical = _canonical_proof_sentence(raw)
        if canonical:
            values.append(canonical)
            continue
        cleaned = _clean_fragment(raw, proof=True)
        if cleaned:
            values.append(_sentence(cleaned))
    return unique_text(values)


def _canonical_proof_sentence(value: Any) -> str:
    text = clean_text(display_text.strip_inline_markdown_emphasis_tokens(str(value or ""))).strip(" .;:")
    text = _naturalize_proof_carrier_hyphens(text)
    if not re.match(
        r"^(?:Successful path evidence|Blocked input evidence|Replay evidence|Handoff evidence|Access evidence|Freshness evidence)\s+for\b",
        text,
        flags=re.I,
    ):
        return ""
    return _sentence(text)


def _naturalize_proof_carrier_hyphens(value: str) -> str:
    return re.sub(
        r"\b([A-Za-z][A-Za-z0-9]*)-(context|record|state|status|history|evidence|decision|identity|material|materials)\b",
        r"\1 \2",
        clean_text(value),
        flags=re.IGNORECASE,
    )


def _clean_fragment(value: Any, *, proof: bool = False) -> str:
    text = clean_text(display_text.strip_inline_markdown_emphasis_tokens(str(value or "")))
    text = re.sub(r"^[-*]\s*", "", text).strip(" .;:")
    if proof and re.match(r"^contract\s+proof\s+covers\b", text, flags=re.I):
        return text
    text = re.sub(r"\bRelated path\s*:\s*[^.;]+[.;]?", "", text, flags=re.I)
    text = re.sub(r"\b(?:Done|DoD)\s+mean(?:s)?\b", "", text, flags=re.I)
    text = re.sub(r"\bMean(?:s)?\s*:\s*[a-z][^.;,]*", "", text, flags=re.I)
    text = re.sub(r"\breadout\s+plus\b", "readout and", text, flags=re.I)
    text = re.sub(r"\bon\s+screen,\s+alongside\b", "on screen with", text, flags=re.I)
    text = re.sub(r"\balongside\b", "with", text, flags=re.I)
    text = re.sub(r"\bdashboard\s+visibly\s+update\s+suggestion\b", "dashboard suggestion state", text, flags=re.I)
    text = re.sub(r"\bmutation\s+of\s+upstream\s+source\s+truth\b", "mutation of original input facts", text, flags=re.I)
    leading_modifiers = "validated|candidate|selected|ranked|authorized"
    if "completeness" not in text.casefold():
        leading_modifiers = f"required|{leading_modifiers}"
    text = re.sub(rf"^(?:{leading_modifiers})\s+", "", text, flags=re.I)
    text = re.sub(
        r"^(?:refused domain responsibilities|sibling-owned state|forbidden runtime authorities)\s*:\s*",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(r"^[A-Z][A-Za-z0-9]*(?:\s+[A-Z][A-Za-z0-9]*){0,5}\s+owns\s+", "", text)
    text = re.sub(r"^[a-z0-9][a-z0-9 -]{0,80}\s+owns\s+", "", text, flags=re.I)
    text = re.sub(
        r"^(?:owns?|accepts?|produces?|returns?|return|depends\s+on|coordinates\s+with|computes?|evaluates?|explains?|validates?|captures?)\s+",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(r"\b(?:and\s+)?keeps?\s+the\s+next\s+visible\s+step\s+tied\s+to\s*:\s*.+$", "next-step context", text, flags=re.I)
    text = re.sub(r"\btied\s+to\s*:\s*.+$", "", text, flags=re.I)
    text = re.sub(r"\b(?:producing|recording|capturing|tracking|reviewing|showing|returning)\s+the\s+", "", text, flags=re.I)
    text = re.sub(r"\b(?:producing|recording|capturing|tracking|reviewing|showing|returning)\s+", "", text, flags=re.I)
    text = re.sub(r"\busing\s+(?:mocked|stubbed|simulated)\b.*$", "", text, flags=re.I)
    text = re.sub(r"^guides?\s+the\s+first\s+path,?\s*", "", text, flags=re.I)
    text = re.sub(r"^keep(?:s|ing)?\s+", "", text, flags=re.I)
    text = re.sub(r"\bexplicit(?:ly)?\b", "", text, flags=re.I)
    text = normalize_action_splice_phrase(text)
    text = re.sub(r"^(?:them|it|their|they|this|that)\s+(?:against|with|to|from|for|into)\s+", "", text, flags=re.I)
    text = re.sub(r"^(?:against|with|to|from|for|into)\s+", "", text, flags=re.I)
    text = _drop_unanchored_pronouns(text)
    text = re.sub(
        r"\bbefore\s+(creates?|presents?|shows?|returns?|produces?)\b",
        r"before it \1",
        text,
        flags=re.I,
    )
    text = re.sub(r"\s+", " ", text).strip(" .;:,")
    text = normalize_artifact_tail(text, carrier_terms=_CONTRACT_CARRIER_TERMS)
    if not text:
        return ""
    lowered = text.casefold()
    if re.search(r"\b(?:runs?|evaluates?|checks?|computes?)\s+(?:it|them|their|they)\b", lowered):
        return ""
    if re.match(r"^(?:and|or|their|they|them|it|this|that|who|which|where)\b", lowered):
        return ""
    if not proof and re.fullmatch(r"(?:actions?|user actions?|local blockers?|handoff evidence|source evidence|prior state|prior result|authorized actor|validation command|validation context|validation notes?|next-step context|blocker state|blocked states?)", lowered):
        return ""
    if re.search(r"\bresponsibilities\s+not\s+named\s+by\s+(?:this\s+)?component\s+boundary\b", lowered):
        return ""
    if len(text.split()) <= 2 and lowered in {"state", "command", "record", "result", "evidence", "handoff"}:
        return ""
    return _lower_first(text)


def _failure_fragment(value: Any) -> str:
    text = clean_text(display_text.strip_inline_markdown_emphasis_tokens(str(value or "")))
    text = re.sub(r"^[-*]\s*", "", text).strip(" .;:")
    text = re.sub(r"\bRelated path\s*:\s*[^.;]+[.;]?", "", text, flags=re.I)
    text = re.sub(r"\b(?:Done|DoD)\s+mean(?:s)?\s*:?\s*", "", text, flags=re.I).strip(" .;:")
    text = re.sub(r"\s+", " ", text).strip(" .;:,")
    return repair_modal_base_form_drift(text)


def _drop_unanchored_pronouns(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        previous = str(match.group("previous") or "")
        pronoun = str(match.group("pronoun") or "")
        previous_word = previous.strip().casefold()
        if previous_word in _PRONOUN_OBJECT_PRECEDERS:
            return f"{previous}{pronoun}"
        return previous

    return re.sub(
        r"(?P<previous>\b[A-Za-z][A-Za-z'-]*\s+)?\b(?P<pronoun>them|it|their|they|this|that)\b(?!\s+(?:are|is|was|were)\b)",
        replace,
        value,
        flags=re.I,
    )


def _entity_text(value: Any) -> str:
    rows = [_clean_entity_item(item) for item in text_values(value, split_scalar=True, split_commas=True, strip_bullets=True)]
    rows = [row for row in rows if row]
    return _human_join(rows[:4])


def _clean_entity_item(value: str) -> str:
    text = _clean_fragment(value)
    if not text:
        return ""
    if text.casefold() == "accepted input context":
        return "accepted first-path input"
    return text[:1].upper() + text[1:] if re.match(r"^[a-z]", text) and re.search(r"\b[A-Z][a-z]", value) else text


_CONTRACT_CARRIER_TERMS = {
    "answer", "case", "channel", "command", "data", "decision", "detail", "entry", "event", "evidence", "field", "history",
    "input", "intake", "ledger", "log", "note", "outcome", "output", "readiness", "record", "request", "result",
    "review", "score", "state", "status", "summary", "timeline", "view",
}


def _fallback_phrase(values: Sequence[str], fallback: str) -> str:
    rows = narrative_items(values, limit=3)
    return _human_join(rows) if rows else _lower_first(fallback)


def _material_state_sentence(*, label: str, role: str, material_state: str) -> str:
    if not material_state:
        return ""
    if role == "read_model":
        return f"{label} should also keep {material_state} visible enough for someone to understand the view"
    if role == "state_store":
        if re.search(r"\battached\b$", material_state, flags=re.IGNORECASE):
            record_state = re.sub(r"\battached\b$", "", material_state, flags=re.IGNORECASE).strip(" ,")
            record_state = record_state or material_state
            return f"{label} should also keep {record_state} in the record instead of leaving those facts implicit"
        return f"{label} should also keep {material_state} attached to the record instead of leaving those facts implicit"
    if role == "evidence":
        return f"{label} should also keep {material_state} connected to the evidence trail"
    if role in {"entry", "recovery"}:
        return f"{label} should also keep {material_state} visible before the path moves on"
    return f"{label} should also keep {material_state} visible enough to review"


def _present_verb(subject: str, *, singular: str, plural: str) -> str:
    text = clean_text(subject).casefold()
    if " and " in text or "," in text:
        return plural
    if re.search(r"\b(?:items|outputs|records|results|states|details|fields|entries|events|requests)\b", text):
        return plural
    return singular


def _human_join(values: Sequence[str]) -> str:
    rows = [str(item).strip(" .") for item in values if str(item).strip(" .")]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def _state_store_owned_text(values: Sequence[str]) -> str:
    rows = [str(item).strip(" .") for item in values if str(item).strip(" .")]
    if len(rows) >= 3 and rows[-1].casefold().endswith((" result", " update")):
        return f"{_human_join(rows[:-1])}, with {rows[-1]}"
    return _human_join(rows)


def _calculation_focus(*, focus: str, output_focus: str, transition_focus: str, label: str) -> str:
    transition_parts = _calculation_parts(transition_focus)
    output_parts = _calculation_parts(output_focus)
    focus_parts = _calculation_parts(focus)
    preferred = (
        _preferred_calculation_result(transition_parts)
        or _preferred_calculation_result(output_parts)
        or _preferred_calculation_result(focus_parts)
    )
    if preferred:
        return preferred
    noun_parts = [part for part in focus_parts if not contains_finite_action(part)]
    if noun_parts:
        return _human_join(noun_parts[:3])
    if output_focus and not contains_finite_action(output_focus):
        return output_focus
    return re.sub(r"\b(?:adapter|component|engine|service|system|view)\b$", "", label, flags=re.I).strip(" .") or "the result"


def _calculation_transition_focus(values: Sequence[str]) -> str:
    candidates = [
        _calculation_result_subject(
            re.sub(
                r"\s+(?:accepted|blocked|calculated|computed|converted|created|generated|logged|"
                r"received|returned|shown|updated|validated)\b$",
                "",
                clean_text(value).strip(" ."),
                flags=re.I,
            )
        )
        for value in values
        if clean_text(value)
    ]
    return _preferred_calculation_result(candidates)


def _calculation_parts(value: str) -> list[str]:
    text = clean_text(value).replace(", and ", ",")
    return [part.strip(" .") for part in text.split(",") if part.strip(" .")]


def _preferred_calculation_result(values: Sequence[str]) -> str:
    best_score = 0
    best = ""
    for value in values:
        text = clean_text(value).strip(" .")
        if not text or contains_finite_action(text):
            continue
        words = {word.casefold().strip(".,;:") for word in text.split() if word.strip(".,;:")}
        score = len(words & _CALCULATION_RESULT_TERMS) * 10
        if "result" in words:
            score += 20
        if "recommendation" in words or "decision" in words:
            score += 12
        if score > best_score:
            best_score = score
            best = text
    return best


def _calculation_subject(value: str) -> str:
    text = _calculation_result_subject(clean_text(value).strip(" .")) or "result"
    first_word = text.split(maxsplit=1)[0].casefold().strip(".,;:")
    if first_word in {"a", "an", "the", "this", "that", "these", "those"}:
        return text
    if text[:1].islower():
        return f"the {text}"
    return text


def _calculation_result_subject(value: str) -> str:
    text = clean_text(value).strip(" .")
    if not text:
        return ""
    text = re.sub(
        r"\s+(?:evidence|proof|record|artifact|trace|trail)\b$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .")
    return text


_CALCULATION_RESULT_TERMS = {
    "answer",
    "decision",
    "estimate",
    "number",
    "outcome",
    "output",
    "recommendation",
    "result",
    "score",
    "summary",
}


def _finalize_narrative_spec_text(value: str) -> str:
    text = collapse_adjacent_duplicate_terms(value)
    text = repair_modal_base_form_drift(text)
    return re.sub(r",\s+(?=(?:When|If|While)\b)", ". ", text)


def _sentences(*values: str) -> str:
    return " ".join(_sentence(value) for value in values if clean_text(value)).strip()


def _sentence(value: str) -> str:
    text = clean_text(value).strip(" .;:,")
    if not text:
        return ""
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r",\s+(?=(?:When|If|While)\b)", ". ", text)
    text = text.rstrip(" .;:,")
    if not text:
        return ""
    return f"{text[:1].upper()}{text[1:]}."


def _lower_first(value: str) -> str:
    text = clean_text(value).strip(" .")
    if not text:
        return ""
    if len(text) > 1 and text[:2].isupper():
        return text
    return f"{text[:1].lower()}{text[1:]}"


def _kind_noun(kind: str) -> str:
    token = str(kind or "").strip().casefold()
    if token in {"application", "client", "surface", "ui", "frontend", "web"}:
        return "user-facing surface"
    if token in {"tooling", "test", "harness"}:
        return "proof harness"
    if token in {"integration", "adapter"}:
        return "integration boundary"
    if token in {"library", "module"}:
        return "module boundary"
    return "service boundary"


def _identifier_list(values: Sequence[str]) -> str:
    rows = [str(item).strip().upper() for item in values if str(item).strip()]
    return ", ".join(rows)


def _first(values: Sequence[str]) -> str:
    for value in values:
        text = str(value or "").strip().upper()
        if text:
            return text
    return ""


def _plan_link(workstream_id: str) -> str:
    token = str(workstream_id or "").strip().upper()
    if not re.fullmatch(r"B-\d{3,}", token):
        return ""
    return f" (Plan: [{token}](odylith/radar/radar.html?view=plan&workstream={token}))"


def _handoff_text(handoff: Mapping[str, Any], key: str) -> str:
    value = handoff.get(key)
    return clean_text(value) if value is not None else ""
