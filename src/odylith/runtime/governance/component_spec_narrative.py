"""Narrative Registry spec renderer for greenfield component contracts."""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common import display_text
from odylith.runtime.common.prose_grammar import contains_finite_action
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_text import clean_text, text_values, unique_text


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
    failure = _sentence(_clean_fragment(component_contract.get("unique_failure")))
    accepted_intent = _accepted_intent_sentence(responsibility)

    focus = _fallback_phrase(owns, label)
    input_focus = _fallback_phrase(accepts, "the inputs required for this boundary")
    output_focus = _fallback_phrase(produces, "the output that downstream work depends on")
    first_workstream = _handoff_text(handoff, "workstream_id") or _first(workstreams)
    first_workstream_title = _handoff_text(handoff, "workstream_title")
    first_slice = _sentence(_handoff_text(handoff, "first_slice"))
    release_selector = _handoff_text(handoff, "release_selector")
    wave_label = _handoff_text(handoff, "wave_label")
    source_boundary = path or "selected by the first implementation plan"
    role = _narrative_role(
        label=label,
        owns=owns,
        accepts=accepts,
        produces=produces,
        transitions=transitions,
        outside=outside,
        proofs=proofs,
    )

    lines = [
        f"# {label}",
        "",
        _planning_note(sources=sources, path=path, workstreams=workstreams, diagrams=diagrams),
        "",
        _opening_narrative(
            label=label,
            kind=kind,
            role=role,
            focus=focus,
            input_focus=input_focus,
            output_focus=output_focus,
            accepted_intent=accepted_intent,
        ),
        "",
        _state_narrative(
            label=label,
            role=role,
            owns=owns,
            accepts=accepts,
            produces=produces,
            transitions=transitions,
        ),
        "",
        _boundary_narrative(
            label=label,
            role=role,
            upstream=upstream,
            downstream=downstream,
            outside=outside,
        ),
        "",
        _proof_narrative(label=label, role=role, failure=failure, proofs=proofs),
        "",
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
        "",
        "## Feature History",
        "",
        f"- {dt.date.today().isoformat()}: Registered {label} as a {status or 'planned'} {kind or 'component'} from user intent{_plan_link(first_workstream)}.",
        "",
    ]
    return "\n".join(line for line in lines if line is not None)


