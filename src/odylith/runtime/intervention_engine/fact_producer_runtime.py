"""Prompt-grounded fact production for intervention-engine observations."""

from __future__ import annotations

import re
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.intervention_engine.contract import GovernanceFact
from odylith.runtime.intervention_engine.contract import ObservationEnvelope
from odylith.runtime.intervention_engine import visibility_contract


_WORKSTREAM_RE = re.compile(r"\bB-\d{3,}\b")
_BUG_RE = re.compile(r"\bCB-\d{3,}\b")
_DIAGRAM_RE = re.compile(r"\bD-\d{3,}\b")
_GOVERNANCE_HINTS: tuple[str, ...] = (
    "governance",
    "workstream",
    "radar",
    "registry",
    "atlas",
    "casebook",
    "proposal",
    "capture",
    "record",
)
_TOPOLOGY_HINTS: tuple[str, ...] = (
    "topology",
    "diagram",
    "atlas",
    "architecture",
    "ownership",
    "boundary",
    "authority",
    "relationship",
)
_INVARIANT_HINTS: tuple[str, ...] = ("invariant", "must", "never", "always", "guardrail", "non-negotiable")
_BUG_HINTS: tuple[str, ...] = ("bug", "failure", "regression", "incident", "broken", "crash")
_EXECUTION_HINTS: tuple[str, ...] = ("implement", "wire", "build", "fix", "ship", "harden", "design")
_HELP_PROMPT_TOKENS: frozenset[str] = frozenset(
    {
        "odylith help",
        "odylith please help",
        "please odylith help",
    }
)
_SHOW_PROMPT_TOKENS: frozenset[str] = frozenset(
    {
        "odylith show me what you can do",
        "odylith what can you do",
        "odylith show capabilities",
    }
)


_normalize_string = visibility_contract.normalize_string
_normalize_token = visibility_contract.normalize_token
_normalize_string_list = visibility_contract.normalize_string_list
_mapping = visibility_contract.mapping_copy


def explicit_ids(text: str, pattern: re.Pattern[str]) -> list[str]:
    """Return deduplicated explicit ids that appear in the raw prompt text."""

    seen: set[str] = set()
    rows: list[str] = []
    for token in pattern.findall(_normalize_string(text)):
        value = _normalize_string(token).upper()
        if not value or value in seen:
            continue
        seen.add(value)
        rows.append(value)
    return rows


def joined_prompt_surface(observation: ObservationEnvelope) -> str:
    """Return the prompt plus assistant carryover used for producer grounding."""

    if is_passthrough_prompt(observation.prompt_excerpt):
        return _normalize_string(observation.prompt_excerpt)
    return " ".join(
        token
        for token in (observation.prompt_excerpt, observation.assistant_summary)
        if _normalize_string(token) and not is_cli_help_output(token)
    ).strip()


def contains_any(text: str, hints: Sequence[str]) -> bool:
    """Return whether any hint token appears in the normalized text."""

    haystack = _normalize_token(text)
    return any(_normalize_token(hint) in haystack for hint in hints)


def normalized_passthrough_prompt(value: Any) -> str:
    """Return a compact prompt token for exact first-match passthrough routes."""
    text = _normalize_string(value).casefold()
    if not text:
        return ""
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def is_passthrough_prompt(value: Any) -> bool:
    """Return whether a prompt should print CLI/demo stdout without narration."""
    token = normalized_passthrough_prompt(value)
    return token in _HELP_PROMPT_TOKENS or token in _SHOW_PROMPT_TOKENS


def is_cli_help_output(value: Any) -> bool:
    """Return whether text is raw Odylith CLI help output, not conversation signal."""
    text = _normalize_string(value).casefold()
    if not text:
        return False
    return (
        "usage: odylith" in text
        and "-h, --help" in text
        and ("options:" in text or "optional arguments:" in text)
        and "show this help message" in text
    )


