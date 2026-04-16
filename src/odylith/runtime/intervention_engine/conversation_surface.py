from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import engine
from odylith.runtime.intervention_engine import surface_runtime
from odylith.runtime.intervention_engine import voice
from odylith.runtime.intervention_engine.contract import ObservationEnvelope


_AMBIENT_SIGNAL_SCORE_FLOOR = 74


def _normalize_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_block_string(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    rows: list[str] = []
    blank_run = 0
    for raw_line in text.split("\n"):
        line = str(raw_line).rstrip()
        if not line.strip():
            blank_run += 1
            if blank_run > 1:
                continue
            rows.append("")
            continue
        blank_run = 0
        rows.append(line)
    return "\n".join(rows).strip()


def _normalize_token(value: Any) -> str:
    return _normalize_string(value).lower().replace("-", "_").replace(" ", "_")


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sentence(value: Any) -> str:
    token = _normalize_string(value)
    if not token:
        return ""
    return token if token.endswith((".", "!", "?")) else f"{token}."


def _strip_terminal_punctuation(value: Any) -> str:
    return _normalize_string(value).rstrip(".!? ")


def _label(name: str, *, markdown: bool) -> str:
    token = _normalize_token(name)
    labels = {
        "insight": "Odylith Insight:",
        "history": "Odylith History:",
        "risks": "Odylith Risks:",
    }
    plain = labels.get(token, "Odylith Insight:")
    return f"**{plain}**" if markdown else plain


def _empty_signal(name: str) -> dict[str, Any]:
    return {
        "eligible": False,
        "label": _label(name, markdown=False),
        "preferred_markdown_label": _label(name, markdown=True),
        "plain_text": "",
        "markdown_text": "",
        "render_hint": "silent",
        "signal_score": 0,
        "suppressed_reason": "not_selected",
    }


def _intervention_payload(bundle: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(bundle.get("candidate"), Mapping) and isinstance(bundle.get("proposal"), Mapping):
        return dict(bundle)
    return _mapping(bundle.get("intervention_bundle"))


def _primary_fact(intervention: Mapping[str, Any]) -> dict[str, Any]:
    facts = intervention.get("facts")
    if not isinstance(facts, list):
        return {}
    for row in facts:
        if isinstance(row, Mapping):
            return dict(row)
    return {}


def _signal_name_for_fact(fact: Mapping[str, Any]) -> str:
    kind = _normalize_token(fact.get("kind"))
    if kind == "history":
        return "history"
    if kind == "invariant":
        return "risks"
    return "insight"

def _signal_score(
    *,
    intervention: Mapping[str, Any],
) -> int:
    candidate = _mapping(intervention.get("candidate"))
    moment = _mapping(candidate.get("moment"))
    return max(0, min(100, int(moment.get("score") or 0)))


def _ambient_payload(
    *,
    observation: ObservationEnvelope,
    intervention: Mapping[str, Any],
) -> dict[str, Any]:
    candidate = _mapping(intervention.get("candidate"))
    stage = _normalize_token(candidate.get("stage"))
    if _normalize_token(observation.turn_phase) in {"prompt_submit", "userpromptsubmit"}:
        return {}
    if stage == "card":
        return {}
    if _normalize_string(candidate.get("suppressed_reason")):
        return {}
    moment = _mapping(candidate.get("moment"))
    fact = _primary_fact(intervention)
    if not fact:
        return {}
    score = _signal_score(intervention=intervention)
    if score < _AMBIENT_SIGNAL_SCORE_FLOOR:
        return {}
    signal_name, plain_text = voice.render_ambient_signal(
        moment=moment,
        facts=[fact],
        markdown=False,
        seed=_normalize_string(candidate.get("key")),
    )
    _markdown_signal_name, markdown_text = voice.render_ambient_signal(
        moment=moment,
        facts=[fact],
        markdown=True,
        seed=_normalize_string(candidate.get("key")),
    )
    if not plain_text:
        return {}
    return {
        "eligible": True,
        "label": _label(signal_name, markdown=False),
        "preferred_markdown_label": _label(signal_name, markdown=True),
        "plain_text": plain_text,
        "markdown_text": markdown_text,
        "render_hint": "explicit_label",
        "signal_score": score,
        "suppressed_reason": "",
        "source_kind": _normalize_string(moment.get("kind")) or _normalize_string(fact.get("kind")),
    }


def build_conversation_bundle(
    *,
    repo_root: Path,
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_observation = ObservationEnvelope.from_mapping(observation)
    normalized_payload = normalized_observation.as_dict()
    intervention_bundle = engine.build_intervention_bundle(
        repo_root=repo_root,
        observation=normalized_payload,
    )
    ambient = {
        "insight": _empty_signal("insight"),
        "history": _empty_signal("history"),
        "risks": _empty_signal("risks"),
        "selected_signal": "",
        "render_policy": {
            "owner": "governance_intervention_engine",
            "live_mid_turn_only": True,
            "prompt_submit_teaser_only": True,
            "explicit_labels_rare": True,
        },
    }
    selected_payload = _ambient_payload(
        observation=normalized_observation,
        intervention=intervention_bundle,
    )
    if selected_payload:
        signal_name = _signal_name_for_fact(_primary_fact(intervention_bundle))
        ambient[signal_name] = selected_payload
        ambient["selected_signal"] = signal_name
    return {
        "observation": normalized_payload,
        "ambient_signals": ambient,
        "intervention_bundle": intervention_bundle,
        "pending_state": _mapping(intervention_bundle.get("pending_state")),
        "render_policy": {
            "owner": "governance_intervention_engine",
            "mid_turn_surface": True,
            "closeout_owned_by_chatter": True,
            "cross_host_shared": True,
        },
    }


def _selected_ambient_payload(bundle: Mapping[str, Any]) -> dict[str, Any]:
    ambient = _mapping(bundle.get("ambient_signals"))
    selected = _normalize_token(ambient.get("selected_signal"))
    payload = _mapping(ambient.get(selected))
    if not payload.get("eligible"):
        return {}
    if _normalize_token(payload.get("render_hint")) != "explicit_label":
        return {}
    return payload


def render_live_text(
    bundle: Mapping[str, Any],
    *,
    markdown: bool,
    include_proposal: bool,
    prefer_ambient_over_teaser: bool = True,
) -> str:
    intervention = _intervention_payload(bundle)
    rendered = surface_runtime.render_blocks(
        intervention,
        markdown=markdown,
        include_proposal=include_proposal,
    )
    if rendered:
        return rendered
    ambient_payload = _selected_ambient_payload(bundle)
    ambient_text = _normalize_string(ambient_payload.get("markdown_text" if markdown else "plain_text"))
    teaser_text = surface_runtime.teaser_text(intervention)
    if prefer_ambient_over_teaser and ambient_text:
        return ambient_text
    if teaser_text:
        return teaser_text
    return ambient_text


def render_closeout_text(
    bundle: Mapping[str, Any],
    *,
    markdown: bool,
) -> str:
    closeout = _mapping(bundle.get("closeout_bundle"))
    return _normalize_block_string(closeout.get("markdown_text" if markdown else "plain_text"))


def append_intervention_events(
    *,
    repo_root: Path,
    bundle: Mapping[str, Any],
    include_proposal: bool,
    include_closeout: bool = False,
    delivery_channel: str = "",
    delivery_status: str = "",
    render_surface: str = "",
    delivery_latency_ms: float | None = None,
) -> list[str]:
    events: list[str] = []
    intervention = _intervention_payload(bundle)
    if intervention:
        events.extend(
            surface_runtime.append_bundle_events(
                repo_root=repo_root,
                bundle=intervention,
                include_proposal=include_proposal,
                delivery_channel=delivery_channel,
                delivery_status=delivery_status,
                render_surface=render_surface,
                delivery_latency_ms=delivery_latency_ms,
            )
        )
    observation = _mapping(bundle.get("observation"))
    ambient = _selected_ambient_payload(bundle)
    if ambient and _normalize_string(ambient.get("markdown_text")):
        surface_runtime.stream_state.append_intervention_event(
            repo_root=repo_root,
            kind="ambient_signal",
            summary=_normalize_string(ambient.get("plain_text")) or "Odylith ambient signal.",
            session_id=_normalize_string(observation.get("session_id")),
            host_family=_normalize_string(observation.get("host_family")),
            intervention_key=_normalize_string(ambient.get("source_kind")) or "ambient",
            turn_phase=_normalize_string(observation.get("turn_phase")),
            artifacts=observation.get("changed_paths") if isinstance(observation.get("changed_paths"), list) else (),
            display_markdown=_normalize_block_string(ambient.get("markdown_text")),
            display_plain=_normalize_block_string(ambient.get("plain_text")),
            prompt_excerpt=_normalize_string(observation.get("prompt_excerpt")),
            assistant_summary=_normalize_string(observation.get("assistant_summary")),
            moment_kind=_normalize_string(ambient.get("source_kind")),
            semantic_signature=("ambient", _normalize_string(ambient.get("source_kind"))),
            delivery_channel=delivery_channel,
            delivery_status=delivery_status,
            render_surface=render_surface,
            delivery_latency_ms=delivery_latency_ms,
        )
        events.append("ambient_signal")
    closeout_text = render_closeout_text(bundle, markdown=True) if include_closeout else ""
    if closeout_text:
        surface_runtime.stream_state.append_intervention_event(
            repo_root=repo_root,
            kind="assist_closeout",
            summary=_normalize_string(closeout_text),
            session_id=_normalize_string(observation.get("session_id")),
            host_family=_normalize_string(observation.get("host_family")),
            intervention_key="assist",
            turn_phase=_normalize_string(observation.get("turn_phase")),
            artifacts=observation.get("changed_paths") if isinstance(observation.get("changed_paths"), list) else (),
            display_markdown=closeout_text,
            display_plain=render_closeout_text(bundle, markdown=False),
            prompt_excerpt=_normalize_string(observation.get("prompt_excerpt")),
            assistant_summary=_normalize_string(observation.get("assistant_summary")),
            moment_kind="assist",
            semantic_signature=("assist",),
            delivery_channel=delivery_channel,
            delivery_status=delivery_status,
            render_surface=render_surface,
            delivery_latency_ms=delivery_latency_ms,
        )
        events.append("assist_closeout")
    return events
