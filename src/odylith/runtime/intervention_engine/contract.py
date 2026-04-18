"""Shared normalized data contracts for intervention-engine runtime surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.intervention_engine import visibility_contract


_normalize_string = visibility_contract.normalize_string
_normalize_string_list = visibility_contract.normalize_string_list
_normalize_mapping = visibility_contract.mapping_copy


def _normalize_ref_list(value: Any) -> list[dict[str, str]]:
    """Normalize reference payloads into the canonical ref-row shape."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in value:
        if isinstance(item, Mapping):
            row = {
                "kind": _normalize_string(item.get("kind")),
                "id": _normalize_string(item.get("id")),
                "path": _normalize_string(item.get("path")),
                "label": _normalize_string(item.get("label")),
            }
        else:
            row = {
                "kind": "",
                "id": _normalize_string(item),
                "path": "",
                "label": "",
            }
        key = (row["kind"], row["id"], row["path"])
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return rows


def _copy_dict_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return shallow-copied dict rows for JSON-friendly payload serialization."""
    return [dict(row) for row in rows]


@dataclass(frozen=True)
class ObservationEnvelope:
    """Normalized observation context collected around one intervention decision."""

    host_family: str = ""
    session_id: str = ""
    turn_phase: str = ""
    prompt_excerpt: str = ""
    assistant_summary: str = ""
    changed_paths: list[str] = field(default_factory=list)
    packet_summary: dict[str, Any] = field(default_factory=dict)
    context_packet_summary: dict[str, Any] = field(default_factory=dict)
    execution_engine_summary: dict[str, Any] = field(default_factory=dict)
    memory_summary: dict[str, Any] = field(default_factory=dict)
    tribunal_summary: dict[str, Any] = field(default_factory=dict)
    visibility_summary: dict[str, Any] = field(default_factory=dict)
    delivery_snapshot: dict[str, Any] = field(default_factory=dict)
    active_target_refs: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """Return the observation envelope as a JSON-friendly dict."""
        return {
            "host_family": self.host_family,
            "session_id": self.session_id,
            "turn_phase": self.turn_phase,
            "prompt_excerpt": self.prompt_excerpt,
            "assistant_summary": self.assistant_summary,
            "changed_paths": list(self.changed_paths),
            "packet_summary": dict(self.packet_summary),
            "context_packet_summary": dict(self.context_packet_summary),
            "execution_engine_summary": dict(self.execution_engine_summary),
            "memory_summary": dict(self.memory_summary),
            "tribunal_summary": dict(self.tribunal_summary),
            "visibility_summary": dict(self.visibility_summary),
            "delivery_snapshot": dict(self.delivery_snapshot),
            "active_target_refs": _copy_dict_rows(self.active_target_refs),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "ObservationEnvelope":
        """Build an observation envelope from an arbitrary mapping payload."""
        payload = dict(value) if isinstance(value, Mapping) else {}
        return cls(
            host_family=_normalize_string(payload.get("host_family")).lower(),
            session_id=_normalize_string(payload.get("session_id")),
            turn_phase=_normalize_string(payload.get("turn_phase")).lower(),
            prompt_excerpt=_normalize_string(payload.get("prompt_excerpt")),
            assistant_summary=_normalize_string(payload.get("assistant_summary")),
            changed_paths=_normalize_string_list(payload.get("changed_paths")),
            packet_summary=_normalize_mapping(payload.get("packet_summary")),
            context_packet_summary=_normalize_mapping(payload.get("context_packet_summary")),
            execution_engine_summary=_normalize_mapping(payload.get("execution_engine_summary")),
            memory_summary=_normalize_mapping(payload.get("memory_summary")),
            tribunal_summary=_normalize_mapping(payload.get("tribunal_summary")),
            visibility_summary=_normalize_mapping(payload.get("visibility_summary")),
            delivery_snapshot=_normalize_mapping(payload.get("delivery_snapshot")),
            active_target_refs=_normalize_ref_list(payload.get("active_target_refs")),
        )


@dataclass(frozen=True)
class GovernanceFact:
    """One grounded governance fact that can support intervention copy."""

    kind: str
    headline: str
    detail: str = ""
    evidence_classes: list[str] = field(default_factory=list)
    refs: list[dict[str, str]] = field(default_factory=list)
    priority: int = 0

    def as_dict(self) -> dict[str, Any]:
        """Return the governance fact as a JSON-friendly dict."""
        return {
            "kind": self.kind,
            "headline": self.headline,
            "detail": self.detail,
            "evidence_classes": list(self.evidence_classes),
            "refs": _copy_dict_rows(self.refs),
            "priority": self.priority,
        }


@dataclass(frozen=True)
class InterventionCandidate:
    """One candidate user-visible intervention produced by the engine."""

    key: str
    stage: str
    eligible: bool
    teaser_text: str = ""
    markdown_text: str = ""
    plain_text: str = ""
    evidence_classes: list[str] = field(default_factory=list)
    facts: list[dict[str, Any]] = field(default_factory=list)
    moment: dict[str, Any] = field(default_factory=dict)
    suppressed_reason: str = ""
    headline: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return the intervention candidate as a JSON-friendly dict."""
        return {
            "key": self.key,
            "stage": self.stage,
            "eligible": self.eligible,
            "teaser_text": self.teaser_text,
            "markdown_text": self.markdown_text,
            "plain_text": self.plain_text,
            "evidence_classes": list(self.evidence_classes),
            "facts": _copy_dict_rows(self.facts),
            "moment": dict(self.moment),
            "suppressed_reason": self.suppressed_reason,
            "headline": self.headline,
        }