def _fact(kind: str, headline: str, detail: str, evidence_classes: Sequence[str], refs: Sequence[Mapping[str, str]], priority: int) -> GovernanceFact:
    return GovernanceFact(
        kind=kind,
        headline=_normalize_string(headline),
        detail=_normalize_string(detail),
        evidence_classes=_normalize_string_list(evidence_classes),
        refs=[
            {
                "kind": _normalize_token(item.get("kind")),
                "id": _normalize_string(item.get("id")),
                "path": _normalize_string(item.get("path")),
                "label": _normalize_string(item.get("label")),
            }
            for item in refs
            if isinstance(item, Mapping)
        ],
        priority=priority,
    )


def _join_labels(values: Sequence[str]) -> str:
    rows = [_normalize_string(value) for value in values if _normalize_string(value)]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def _capture_opportunity_copy(
    *,
    prompt_surface: str,
    signal_profile: Mapping[str, Any],
) -> tuple[str, str]:
    lowered = _normalize_token(prompt_surface)
    if "proposal" in lowered:
        headline = "This turn is already framing a governed proposal."
    elif contains_any(prompt_surface, ("workstream", "radar")) or _normalize_string_list(
        signal_profile.get("prompt_explicit_workstream_ids")
    ):
        headline = "This turn is already naming a governed workstream move."
    elif contains_any(prompt_surface, ("registry", "component")):
        headline = "This turn is already naming Registry-owned truth."
    elif contains_any(prompt_surface, ("atlas", "diagram", "topology", "architecture", "boundary")) or _normalize_string_list(
        signal_profile.get("prompt_explicit_diagram_ids")
    ):
        headline = "This turn is already making Atlas-owned boundary claims."
    elif contains_any(prompt_surface, ("casebook", "bug", "failure", "regression", "incident")) or _normalize_string_list(
        signal_profile.get("prompt_explicit_bug_ids")
    ):
        headline = "This turn is already describing a governed failure lane."
    else:
        headline = "This turn is already asking Odylith to record this slice."

    target_surfaces: list[str] = []
    if contains_any(prompt_surface, ("workstream", "radar")) or _normalize_string_list(
        signal_profile.get("prompt_explicit_workstream_ids")
    ):
        target_surfaces.append("Radar")
    if contains_any(prompt_surface, ("registry", "component")):
        target_surfaces.append("Registry")
    if contains_any(prompt_surface, ("atlas", "diagram", "topology", "architecture", "boundary")) or _normalize_string_list(
        signal_profile.get("prompt_explicit_diagram_ids")
    ):
        target_surfaces.append("Atlas")
    if contains_any(prompt_surface, ("casebook", "bug", "failure", "regression", "incident")) or _normalize_string_list(
        signal_profile.get("prompt_explicit_bug_ids")
    ):
        target_surfaces.append("Casebook")

    if not target_surfaces:
        detail = "Capture the exact governed change while the request is still current."
    else:
        detail = f"Capture the exact {_join_labels(target_surfaces)} move while the request is still current."
    return headline, detail


def _allow_repo_fact(
    *,
    observation: ObservationEnvelope,
    signal_profile: Mapping[str, Any],
    kind: str,
) -> bool:
    """Return whether inherited repo truth is current enough for visible narration."""

    phase = _normalize_token(observation.turn_phase)
    if phase in {"post_bash_checkpoint", "post_edit_checkpoint"}:
        return True
    has_changed_paths = bool(observation.changed_paths)
    has_execution_pressure = bool(signal_profile.get("prompt_has_execution_hints"))
    if kind == "workstream":
        return bool(
            has_changed_paths
            or has_execution_pressure
            or signal_profile.get("prompt_has_governance_hints")
            or _normalize_string_list(signal_profile.get("prompt_explicit_workstream_ids"))
        )
    if kind == "bug":
        return bool(
            has_changed_paths
            or signal_profile.get("prompt_has_bug_hints")
            or _normalize_string_list(signal_profile.get("prompt_explicit_bug_ids"))
        )
    if kind == "diagram":
        return bool(
            has_changed_paths
            or signal_profile.get("prompt_has_topology_hints")
            or _normalize_string_list(signal_profile.get("prompt_explicit_diagram_ids"))
        )
    if kind == "component":
        return bool(
            has_changed_paths
            or has_execution_pressure
            or signal_profile.get("prompt_has_governance_hints")
            or signal_profile.get("prompt_has_topology_hints")
        )
    return has_changed_paths