def _planning_note(
    *,
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
    trace_text = f" Trace links: {', '.join(trace)}." if trace else ""
    return f"> Planned from {evidence}.{source}{trace_text}"


def _narrative_role(
    *,
    label: str,
    owns: Sequence[str],
    accepts: Sequence[str],
    produces: Sequence[str],
    transitions: Sequence[str],
    outside: Sequence[str],
    proofs: Sequence[str],
) -> str:
    text = " ".join([label, *_string_rows(owns), *_string_rows(accepts), *_string_rows(produces), *_string_rows(transitions), *_string_rows(outside), *_string_rows(proofs)]).casefold()
    label_text = label.casefold()
    if re.search(r"\b(catalog|knowledge|reference)\b", label_text):
        return "reference"
    if re.search(r"\b(store|repository|record|records|profile|registry|history|log|logging|tracking)\b", label_text):
        return "state_store"
    if re.search(r"\b(audit|evidence|file|ledger|provenance|trail)\b", label_text):
        return "evidence"
    if re.search(r"\b(config|configuration|admin|administrator|policy|setting)\b", label_text):
        return "configuration"
    if re.search(r"\b(view|timeline|dashboard|summary|report|export|surface|display|history|trend)\b", label_text):
        return "read_model"
    if re.search(r"\b(decision|outcome|reason|approve|approval|decline|explain|rationale|recommendation)\b", label_text):
        return "decision"
    if re.search(r"\b(compute|calculation|calculator|engine|score|rank|compare|threshold|ratio|rule|eligibility|pricing)\b", label_text):
        return "calculation"
    if re.search(r"\b(queue|route|routing|handoff|follow-up|notification|assignment|case)\b", label_text):
        return "handoff"
    if re.search(r"\b(intake|capture|entry|submit|upload|log|record|draft)\b", label_text):
        return "entry"
    role_patterns = (
        ("read_model", r"\b(view|timeline|dashboard|summary|report|export|surface|display|history|trend)\b"),
        ("decision", r"\b(decision|outcome|reason|approve|approval|decline|qualified|eligible|explain|rationale|recommendation)\b"),
        ("calculation", r"\b(compute|calculate|evaluate|score|rank|compare|threshold|ratio|rule|eligibility|pricing)\b"),
        ("configuration", r"\b(config|configuration|admin|administrator|policy|rule|threshold|template|setting)\b"),
        ("state_store", r"\b(store|repository|record|records|profile|history|log|persist|saved|stored)\b"),
        ("handoff", r"\b(queue|route|routing|handoff|follow-up|notification|assignment|case)\b"),
        ("evidence", r"\b(audit|evidence|provenance|source|replay|retention|version|history|attachment)\b"),
        ("recovery", r"\b(edit|correction|recover|revision|blocked|blocker|stale|missing|invalid)\b"),
        ("integration", r"\b(adapter|provider|external|import|feed|integration|sync)\b"),
        ("entry", r"\b(intake|capture|entry|submit|submitted|upload|log|record|draft|required field|input)\b"),
    )
    for role, pattern in role_patterns:
        if re.search(pattern, text):
            return role
    return "service"


def _opening_narrative(
    *,
    label: str,
    kind: str,
    role: str,
    focus: str,
    input_focus: str,
    output_focus: str,
    accepted_intent: str,
) -> str:
    noun = _kind_noun(kind)
    if role == "entry":
        lead = f"{label} is responsible for the first product information this boundary must make reliable."
        body = f"It keeps {focus} together so the next product step can move forward without another boundary guessing what the user meant or what is still missing."
    elif role == "decision":
        lead = f"{label} turns prepared evidence into a product outcome with an explanation."
        body = f"The spec should stay focused on {output_focus}, because downstream work needs to know not only what happened but why it happened."
    elif role == "calculation":
        lead = f"{label} carries the product logic that interprets accepted inputs before anyone treats the result as true."
        if _phrases_too_similar(input_focus, output_focus):
            calculation_focus = _calculation_focus(focus=focus, output_focus=output_focus, label=label)
            body = (
                f"It should explain how {calculation_focus} "
                f"{_present_verb(calculation_focus, singular='is', plural='are')} calculated, "
                "which facts were used, and why the result is safe to show."
            )
        else:
            body = f"It should make {input_focus} traceable to {output_focus}, with the rule or calculation context visible enough to review."
    elif role == "reference":
        lead = f"{label} is the source for product reference information used by this release."
        body = f"It should keep {focus} reviewable, explain where those facts came from, and stay separate from user-specific decisions."
    elif role == "configuration":
        lead = f"{label} exists so product rules can change intentionally instead of being hidden in implementation code."
        body = f"It protects {focus} and makes those settings available to the runtime path without turning configuration into a release-review shortcut."
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
        lead = f"{label} preserves the evidence that makes the first release reviewable."
        body = f"Its job is to keep {focus} tied to the result a reviewer needs to understand, without turning the evidence record into the decision owner."
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
    return _sentences(lead, body, intent.strip())


def _accepted_intent_sentence(value: str) -> str:
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
    cleaned_fragment = _clean_fragment(text)
    if cleaned_fragment:
        text = cleaned_fragment
    if _accepted_intent_is_low_signal(text):
        return ""
    text = re.sub(r"\s+[—-]\s+", ": ", text, count=1)
    text = re.sub(r"\s+", " ", text).strip(" .")
    keep_match = re.match(r"^keeps?\s+(?P<body>.+)$", text, flags=re.I)
    if keep_match:
        body = _clean_fragment(keep_match.group("body"))
        return _sentence(f"Accepted intent assigns this component to {_lower_first(body)}") if body else ""
    if looks_like_finite_action(text):
        return _sentence(f"Accepted intent says this component {_lower_first(text)}")
    return _sentence(f"Accepted intent centers this component on {_lower_first(text)}")


def _accepted_intent_is_low_signal(value: str) -> bool:
    text = clean_text(value).casefold()
    return bool(
        re.search(r"\buser actions?\b", text)
        or re.search(r"\bblocked states?\b", text)
        or re.search(r"\bnext-step context\b", text)
    )


def _state_narrative(
    *,
    label: str,
    role: str,
    owns: Sequence[str],
    accepts: Sequence[str],
    produces: Sequence[str],
    transitions: Sequence[str],
) -> str:
    owned_rows = _narrative_items(owns, limit=4)
    owned = _human_join(owned_rows)
    material_state = _human_join(_supplemental_state_items(owns, existing=owned_rows, limit=5))
    accepted_rows = _narrative_items(accepts, limit=3)
    produced_rows = _narrative_items(produces, limit=3)
    accepted = _human_join(accepted_rows)
    produced = _human_join(produced_rows)
    blocker_state = _human_join(_supplemental_state_items([*accepts, *produces], existing=(*owned_rows, *accepted_rows, *produced_rows), limit=3))
    state_path = _human_join(_transition_items(transitions, limit=12))
    blocker = f"Specific missing or blocked inputs include {blocker_state}" if role in {"entry", "recovery"} and blocker_state else ""
    if role in {"entry", "recovery"}:
        first = f"It owns {owned}." if owned else f"{label} needs the first implementation plan to name its local state."
        second = f"The component can take in {accepted}, but it should only move forward after required values, corrections, or blockers are explicit." if accepted else ""
    elif role in {"decision", "calculation"}:
        if accepted and produced and not _phrases_too_similar(accepted, produced):
            first = f"The useful state is the explanation that connects incoming {accepted} to {produced}."
        else:
            first = f"{label} must keep its input facts, calculation context, and visible result together."
        second = f"That relationship is what makes the outcome reviewable instead of a black-box claim."
    elif role == "configuration":
        first = f"The owned state is {owned}, and changes to it should read like intentional product policy."
        second = f"The runtime can consume those settings, but configuration itself should not mutate downstream results."
    elif role == "state_store":
        first = f"The owned state is {owned}, and it should stay close to the inputs and corrections that created it."
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
    material = _material_state_sentence(role=role, material_state=material_state)
    transition = f"The important lifecycle is {state_path}." if state_path else ""
    return _sentences(first, second, blocker, material, transition)


def _boundary_narrative(
    *,
    label: str,
    role: str,
    upstream: str,
    downstream: str,
    outside: Sequence[str],
) -> str:
    upstream_text = re.sub(r"^The\s+next\b", "the next", upstream).strip()
    downstream_text = re.sub(r"^The\s+next\b", "the next", downstream).strip()
    kept = [
        item
        for item in outside
        if not re.search(
            r"\b(?:runtime implementation|release approval|silent overwrite|guide path|capture allowed command)\b",
            item,
            flags=re.I,
        )
    ]
    outside_text = _human_join(kept[:4])
    if upstream_text and downstream_text:
        relation = (
            f"{label} receives its trusted context from {upstream_text} and prepares work for {downstream_text}. "
            f"That handoff is explicit so ownership does not blur between the two boundaries."
        )
    elif upstream_text:
        relation = f"{label} starts from {upstream_text} and keeps that input relationship visible."
    elif downstream_text:
        relation = f"{label} prepares state for {downstream_text} and should not hide blockers from the next step."
    else:
        relation = f"{label} must keep its state, validation result, blocker state, and evidence together."
    if not kept:
        boundary = "Unrelated input truth, release approval, and adjacent component state stay outside this component."
    elif role == "configuration":
        boundary = f"Keep {outside_text} outside this boundary so administrative policy does not become hidden runtime authority."
    elif role == "state_store":
        boundary = f"Keep {outside_text} outside this boundary so this component stores the product record without taking over adjacent decisions."
    elif role == "read_model":
        boundary = f"Keep {outside_text} outside this boundary so display logic does not rewrite original input facts."
    else:
        boundary = f"Keep {outside_text} outside this boundary unless a later release explicitly assigns it here."
    return _sentences(relation, boundary)


def _proof_narrative(*, label: str, role: str, failure: str, proofs: Sequence[str]) -> str:
    risk = (
        f"The product failure to guard against is {failure}"
        if failure
        else f"The product failure to guard against is treating {label} as ready without local behavior proof"
    )
    selected = [_clean_proof_sentence(proof, label=label, index=index) for index, proof in enumerate(proofs[:5], start=1)]
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
        parts.append(f"Use {first_workstream}{title} as the implementation anchor.")
    if first_slice:
        parts.append(first_slice)
    if wave_label:
        parts.append(f"Release wave: {wave_label}.")
    if release_selector:
        parts.append(f"Release target: {release_selector}.")
    return " ".join(_sentence(part) for part in parts if part).strip()


def _clean_proof_sentence(proof: str, *, label: str, index: int) -> str:
    text = _sentence(_clean_fragment(proof, proof=True)).rstrip(".")
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
        r"\bmissing,\s*stale,\s*unauthorized,\s*or\s*malformed\s+input\b",
        "the named bad input",
        text,
        flags=re.I,
    )
    return _sentence(text)