@dataclass(frozen=True)
class CaptureAction:
    """One proposed governed action attached to an intervention proposal."""

    surface: str
    action: str
    target_kind: str = ""
    target_id: str = ""
    title: str = ""
    rationale: str = ""
    target_path: str = ""
    apply_supported: bool = False
    cli_command: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return the capture action as a JSON-friendly dict."""
        return {
            "surface": self.surface,
            "action": self.action,
            "target_kind": self.target_kind,
            "target_id": self.target_id,
            "title": self.title,
            "rationale": self.rationale,
            "target_path": self.target_path,
            "apply_supported": self.apply_supported,
            "cli_command": self.cli_command,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class CaptureBundle:
    """One capture proposal bundle ready for rendering or suppression."""

    key: str
    eligible: bool
    stale: bool = False
    markdown_text: str = ""
    plain_text: str = ""
    confirmation_text: str = ""
    actions: list[dict[str, Any]] = field(default_factory=list)
    action_surfaces: list[str] = field(default_factory=list)
    apply_supported: bool = False
    suppressed_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return the capture bundle as a JSON-friendly dict."""
        return {
            "key": self.key,
            "eligible": self.eligible,
            "stale": self.stale,
            "markdown_text": self.markdown_text,
            "plain_text": self.plain_text,
            "confirmation_text": self.confirmation_text,
            "actions": _copy_dict_rows(self.actions),
            "action_surfaces": list(self.action_surfaces),
            "apply_supported": self.apply_supported,
            "suppressed_reason": self.suppressed_reason,
        }


@dataclass(frozen=True)
class InterventionBundle:
    """Top-level intervention-engine output bundle for one user-facing moment."""

    observation: dict[str, Any]
    facts: list[dict[str, Any]]
    candidate: dict[str, Any]
    proposal: dict[str, Any]
    render_policy: dict[str, Any]
    pending_state: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        """Return the intervention bundle as a JSON-friendly dict."""
        return {
            "observation": dict(self.observation),
            "facts": _copy_dict_rows(self.facts),
            "candidate": dict(self.candidate),
            "proposal": dict(self.proposal),
            "render_policy": dict(self.render_policy),
            "pending_state": dict(self.pending_state),
        }