def _current_visibility_status_fact(
    *,
    observation: ObservationEnvelope,
    evidence_classes: Sequence[str],
    signal_profile: Mapping[str, Any],
) -> GovernanceFact | None:
    if not (
        bool(signal_profile.get("status_readout_review"))
        or bool(signal_profile.get("relevance_review"))
    ):
        return None
    visibility = _mapping(observation.visibility_summary)
    delivery = _mapping(observation.delivery_snapshot)
    proof = _normalize_token(visibility.get("chat_visible_proof"))
    event_count = int(visibility.get("event_count") or delivery.get("event_count") or 0)
    visible_event_count = int(visibility.get("visible_event_count") or delivery.get("visible_event_count") or 0)
    chat_confirmed_event_count = int(
        visibility.get("chat_confirmed_event_count") or delivery.get("chat_confirmed_event_count") or 0
    )
    unconfirmed_event_count = int(
        visibility.get("unconfirmed_event_count") or delivery.get("unconfirmed_event_count") or 0
    )
    if (
        proof == "unproven_this_session"
        and visible_event_count <= 0
        and chat_confirmed_event_count <= 0
    ):
        headline = "This session is armed, but chat visibility is still unproven."
        detail = (
            "Activation alone does not count: this session still has zero visible Odylith beats "
            "confirmed in chat."
        )
        priority = 98
    elif proof in {
        "pending_confirmation",
        "ledger_visible_unconfirmed",
        "ledger_visible_with_pending_confirmation",
        "chat_confirmed_with_pending_confirmation",
    } or unconfirmed_event_count > 0:
        headline = "This session has visible Odylith beats waiting for transcript confirmation."
        detail = (
            f"{visible_event_count} visible event(s), {chat_confirmed_event_count} chat-confirmed, "
            f"{unconfirmed_event_count} still pending exact confirmation."
        )
        priority = 97
    elif proof == "proven_this_session" or chat_confirmed_event_count > 0:
        headline = "This session already has current chat-visible Odylith proof."
        detail = f"{chat_confirmed_event_count} chat-confirmed visible beat(s) already landed in this session."
        priority = 95
    elif event_count > 0:
        headline = "This session has delivery activity, but not current chat-visible proof yet."
        detail = f"{event_count} delivery event(s) are recorded, but chat visibility is not yet proven."
        priority = 94
    else:
        return None
    return _fact(
        "governance_truth",
        headline,
        detail,
        evidence_classes,
        [{"kind": "component", "id": "governance-intervention-engine", "label": "governance-intervention-engine"}],
        priority,
    )