def _contract_items(contract: Mapping[str, Any], key: str) -> tuple[str, ...]:
    values: list[str] = []
    for raw in text_values(contract.get(key), split_scalar=True, split_commas=True, strip_bullets=True):
        cleaned = _clean_fragment(raw)
        if cleaned:
            values.append(cleaned)
    return unique_text(values)


def _proof_items(value: Any) -> tuple[str, ...]:
    values: list[str] = []
    for raw in text_values(value):
        cleaned = _clean_fragment(raw, proof=True)
        if cleaned:
            values.append(_sentence(cleaned))
    return unique_text(values)


def _clean_fragment(value: Any, *, proof: bool = False) -> str:
    text = clean_text(display_text.strip_inline_markdown_emphasis_tokens(str(value or "")))
    text = re.sub(r"^[-*]\s*", "", text).strip(" .;:")
    text = re.sub(r"\bRelated path\s*:\s*[^.;]+[.;]?", "", text, flags=re.I)
    text = re.sub(r"\b(?:Done|DoD)\s+mean(?:s)?\b", "", text, flags=re.I)
    text = re.sub(r"\bMean\s+[a-z][^.;,]*", "", text, flags=re.I)
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
    text = re.sub(r"\bkeep(?:s|ing)?\s+", "", text, flags=re.I)
    text = re.sub(r"\bexplicit(?:ly)?\b", "", text, flags=re.I)
    text = re.sub(r"^(?:them|it|their|they|this|that)\s+(?:against|with|to|from|for|into)\s+", "", text, flags=re.I)
    text = re.sub(r"^(?:against|with|to|from|for|into)\s+", "", text, flags=re.I)
    text = re.sub(r"\b(?:them|it|their|they|this|that)\b(?!\s+(?:are|is|was|were)\b)", "", text, flags=re.I)
    text = re.sub(
        r"\bbefore\s+(creates?|presents?|shows?|returns?|produces?)\b",
        r"before it \1",
        text,
        flags=re.I,
    )
    text = re.sub(r"\s+", " ", text).strip(" .;:,")
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


