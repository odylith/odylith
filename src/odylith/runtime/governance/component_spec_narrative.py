"""Narrative Registry spec renderer for greenfield component contracts."""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.common import display_text
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
    if re.search(r"\b(audit|evidence|file|ledger|provenance|registry|trail)\b", label_text):
        return "evidence"
    if re.search(r"\b(config|configuration|admin|administrator|policy|setting)\b", label_text):
        return "configuration"
    if re.search(r"\b(store|repository|record|records|profile|history|log)\b", label_text):
        return "state_store"
    if re.search(r"\b(decision|outcome|reason|approve|approval|decline|explain|rationale|recommendation)\b", label_text):
        return "decision"
    if re.search(r"\b(compute|calculation|calculator|engine|score|rank|compare|threshold|ratio|rule|eligibility|pricing)\b", label_text):
        return "calculation"
    if re.search(r"\b(queue|route|routing|handoff|follow-up|notification|assignment|case)\b", label_text):
        return "handoff"
    if re.search(r"\b(view|timeline|dashboard|summary|report|export|surface|display|history|trend)\b", label_text):
        return "read_model"
    if re.search(r"\b(intake|capture|entry|submit|upload|log|record|draft)\b", label_text):
        return "entry"
    role_patterns = (
        ("decision", r"\b(decision|outcome|reason|approve|approval|decline|qualified|eligible|explain|rationale|recommendation)\b"),
        ("calculation", r"\b(compute|calculate|evaluate|score|rank|compare|threshold|ratio|rule|eligibility|pricing)\b"),
        ("configuration", r"\b(config|configuration|admin|administrator|policy|rule|threshold|template|setting)\b"),
        ("state_store", r"\b(store|repository|record|records|profile|history|log|persist|saved|stored)\b"),
        ("handoff", r"\b(queue|route|routing|handoff|follow-up|notification|assignment|case)\b"),
        ("read_model", r"\b(view|timeline|dashboard|summary|report|export|surface|display|history|trend)\b"),
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
        lead = f"{label} is where the first release turns user-provided information into product state."
        body = f"Its center of gravity is {focus}; the important part is not the screen or adapter, but the moment {input_focus} becomes trustworthy enough to continue."
    elif role == "decision":
        lead = f"{label} is the place where the product turns prepared evidence into an explained outcome."
        body = f"The spec should stay focused on {output_focus}, because downstream work needs to know not only what happened but why it happened."
    elif role == "calculation":
        lead = f"{label} carries the product logic that interprets accepted inputs before anyone treats the result as true."
        if _phrases_too_similar(input_focus, output_focus):
            body = f"It should explain how {focus} is calculated, which facts were used, and why the result is safe to show."
        else:
            body = f"It should make {input_focus} traceable to {output_focus}, with the rule or calculation context visible enough to review."
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
        lead = f"{label} keeps the project honest after the first path runs."
        body = f"Its job is to preserve {focus} so release review can replay what changed, which source was used, and which blockers remained visible."
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
    text = re.sub(r"\s+[—-]\s+", ": ", text, count=1)
    text = re.sub(r"\s+", " ", text).strip(" .")
    if looks_like_finite_action(text):
        return _sentence(f"Accepted intent says this component {_lower_first(text)}")
    return _sentence(f"Accepted intent centers this component on {_lower_first(text)}")


def _state_narrative(
    *,
    label: str,
    role: str,
    owns: Sequence[str],
    accepts: Sequence[str],
    produces: Sequence[str],
    transitions: Sequence[str],
) -> str:
    owned = _human_join(owns[:8])
    accepted = _human_join(accepts[:5])
    produced = _human_join(produces[:5])
    state_path = _human_join(transitions[:16])
    if role in {"entry", "recovery"}:
        first = f"The local state starts with {owned}." if owned else f"{label} needs the first implementation plan to name its local state."
        second = f"The component can take in {accepted}, but it should only move forward after required values, corrections, or blockers are explicit." if accepted else ""
    elif role in {"decision", "calculation"}:
        if accepted and produced and not _phrases_too_similar(accepted, produced):
            first = f"The useful state is the relationship between {accepted} and {produced}."
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
        first = f"The next-step state is useful only if {produced} travels with enough context from {accepted}."
        second = "Raw input fields should remain with their owner; this component should carry the context another participant needs."
    elif role == "read_model":
        first = f"The visible state should explain {owned} without pretending to own every source record."
        second = f"It can render {produced}, while stale, empty, or blocked states remain visible."
    else:
        first = f"The local contract centers on {owned}."
        second = f"It accepts {accepted} and returns {produced}."
    transition = f"The important lifecycle is {state_path}." if state_path else ""
    return _sentences(first, second, transition)


def _boundary_narrative(
    *,
    label: str,
    role: str,
    upstream: str,
    downstream: str,
    outside: Sequence[str],
) -> str:
    kept = [
        item
        for item in outside
        if not re.search(r"\b(?:runtime implementation|release approval|silent overwrite)\b", item, flags=re.I)
    ]
    outside_text = _human_join(kept[:4])
    if upstream and downstream:
        relation = (
            f"{label} receives its trusted context from {upstream} and prepares work for {downstream}. "
            f"That handoff is explicit so ownership does not blur between the two boundaries."
        )
    elif upstream:
        relation = f"{label} starts from {upstream} and keeps that input relationship visible."
    elif downstream:
        relation = f"{label} prepares state for {downstream} and should not hide blockers from the next step."
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
        f"The failure to guard against is {failure}"
        if failure
        else f"The failure to guard against is treating {label} as ready without local behavior proof"
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
    text = re.sub(
        r"^(?:owns?|accepts?|produces?|returns?|return|depends\s+on|coordinates\s+with|computes?|evaluates?|validates?|captures?)\s+",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(r"\b(?:producing|recording|capturing|tracking|reviewing|showing|returning)\s+the\s+", "", text, flags=re.I)
    text = re.sub(r"\b(?:producing|recording|capturing|tracking|reviewing|showing|returning)\s+", "", text, flags=re.I)
    text = re.sub(r"\busing\s+(?:mocked|stubbed|simulated)\b.*$", "", text, flags=re.I)
    text = re.sub(r"^(?:them|it|their|they|this|that)\s+(?:against|with|to|from|for|into)\s+", "", text, flags=re.I)
    text = re.sub(r"^(?:against|with|to|from|for|into)\s+", "", text, flags=re.I)
    text = re.sub(r"\b(?:them|it|their|they|this|that)\b", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" .;:,")
    if not text:
        return ""
    lowered = text.casefold()
    if re.search(r"\b(?:runs?|evaluates?|checks?|computes?)\s+(?:it|them|their|they)\b", lowered):
        return ""
    if re.match(r"^(?:and|or|their|they|them|it|this|that|who|which|where)\b", lowered):
        return ""
    if not proof and re.fullmatch(r"(?:local blockers?|handoff evidence|source evidence|prior state|prior result|authorized actor|validation command|validation context|validation notes?)", lowered):
        return ""
    if "responsibilities not named by this component boundary" in lowered:
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
    return text[:1].upper() + text[1:] if re.match(r"^[a-z]", text) and re.search(r"\b[A-Z][a-z]", value) else text


def _fallback_phrase(values: Sequence[str], fallback: str) -> str:
    return _human_join(values[:5]) if values else _lower_first(fallback)


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


def _proof_handle(label: str, proof: str, *, index: int) -> str:
    seed = f"{label} {proof}"
    words = [word for word in slugify(seed).split("-") if word][:7]
    base = "_".join(words) or "component"
    return f"{base}_{index}_proof"


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