def collect_facts(
    *,
    observation: ObservationEnvelope,
    lookup: Mapping[str, Any],
    evidence_classes: Sequence[str],
    signal_profile: Mapping[str, Any],
) -> list[GovernanceFact]:
    """Return visible producer facts grounded in the current turn and repo truth."""

    facts: list[GovernanceFact] = []
    prompt_surface = joined_prompt_surface(observation)
    if is_passthrough_prompt(observation.prompt_excerpt) or (
        is_cli_help_output(observation.assistant_summary) and not _normalize_string(observation.prompt_excerpt)
    ):
        return facts
    visibility_status_fact = _current_visibility_status_fact(
        observation=observation,
        evidence_classes=evidence_classes,
        signal_profile=signal_profile,
    )
    if visibility_status_fact is not None:
        facts.append(visibility_status_fact)
    if bool(signal_profile.get("suppress_governance_capture")):
        return facts
    if lookup.get("workstream_ids") and _allow_repo_fact(
        observation=observation,
        signal_profile=signal_profile,
        kind="workstream",
    ):
        ws_id = lookup["workstream_ids"][0]
        facts.append(
            _fact(
                "governance_truth",
                f"Radar already has {ws_id} for this slice.",
                "Extend that workstream instead of creating a duplicate backlog record.",
                evidence_classes,
                [{"kind": "workstream", "id": ws_id, "label": ws_id}],
                95,
            )
        )
    if lookup.get("bug_ids") and _allow_repo_fact(
        observation=observation,
        signal_profile=signal_profile,
        kind="bug",
    ):
        bug_id = lookup["bug_ids"][0]
        bug_title = _normalize_string(lookup["bug_rows"].get(bug_id, {}).get("title"))
        facts.append(
            _fact(
                "history",
                f"Casebook already remembers {bug_id}.",
                bug_title or "This conversation is touching a previously captured failure lane.",
                evidence_classes,
                [{"kind": "bug", "id": bug_id, "label": bug_id}],
                90,
            )
        )
    if lookup.get("diagram_refs") and _allow_repo_fact(
        observation=observation,
        signal_profile=signal_profile,
        kind="diagram",
    ):
        diagram = lookup["diagram_refs"][0]
        facts.append(
            _fact(
                "topology",
                f"Atlas already carries topology proof for {diagram.get('id') or 'this slice'}.",
                _normalize_string(diagram.get("label")) or "The conversation is making architecture claims against an existing diagrammed boundary.",
                evidence_classes,
                [diagram],
                88,
            )
        )
    if lookup.get("component_ids") and _allow_repo_fact(
        observation=observation,
        signal_profile=signal_profile,
        kind="component",
    ):
        component_id = lookup["component_ids"][0]
        facts.append(
            _fact(
                "governance_truth",
                f"Registry already maps this work onto `{component_id}`.",
                "Update the existing component dossier instead of creating a duplicate component boundary.",
                evidence_classes,
                [{"kind": "component", "id": component_id, "label": component_id}],
                84,
            )
        )
    if contains_any(prompt_surface, _INVARIANT_HINTS):
        facts.append(
            _fact(
                "invariant",
                "The conversation is setting a hard rule, not just a preference.",
                "Capture it now or the runtime and the governed record will drift apart.",
                evidence_classes,
                [],
                82,
            )
        )
    if contains_any(prompt_surface, _TOPOLOGY_HINTS):
        facts.append(
            _fact(
                "topology",
                "This request is making architecture, ownership, or boundary claims.",
                "If the claim changes product behavior or governed docs, attach it to the existing Atlas or Registry record instead of leaving it only in chat.",
                evidence_classes,
                [],
                80,
            )
        )
    if contains_any(prompt_surface, _GOVERNANCE_HINTS):
        headline, detail = _capture_opportunity_copy(
            prompt_surface=prompt_surface,
            signal_profile=signal_profile,
        )
        facts.append(
            _fact(
                "capture_opportunity",
                headline,
                detail,
                evidence_classes,
                [],
                78,
            )
        )
    return facts


def evidence_classes(*, observation: ObservationEnvelope, lookup: Mapping[str, Any]) -> list[str]:
    """Return the evidence classes that make the current beat current and grounded."""

    classes: list[str] = []
    prompt_surface = joined_prompt_surface(observation)
    if is_passthrough_prompt(observation.prompt_excerpt) or (
        is_cli_help_output(observation.assistant_summary) and not _normalize_string(observation.prompt_excerpt)
    ):
        return []
    if _normalize_string(observation.prompt_excerpt) and (
        contains_any(prompt_surface, _GOVERNANCE_HINTS + _TOPOLOGY_HINTS + _BUG_HINTS + _INVARIANT_HINTS + _EXECUTION_HINTS)
        or explicit_ids(prompt_surface, _WORKSTREAM_RE)
        or explicit_ids(prompt_surface, _BUG_RE)
        or explicit_ids(prompt_surface, _DIAGRAM_RE)
    ):
        classes.append("prompt")
    if _normalize_string(observation.assistant_summary):
        classes.append("assistant")
    if observation.changed_paths:
        classes.append("changed_paths")
    if lookup.get("target_refs"):
        classes.append("packet")
    if lookup.get("bug_ids") or lookup.get("workstream_ids") or lookup.get("diagram_refs"):
        classes.append("history")
    rows: list[str] = []
    seen: set[str] = set()
    for item in classes:
        token = _normalize_token(item)
        if token and token not in seen:
            seen.add(token)
            rows.append(token)
    return rows


__all__ = [
    "collect_facts",
    "contains_any",
    "evidence_classes",
    "explicit_ids",
    "is_cli_help_output",
    "is_passthrough_prompt",
    "joined_prompt_surface",
    "normalized_passthrough_prompt",
]