def _fallback_phrase(values: Sequence[str], fallback: str) -> str:
    rows = _narrative_items(values, limit=3)
    return _human_join(rows) if rows else _lower_first(fallback)


def _narrative_items(values: Sequence[str], *, limit: int, allow_status: bool = False) -> tuple[str, ...]:
    rows: list[str] = []
    filler_status_tokens = {
        "accepted",
        "confirmed",
        "needed",
        "received",
        "requested",
        "trusted",
        "visible",
    }
    material_values = [
        clean_text(value).strip(" .")
        for value in values
        if clean_text(value).strip(" .")
    ]
    has_material_alternative = any(not _generated_boundary_state_item(value) for value in material_values)
    for value in material_values:
        text = clean_text(value).strip(" .")
        if not text:
            continue
        lowered = text.casefold()
        if has_material_alternative and _generated_boundary_state_item(text):
            continue
        if not allow_status and lowered in filler_status_tokens:
            continue
        if re.search(
            r"\b(?:responsibilities not named|adjacent component|silent overwrite|release approval|mutation of original|mutation of upstream|local blockers?|recovery context owned elsewhere|guide path|capture allowed command)\b",
            lowered,
        ):
            continue
        if lowered in {
            "blocker state",
            "blocked states",
            "correction marker",
            "handoff context",
            "next-step context",
            "reviewer explanation",
            "source evidence",
            "validation context",
        }:
            continue
        if any(_phrases_too_similar(text, existing) for existing in rows):
            continue
        rows.append(text)
        if len(rows) >= limit:
            break
    return tuple(rows)


def _generated_boundary_state_item(value: str) -> bool:
    return bool(
        re.fullmatch(
            r"[a-z0-9][a-z0-9 '-]{0,80}\s+(?:adapter|client|component|engine|queue|service|store|surface|system|view)\s+state",
            clean_text(value).casefold(),
        )
    )


def _supplemental_state_items(values: Sequence[str], *, existing: Sequence[str], limit: int) -> tuple[str, ...]:
    candidates: list[tuple[int, int, str]] = []
    for index, value in enumerate(values):
        text = clean_text(value).strip(" .")
        if not text:
            continue
        if any(_phrases_too_similar(text, row) for row in existing):
            continue
        score = _state_material_score(text)
        if score <= 0:
            continue
        candidates.append((score, index, text))
    candidates.sort(key=lambda row: (-row[0], row[1]))
    selected: list[tuple[int, str]] = []
    for _score, index, text in candidates:
        if any(_phrases_too_similar(text, chosen) for _chosen_index, chosen in selected):
            continue
        selected.append((index, text))
        if len(selected) >= limit:
            break
    return tuple(text for _index, text in sorted(selected))


