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
_PLACEHOLDER_FAILURE_EVIDENCE_MARKERS: tuple[str, ...] = (
    "<paste failing command and error>",
    "<paste failing command",
    "paste failing command and error",
    "paste failing command",
)
_STRONG_INVARIANT_RE = re.compile(
    r"\b("
    r"hard rule|"
    r"non-negotiable|"
    r"must never|"
    r"must not|"
    r"never allow|"
    r"never remove|"
    r"do not remove|"
    r"don't remove|"
    r"do not ever|"
    r"always require"
    r")\b",
    re.IGNORECASE,
)
_GOVERNED_CAPTURE_VERB_RE = re.compile(
    r"\b("
    r"capture|"
    r"create|"
    r"define|"
    r"map|"
    r"open|"
    r"register|"
    r"scaffold|"
    r"track|"
    r"write"
    r")\b",
    re.IGNORECASE,
)
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
    }
)
_CAPABILITY_INVENTORY_MARKERS: tuple[str, ...] = (
    "capabilities and engines",
    "capability and engine",
    "capability map",
    "product architecture",
    "odylith show capabilities",
    "odylith capabilities",
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
    return bool(passthrough_prompt_kind(value))


def passthrough_prompt_kind(value: Any) -> str:
    """Return the first-match passthrough route kind for prompt-only CLI lanes."""
    token = normalized_passthrough_prompt(value)
    if token in _HELP_PROMPT_TOKENS:
        return "help"
    if "odylith" in token and any(marker in token for marker in _CAPABILITY_INVENTORY_MARKERS):
        return "capabilities"
    if token in _SHOW_PROMPT_TOKENS:
        return "show"
    return ""


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


def _casebook_placeholder_fact(
    *,
    prompt_surface: str,
    evidence_classes: Sequence[str],
) -> GovernanceFact | None:
    text = _normalize_string(prompt_surface).casefold()
    if not text or not any(marker in text for marker in _PLACEHOLDER_FAILURE_EVIDENCE_MARKERS):
        return None
    if not contains_any(prompt_surface, ("casebook", "bug", "failure", "regression", "incident")):
        return None
    return _fact(
        "write_blocker",
        "Casebook needs real failure evidence before it writes.",
        "The prompt still contains a placeholder; ask for the actual command output or frame the item as Radar debt.",
        evidence_classes,
        [{"kind": "component", "id": "governance-intervention-engine", "label": "governance-intervention-engine"}],
        96,
    )


def _strong_invariant_fact(
    *,
    prompt_surface: str,
    evidence_classes: Sequence[str],
) -> GovernanceFact | None:
    text = _normalize_string(prompt_surface)
    if not text or not _STRONG_INVARIANT_RE.search(text):
        return None
    lowered = text.casefold()
    if "remove" in lowered:
        headline = "The request protects an existing lane; do not delete it to quiet the noise."
        detail = "Fix the leaking decision rule while preserving the real Ambient, Observation, Proposal, and Assist lanes."
    else:
        headline = "The prompt sets a non-negotiable constraint."
        detail = "Carry the exact constraint into the change only when code or governed truth moves."
    return _fact(
        "invariant",
        headline,
        detail,
        evidence_classes,
        [],
        82,
    )


def _capture_opportunity_fact(
    *,
    observation: ObservationEnvelope,
    prompt_surface: str,
    evidence_classes: Sequence[str],
    signal_profile: Mapping[str, Any],
) -> GovernanceFact | None:
    text = _normalize_string(prompt_surface)
    if not text or not _GOVERNED_CAPTURE_VERB_RE.search(text):
        return None
    if bool(signal_profile.get("suppress_governance_capture")):
        return None
    if not bool(signal_profile.get("proposal_signal")):
        return None
    if not (
        observation.changed_paths
        or bool(signal_profile.get("has_direct_refs"))
        or bool(signal_profile.get("has_topology_hints"))
        or bool(signal_profile.get("has_bug_hints"))
        or bool(signal_profile.get("has_governance_hints"))
    ):
        return None
    title = "The request is asking for a governed capture, not just a branded aside."
    detail = "Use a proposal only if the action can be tied to the prompt, touched paths, or explicit governance references."
    return _fact(
        "capture_opportunity",
        title,
        detail,
        evidence_classes,
        [{"kind": "component", "id": "governance-intervention-engine", "label": "governance-intervention-engine"}],
        78,
    )


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
    if kind == "workstream":
        return bool(
            has_changed_paths
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
            or any(
                _normalize_string(component_id).casefold() in _normalize_string(observation.prompt_excerpt).casefold()
                for component_id in _normalize_string_list(signal_profile.get("component_ids"))
            )
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
    if not proof:
        status_surface = joined_prompt_surface(observation).casefold()
        if "chat-visible proof" in status_surface or "chat_visible_proof" in status_surface:
            if "unproven_this_session" in status_surface or "not met" in status_surface:
                proof = "unproven_this_session"
            elif "proven_this_session" in status_surface:
                proof = "proven_this_session"
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
        headline = "Odylith is active, but no Odylith note has reached this chat yet."
        detail = "The operator needs any Odylith note stated directly in normal assistant text."
        priority = 98
    elif proof in {
        "pending_confirmation",
        "ledger_visible_unconfirmed",
        "ledger_visible_with_pending_confirmation",
        "chat_confirmed_with_pending_confirmation",
    } or unconfirmed_event_count > 0:
        headline = "Odylith has appeared in this chat, but the note still needs clear follow-through."
        detail = (
            f"{visible_event_count} Odylith note(s) appeared; keep the next line simple and user-facing."
        )
        priority = 97
    elif proof == "proven_this_session" or chat_confirmed_event_count > 0:
        headline = "Odylith is already visible in this chat."
        detail = f"{chat_confirmed_event_count} Odylith note(s) already landed for the user."
        priority = 95
    elif event_count > 0:
        headline = "Odylith has activity, but the user still needs a visible line."
        detail = f"{event_count} Odylith event(s) are recorded; keep the next surfaced line direct and user-facing."
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
    casebook_placeholder_fact = _casebook_placeholder_fact(
        prompt_surface=prompt_surface,
        evidence_classes=evidence_classes,
    )
    if casebook_placeholder_fact is not None:
        facts.append(casebook_placeholder_fact)
    strong_invariant_fact = _strong_invariant_fact(
        prompt_surface=prompt_surface,
        evidence_classes=evidence_classes,
    )
    if strong_invariant_fact is not None:
        facts.append(strong_invariant_fact)
    if not any(_normalize_token(row.kind) in {"write_blocker", "invariant"} for row in facts):
        capture_opportunity_fact = _capture_opportunity_fact(
            observation=observation,
            prompt_surface=prompt_surface,
            evidence_classes=evidence_classes,
            signal_profile=signal_profile,
        )
        if capture_opportunity_fact is not None:
            facts.append(capture_opportunity_fact)
    if lookup.get("workstream_ids") and _allow_repo_fact(
        observation=observation,
        signal_profile=signal_profile,
        kind="workstream",
    ):
        ws_id = lookup["workstream_ids"][0]
        facts.append(
            _fact(
                "governance_truth",
                f"{ws_id} is the live Radar lane for this turn.",
                "Keep the next visible claim tied to that lane only when this prompt actually touches it.",
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
                f"Casebook has {bug_id} for this failure.",
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
                f"Atlas already carries the topology view for {diagram.get('id') or 'this work'}.",
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
                f"`{component_id}` is the live Registry boundary for this turn.",
                "Update that dossier only when the prompt or touched paths actually hit this component.",
                evidence_classes,
                [{"kind": "component", "id": component_id, "label": component_id}],
                84,
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
    "passthrough_prompt_kind",
]