def _transition_items(values: Sequence[str], *, limit: int) -> tuple[str, ...]:
    rows = _narrative_items(values, limit=24, allow_status=True)
    if len(rows) <= limit:
        return rows
    selected: list[tuple[int, str]] = [(index, text) for index, text in enumerate(rows[: min(6, limit)])]
    for index, text in enumerate(rows[min(6, limit) :], start=min(6, limit)):
        if _transition_material_score(text) <= 0:
            continue
        if any(_phrases_too_similar(text, existing) for _existing_index, existing in selected):
            continue
        selected.append((index, text))
        if len(selected) >= limit:
            break
    if len(selected) < limit:
        for index, text in enumerate(rows):
            if any(index == existing_index or _phrases_too_similar(text, existing) for existing_index, existing in selected):
                continue
            selected.append((index, text))
            if len(selected) >= limit:
                break
    return tuple(text for _index, text in sorted(selected))


def _transition_material_score(value: str) -> int:
    text = clean_text(value).casefold()
    score = 0
    for pattern, weight in (
        (r"\b(?:accepted|approved|declined|denied|rejected|qualified|eligible|ineligible|decided)\b", 3),
        (r"\b(?:scheduled|completed|closed|final|published|delivered|sent|received)\b", 3),
        (r"\b(?:blocked|stale|missing|invalid|failed|error|returned|revised|corrected)\b", 3),
        (r"\b(?:draft|open|started|submitted|created|ready|reviewed)\b", 1),
    ):
        if re.search(pattern, text):
            score += weight
    return score


def _state_material_score(value: str) -> int:
    text = clean_text(value).casefold()
    score = 0
    for pattern, weight in (
        (r"\b(?:validation|validated|validates?|completeness|complete)\b", 3),
        (r"\b(?:missing|blocked|blocker|invalid|correction|recovery)\b", 3),
        (r"\b(?:provenance|source|evidence|attachment|uploaded|document)\b", 3),
        (r"\b(?:access|permission|privacy|sensitive|retention|deletion|consent)\b", 3),
        (r"\b(?:lifecycle|history|timeline|transition|status)\b", 2),
        (r"\b(?:visibility|visible|reviewable|audit|traceable|replay)\b", 2),
    ):
        if re.search(pattern, text):
            score += weight
    return score


def _material_state_sentence(*, role: str, material_state: str) -> str:
    if not material_state:
        return ""
    if role == "read_model":
        return f"It should also keep {material_state} visible enough for someone to understand the view"
    if role == "state_store":
        return f"It should also keep {material_state} attached to the record instead of leaving those facts implicit"
    if role == "evidence":
        return f"It should also keep {material_state} connected to the evidence trail"
    if role in {"entry", "recovery"}:
        return f"It should also keep {material_state} visible before the path moves on"
    return f"It should also keep {material_state} visible enough to review"


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


def _phrases_too_similar(left: str, right: str) -> bool:
    left_terms = set(re.findall(r"[a-z0-9][a-z0-9-]+", clean_text(left).casefold()))
    right_terms = set(re.findall(r"[a-z0-9][a-z0-9-]+", clean_text(right).casefold()))
    if not left_terms or not right_terms:
        return False
    return len(left_terms & right_terms) / max(1, min(len(left_terms), len(right_terms))) >= 0.72


def _calculation_focus(*, focus: str, output_focus: str, label: str) -> str:
    parts = [part.strip(" .") for part in clean_text(focus).replace(", and ", ",").split(",") if part.strip(" .")]
    noun_parts = [part for part in parts if not contains_finite_action(part)]
    if noun_parts:
        return _human_join(noun_parts[:3])
    if output_focus and not contains_finite_action(output_focus):
        return output_focus
    return re.sub(r"\b(?:adapter|component|engine|service|system|view)\b$", "", label, flags=re.I).strip(" .") or "the result"


def _string_rows(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(str(item).strip() for item in values if str(item).strip())


def _sentences(*values: str) -> str:
    return " ".join(_sentence(value) for value in values if clean_text(value)).strip()


def _sentence(value: str) -> str:
    text = clean_text(value).strip(" .")
    if not text:
        return ""
    text = re.sub(r"\s+([,.;:])", r"\1", text)
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
