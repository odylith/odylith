"""Bounded narrator helpers for Compass standup briefs and packet bundles."""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any, Mapping, Sequence

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.surfaces import compass_standup_brief_narrator as narrator
from odylith.runtime.surfaces import compass_standup_brief_substrate
from odylith.runtime.surfaces import compass_standup_brief_telemetry


DEFAULT_SCOPED_PROVIDER_PACK_SIZE = 12
DEFAULT_SCOPED_PROVIDER_PACK_MAX_CHARS = 18000
DEFAULT_BUNDLE_PROVIDER_MAX_CHARS = 18000
DEFAULT_BUNDLE_PROVIDER_MAX_ENTRIES = 4
_PARALLEL_PACK_TARGET_ENTRIES = 12

# Context window budgets per host family. Use ~40% of the model's context window
# for the prompt payload to leave room for system prompt, schema, and output.
_HOST_CONTEXT_BUDGET: dict[str, tuple[int, int]] = {
    # (max_chars, max_entries) — chars is a rough proxy for tokens at ~4 chars/token
    "claude": (160000, 24),    # Haiku/Sonnet/Opus: 200K context → 160K budget
    "codex": (160000, 24),     # Codex Spark/Codex: 200K context → 160K budget
    "unknown": (18000, 4),     # Conservative fallback for unknown hosts
}


def _host_aware_bundle_budget(
    config: odylith_reasoning.ReasoningConfig | None = None,
) -> tuple[int, int]:
    """Return (max_chars, max_entries) based on the resolved provider's host family."""
    if config is None:
        return DEFAULT_BUNDLE_PROVIDER_MAX_CHARS, DEFAULT_BUNDLE_PROVIDER_MAX_ENTRIES
    provider_token = str(config.provider or "").strip().lower()
    if "claude" in provider_token:
        return _HOST_CONTEXT_BUDGET["claude"]
    if "codex" in provider_token:
        return _HOST_CONTEXT_BUDGET["codex"]
    import os
    from odylith.runtime.common import host_runtime as host_runtime_contract
    detected = host_runtime_contract.detect_host_runtime(environ=os.environ)
    if detected == "claude_cli":
        return _HOST_CONTEXT_BUDGET["claude"]
    if detected == "codex_cli":
        return _HOST_CONTEXT_BUDGET["codex"]
    return _HOST_CONTEXT_BUDGET["unknown"]
_ABORT_FANOUT_FAILURE_CODES = frozenset(
    {
        "rate_limited",
        "credits_exhausted",
        "timeout",
        "provider_unavailable",
        "transport_error",
        "auth_error",
        "provider_error",
        "unavailable",
    }
)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _scope_packet_payload_chars(*, fact_packet: Mapping[str, Any]) -> int:
    payload = narrator._provider_fact_packet_view(fact_packet=fact_packet)  # noqa: SLF001
    return len(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def _adaptive_chunked_scope_packets(
    scope_packets: Mapping[str, Mapping[str, Any]],
    *,
    pack_size: int,
    max_payload_chars: int,
) -> list[list[tuple[str, Mapping[str, Any]]]]:
    size_limit = max(1, int(pack_size))
    char_limit = max(1, int(max_payload_chars))
    chunks: list[list[tuple[str, Mapping[str, Any]]]] = []
    current_chunk: list[tuple[str, Mapping[str, Any]]] = []
    current_chars = 0
    for scope_id, fact_packet in scope_packets.items():
        packet_chars = _scope_packet_payload_chars(fact_packet=fact_packet)
        should_flush = bool(current_chunk) and (
            len(current_chunk) >= size_limit or current_chars + packet_chars > char_limit
        )
        if should_flush:
            chunks.append(current_chunk)
            current_chunk = []
            current_chars = 0
        current_chunk.append((scope_id, fact_packet))
        current_chars += packet_chars
    if current_chunk:
        chunks.append(current_chunk)
    return chunks


def _split_scope_packets(
    scope_packets: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Mapping[str, Any]]]:
    items = list(scope_packets.items())
    if len(items) <= 1:
        return [{scope_id: fact_packet for scope_id, fact_packet in items}] if items else []
    weighted_items = [
        (scope_id, fact_packet, _scope_packet_payload_chars(fact_packet=fact_packet))
        for scope_id, fact_packet in items
    ]
    weighted_items.sort(key=lambda item: (-item[2], item[0]))
    left: list[tuple[str, Mapping[str, Any], int]] = []
    right: list[tuple[str, Mapping[str, Any], int]] = []
    left_weight = 0
    right_weight = 0
    for entry in weighted_items:
        if left_weight <= right_weight:
            left.append(entry)
            left_weight += entry[2]
        else:
            right.append(entry)
            right_weight += entry[2]
    if not left or not right:
        midpoint = max(1, len(weighted_items) // 2)
        left = weighted_items[:midpoint]
        right = weighted_items[midpoint:]
    return [
        {scope_id: fact_packet for scope_id, fact_packet, _weight in chunk}
        for chunk in (left, right)
        if chunk
    ]


def _sections_schema() -> dict[str, Any]:
    section_schema = narrator._provider_output_schema()["properties"]["sections"]  # noqa: SLF001
    return json.loads(json.dumps(section_schema))


def _provider_failure_should_abort_fanout(provider: odylith_reasoning.ReasoningProvider) -> bool:
    metadata = odylith_reasoning.provider_failure_metadata(provider)
    return str(metadata.get("code", "")).strip().lower() in _ABORT_FANOUT_FAILURE_CODES


def _request_profile_metadata(
    request: odylith_reasoning.StructuredReasoningRequest,
) -> tuple[str, str]:
    return (
        str(getattr(request, "model", "")).strip(),
        str(getattr(request, "reasoning_effort", "")).strip(),
    )


def _batch_provider_system_prompt() -> str:
    return (
        narrator._provider_system_prompt()  # noqa: SLF001
        + " You are writing multiple scoped briefs in one batch. "
        "Return one independent four-section brief per scope_id. "
        "Never mix facts, fact ids, or workstream meaning across scopes. "
        "If one scope has thin evidence, keep that scope plainer rather than borrowing tone or detail from another scope."
    )


def _window_batch_provider_system_prompt() -> str:
    return (
        narrator._provider_system_prompt()  # noqa: SLF001
        + " You are writing multiple global Compass briefs in one batch. "
        "Return one independent four-section brief per window_key. "
        "Keep the 24h and 48h briefs isolated to their own fact packets. "
        "Do not flatten the two windows into one shared answer."
    )


def _batch_provider_output_schema(*, scope_ids: Sequence[str]) -> dict[str, Any]:
    scope_tokens = [str(scope_id).strip() for scope_id in scope_ids if str(scope_id).strip()]
    return {
        "type": "object",
        "required": ["briefs"],
        "additionalProperties": False,
        "properties": {
            "briefs": {
                "type": "array",
                "minItems": 1,
                "maxItems": len(scope_tokens),
                "items": {
                    "type": "object",
                    "required": ["scope_id", "sections"],
                    "additionalProperties": False,
                    "properties": {
                        "scope_id": {
                            "type": "string",
                            "enum": scope_tokens,
                        },
                        "sections": _sections_schema(),
                    },
                },
            }
        },
    }


def _window_batch_provider_output_schema(*, window_keys: Sequence[str]) -> dict[str, Any]:
    window_tokens = [str(window_key).strip() for window_key in window_keys if str(window_key).strip()]
    return {
        "type": "object",
        "required": ["briefs"],
        "additionalProperties": False,
        "properties": {
            "briefs": {
                "type": "array",
                "minItems": 1,
                "maxItems": len(window_tokens),
                "items": {
                    "type": "object",
                    "required": ["window_key", "sections"],
                    "additionalProperties": False,
                    "properties": {
                        "window_key": {
                            "type": "string",
                            "enum": window_tokens,
                        },
                        "sections": _sections_schema(),
                    },
                },
            }
        },
    }


def _batch_provider_request_payload(
    *,
    scope_packets: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    first_packet = next(iter(scope_packets.values()))
    base_payload = narrator._provider_request_payload(fact_packet=first_packet)  # noqa: SLF001
    return {
        "schema_version": narrator.STANDUP_BRIEF_SCHEMA_VERSION,
        "brief_contract": dict(base_payload.get("brief_contract", {})),
        "batch_contract": {
            "scope_count": len(scope_packets),
            "rules": [
                "return one brief per scope_id",
                "keep each scope isolated to its own fact packet",
                "do not drop a scope just because another scope has stronger evidence",
            ],
        },
        "scoped_fact_packets": [
            {
                "scope_id": scope_id,
                "fact_packet": narrator._provider_fact_packet_view(fact_packet=fact_packet),  # noqa: SLF001
            }
            for scope_id, fact_packet in scope_packets.items()
        ],
    }


def _window_batch_provider_request_payload(
    *,
    window_packets: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    first_packet = next(iter(window_packets.values()))
    base_payload = narrator._provider_request_payload(fact_packet=first_packet)  # noqa: SLF001
    return {
        "schema_version": narrator.STANDUP_BRIEF_SCHEMA_VERSION,
        "brief_contract": dict(base_payload.get("brief_contract", {})),
        "batch_contract": {
            "window_count": len(window_packets),
            "rules": [
                "return one brief per window_key",
                "keep each window isolated to its own fact packet",
                "do not collapse 24h and 48h into one summary",
            ],
        },
        "window_fact_packets": [
            {
                "window_key": window_key,
                "fact_packet": narrator._provider_fact_packet_view(fact_packet=fact_packet),  # noqa: SLF001
            }
            for window_key, fact_packet in window_packets.items()
        ],
    }


def _batch_repair_provider_request_payload(
    *,
    scope_packets: Mapping[str, Mapping[str, Any]],
    invalid_response: Mapping[str, Any],
    validation_errors: Sequence[str],
) -> dict[str, Any]:
    payload = _batch_provider_request_payload(scope_packets=scope_packets)
    payload["repair_contract"] = {
        "goal": "repair the invalid multi-scope brief batch so every returned scope satisfies the Compass validation contract",
        "validation_errors": [str(error).strip() for error in validation_errors[:12] if str(error).strip()],
    }
    payload["previous_response"] = dict(invalid_response)
    return payload


def _window_batch_repair_provider_request_payload(
    *,
    window_packets: Mapping[str, Mapping[str, Any]],
    invalid_response: Mapping[str, Any],
    validation_errors: Sequence[str],
) -> dict[str, Any]:
    payload = _window_batch_provider_request_payload(window_packets=window_packets)
    payload["repair_contract"] = {
        "goal": "repair the invalid multi-window brief batch so every returned window satisfies the Compass validation contract",
        "validation_errors": [str(error).strip() for error in validation_errors[:12] if str(error).strip()],
    }
    payload["previous_response"] = dict(invalid_response)
    return payload


def _bundle_provider_system_prompt() -> str:
    return (
        narrator._provider_system_prompt()  # noqa: SLF001
        + " You are writing one Compass narrated bundle for one runtime packet. "
        "Return one independent brief per requested entry. "
        "Global and scoped entries must stay tied to their own supplied fact packets. "
        "Do not invent coverage, do not blend scopes together, and do not let one stronger lane flatten the others."
    )


def _bundle_provider_output_schema(
    *,
    window_keys: Sequence[str],
    scope_ids: Sequence[str],
) -> dict[str, Any]:
    window_tokens = [str(window_key).strip() for window_key in window_keys if str(window_key).strip()]
    scope_tokens = ["", *[str(scope_id).strip() for scope_id in scope_ids if str(scope_id).strip()]]
    return {
        "type": "object",
        "required": ["briefs"],
        "additionalProperties": False,
        "properties": {
            "briefs": {
                "type": "array",
                "minItems": 1,
                "maxItems": max(1, len(window_tokens) + len(scope_tokens)),
                "items": {
                    "type": "object",
                    "required": ["entry_kind", "window_key", "scope_id", "sections"],
                    "additionalProperties": False,
                    "properties": {
                        "entry_kind": {"type": "string", "enum": ["global", "scoped"]},
                        "window_key": {"type": "string", "enum": window_tokens},
                        "scope_id": {"type": "string", "enum": scope_tokens},
                        "sections": _sections_schema(),
                    },
                },
            }
        },
    }


def _bundle_provider_request_payload(
    *,
    repo_root: Path,
    global_packets_by_window: Mapping[str, Mapping[str, Any]],
    scoped_packets_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    first_packet = next(
        iter(global_packets_by_window.values()),
        next(iter(next(iter(scoped_packets_by_window.values()), {}).values()), {}),
    )
    base_payload = narrator._provider_request_payload(fact_packet=first_packet)  # noqa: SLF001
    global_entries = []
    scoped_entries = []
    global_substrates: dict[str, Mapping[str, Any]] = {}
    scoped_substrates: dict[str, dict[str, Mapping[str, Any]]] = {}
    for window_key, fact_packet in global_packets_by_window.items():
        prepared = _prepared_substrate_entry(repo_root=repo_root, fact_packet=fact_packet)
        current = dict(prepared["current"]) if isinstance(prepared.get("current"), Mapping) else {}
        previous_accepted = _compact_previous_accepted_provider_view(_mapping(current.get("previous_accepted")))
        global_substrates[str(window_key).strip()] = current
        entry = {
            "entry_kind": "global",
            "window_key": str(window_key).strip(),
            "scope_id": "",
            "substrate_fingerprint": str(current.get("fingerprint", "")).strip(),
            "delta": _compact_delta_provider_view(_mapping(prepared.get("delta"))),
            "current": compass_standup_brief_substrate.provider_substrate_view(substrate=current),
        }
        if previous_accepted:
            entry["previous_accepted"] = previous_accepted
        global_entries.append(entry)
    for window_key, window_packets in scoped_packets_by_window.items():
        window_entries = []
        window_substrates: dict[str, Mapping[str, Any]] = {}
        for scope_id, fact_packet in window_packets.items():
            prepared = _prepared_substrate_entry(repo_root=repo_root, fact_packet=fact_packet)
            current = dict(prepared["current"]) if isinstance(prepared.get("current"), Mapping) else {}
            previous_accepted = _compact_previous_accepted_provider_view(_mapping(current.get("previous_accepted")))
            window_substrates[str(scope_id).strip()] = current
            entry = {
                "entry_kind": "scoped",
                "window_key": str(window_key).strip(),
                "scope_id": str(scope_id).strip(),
                "substrate_fingerprint": str(current.get("fingerprint", "")).strip(),
                "delta": _compact_delta_provider_view(_mapping(prepared.get("delta"))),
                "current": compass_standup_brief_substrate.provider_substrate_view(substrate=current),
            }
            if previous_accepted:
                entry["previous_accepted"] = previous_accepted
            window_entries.append(entry)
        if window_entries:
            scoped_entries.extend(window_entries)
            scoped_substrates[str(window_key).strip()] = window_substrates
    bundle_fingerprint = _bundle_fingerprint(
        global_substrates_by_window=global_substrates,
        scoped_substrates_by_window=scoped_substrates,
    )
    return {
        "schema_version": narrator.STANDUP_BRIEF_SCHEMA_VERSION,
        "brief_contract": dict(base_payload.get("brief_contract", {})),
        "bundle_mode": "delta_substrate_update",
        "bundle_fingerprint": bundle_fingerprint,
        "bundle_contract": {
            "window_count": len(global_packets_by_window) or len(scoped_packets_by_window),
            "global_brief_count": len(global_packets_by_window),
            "scoped_brief_count": sum(
                len(window_packets)
                for window_packets in scoped_packets_by_window.values()
                if isinstance(window_packets, Mapping)
            ),
            "rules": [
                "return one brief per requested entry",
                "keep each entry isolated to its own narration substrate",
                "do not invent roll-up coverage to fill missing scoped detail",
                "update from current winners and prior accepted brief only",
            ],
        },
        "entries": global_entries + scoped_entries,
    }


def _compact_delta_provider_view(delta: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    changed_fact_keys = [
        str(token).strip()
        for token in delta.get("changed_fact_keys", [])
        if str(token).strip()
    ] if isinstance(delta.get("changed_fact_keys"), Sequence) and not isinstance(delta.get("changed_fact_keys"), (str, bytes, bytearray)) else []
    dropped_fact_keys = [
        str(token).strip()
        for token in delta.get("dropped_fact_keys", [])
        if str(token).strip()
    ] if isinstance(delta.get("dropped_fact_keys"), Sequence) and not isinstance(delta.get("dropped_fact_keys"), (str, bytes, bytearray)) else []
    changed_sections = [
        str(token).strip()
        for token in delta.get("changed_sections", [])
        if str(token).strip()
    ] if isinstance(delta.get("changed_sections"), Sequence) and not isinstance(delta.get("changed_sections"), (str, bytes, bytearray)) else []
    storyline_changed_keys = [
        str(token).strip()
        for token in delta.get("storyline_changed_keys", [])
        if str(token).strip()
    ] if isinstance(delta.get("storyline_changed_keys"), Sequence) and not isinstance(delta.get("storyline_changed_keys"), (str, bytes, bytearray)) else []
    if changed_fact_keys:
        payload["changed_fact_keys"] = changed_fact_keys
        payload["changed_fact_count"] = len(changed_fact_keys)
    if dropped_fact_keys:
        payload["dropped_fact_keys"] = dropped_fact_keys
        payload["dropped_fact_count"] = len(dropped_fact_keys)
    if changed_sections:
        payload["changed_sections"] = changed_sections
    if storyline_changed_keys:
        payload["storyline_changed_keys"] = storyline_changed_keys
    if bool(delta.get("freshness_changed")):
        payload["freshness_changed"] = True
    return payload


def _compact_previous_accepted_provider_view(previous_accepted: Mapping[str, Any]) -> dict[str, Any]:
    sections_payload = []
    for section in previous_accepted.get("sections", []):
        if not isinstance(section, Mapping):
            continue
        bullets = [
            str(bullet.get("text", "")).strip()
            for bullet in section.get("bullets", [])
            if isinstance(bullet, Mapping) and str(bullet.get("text", "")).strip()
        ]
        if bullets:
            sections_payload.append(
                {
                    "key": str(section.get("key", "")).strip(),
                    "bullets": bullets,
                }
            )
    if not sections_payload:
        return {}
    return {
        "generated_utc": str(previous_accepted.get("generated_utc", "")).strip(),
        "sections": sections_payload,
    }


def _compact_response_for_repair(invalid_response: Mapping[str, Any]) -> dict[str, Any]:
    briefs_payload = []
    for brief in invalid_response.get("briefs", []):
        if not isinstance(brief, Mapping):
            continue
        sections_payload = []
        for section in brief.get("sections", []):
            if not isinstance(section, Mapping):
                continue
            bullets = [
                str(bullet.get("text", "")).strip()
                for bullet in section.get("bullets", [])
                if isinstance(bullet, Mapping) and str(bullet.get("text", "")).strip()
            ]
            if bullets:
                sections_payload.append(
                    {
                        "key": str(section.get("key", "")).strip(),
                        "bullets": bullets,
                    }
                )
        briefs_payload.append(
            {
                "entry_kind": str(brief.get("entry_kind", "")).strip(),
                "window_key": str(brief.get("window_key", "")).strip(),
                "scope_id": str(brief.get("scope_id", "")).strip(),
                "sections": sections_payload,
            }
        )
    return {"briefs": briefs_payload}


def _bundle_repair_provider_request_payload(
    *,
    repo_root: Path,
    global_packets_by_window: Mapping[str, Mapping[str, Any]],
    scoped_packets_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
    invalid_response: Mapping[str, Any],
    validation_errors: Sequence[str],
) -> dict[str, Any]:
    payload = _bundle_provider_request_payload(
        repo_root=repo_root,
        global_packets_by_window=global_packets_by_window,
        scoped_packets_by_window=scoped_packets_by_window,
    )
    payload["repair_contract"] = {
        "goal": "repair the invalid Compass brief bundle so every returned entry satisfies the Compass validation contract",
        "validation_errors": [str(error).strip() for error in validation_errors[:16] if str(error).strip()],
    }
    payload["previous_response"] = _compact_response_for_repair(invalid_response)
    return payload


def _bundle_entry_key(*, window_key: str, scope_id: str = "") -> str:
    window_token = str(window_key).strip()
    scope_token = str(scope_id).strip()
    return f"{window_token}:{scope_token}" if scope_token else f"{window_token}:global"


def _prepared_substrate_entry(
    *,
    repo_root: Path,
    fact_packet: Mapping[str, Any],
) -> dict[str, Any]:
    previous_entry = narrator.latest_cached_entry_for_context(repo_root=repo_root, fact_packet=fact_packet)
    previous_substrate = (
        previous_entry.get("substrate")
        if isinstance(previous_entry, Mapping) and isinstance(previous_entry.get("substrate"), Mapping)
        else None
    )
    previous_brief = None
    if isinstance(previous_entry, Mapping):
        previous_brief = narrator._cache_ready_brief(  # noqa: SLF001
            fingerprint=str(previous_entry.get("fingerprint", "")).strip(),
            cached_entry=previous_entry,
            fact_packet=fact_packet,
            cache_mode="exact",
        )
    current_substrate = compass_standup_brief_substrate.build_narration_substrate(
        fact_packet=fact_packet,
        previous_substrate=previous_substrate,
        previous_brief=previous_brief,
        schema_version=narrator.STANDUP_BRIEF_SCHEMA_VERSION,
    )
    should_call, decision_reason, delta = compass_standup_brief_substrate.worth_calling_provider(
        current=current_substrate,
        previous=previous_substrate,
    )
    return {
        "current": current_substrate,
        "previous_entry": previous_entry if isinstance(previous_entry, Mapping) else None,
        "previous_substrate": previous_substrate if isinstance(previous_substrate, Mapping) else None,
        "previous_brief": previous_brief if isinstance(previous_brief, Mapping) else None,
        "should_call_provider": bool(should_call),
        "decision_reason": str(decision_reason).strip(),
        "delta": dict(delta),
    }


def _skip_brief(
    *,
    fingerprint: str,
    generated_utc: str,
    decision_reason: str,
) -> dict[str, Any]:
    return narrator._unavailable_ready_brief(  # noqa: SLF001
        fingerprint=fingerprint,
        generated_utc=generated_utc,
        reason="skipped_not_worth_calling",
        diagnostics={
            "provider_decision": "skipped_not_worth_calling",
            "skip_reason": str(decision_reason).strip(),
        },
    )


def _bundle_fingerprint(
    *,
    global_substrates_by_window: Mapping[str, Mapping[str, Any]],
    scoped_substrates_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> str:
    canonical = {
        "schema_version": narrator.STANDUP_BRIEF_SCHEMA_VERSION,
        "global": {
            str(window_key).strip(): str(substrate.get("fingerprint", "")).strip()
            for window_key, substrate in global_substrates_by_window.items()
            if str(window_key).strip() and isinstance(substrate, Mapping)
        },
        "scoped": {
            str(window_key).strip(): {
                str(scope_id).strip(): str(substrate.get("fingerprint", "")).strip()
                for scope_id, substrate in window_substrates.items()
                if str(scope_id).strip() and isinstance(substrate, Mapping)
            }
            for window_key, window_substrates in scoped_substrates_by_window.items()
            if str(window_key).strip() and isinstance(window_substrates, Mapping)
        },
    }
    return odylith_context_cache.fingerprint_payload(canonical)


def _batch_provider_request(
    *,
    scope_packets: Mapping[str, Mapping[str, Any]],
    config: odylith_reasoning.ReasoningConfig | None = None,
) -> odylith_reasoning.StructuredReasoningRequest:
    scope_ids = list(scope_packets)
    profile = narrator._provider_request_profile(config=config)  # noqa: SLF001
    return odylith_reasoning.StructuredReasoningRequest(
        system_prompt=_batch_provider_system_prompt(),
        schema_name="compass_standup_brief_batch",
        output_schema=_batch_provider_output_schema(scope_ids=scope_ids),
        prompt_payload=_batch_provider_request_payload(scope_packets=scope_packets),
        model=profile.model,
        reasoning_effort=profile.reasoning_effort,
        timeout_seconds=max(45.0, narrator._COMPASS_PROVIDER_TIMEOUT_SECONDS * 2),  # noqa: SLF001
    )


def _window_batch_provider_request(
    *,
    window_packets: Mapping[str, Mapping[str, Any]],
    config: odylith_reasoning.ReasoningConfig | None = None,
) -> odylith_reasoning.StructuredReasoningRequest:
    window_keys = list(window_packets)
    profile = narrator._provider_request_profile(config=config)  # noqa: SLF001
    return odylith_reasoning.StructuredReasoningRequest(
        system_prompt=_window_batch_provider_system_prompt(),
        schema_name="compass_standup_brief_window_batch",
        output_schema=_window_batch_provider_output_schema(window_keys=window_keys),
        prompt_payload=_window_batch_provider_request_payload(window_packets=window_packets),
        model=profile.model,
        reasoning_effort=profile.reasoning_effort,
        timeout_seconds=max(45.0, narrator._COMPASS_PROVIDER_TIMEOUT_SECONDS * 2),  # noqa: SLF001
    )


def _batch_repair_provider_request(
    *,
    scope_packets: Mapping[str, Mapping[str, Any]],
    invalid_response: Mapping[str, Any],
    validation_errors: Sequence[str],
    config: odylith_reasoning.ReasoningConfig | None = None,
) -> odylith_reasoning.StructuredReasoningRequest:
    scope_ids = list(scope_packets)
    profile = narrator._provider_request_profile(config=config)  # noqa: SLF001
    return odylith_reasoning.StructuredReasoningRequest(
        system_prompt=(
            _batch_provider_system_prompt()
            + " You are repairing a prior invalid batch reply. Fix only the cited scope failures and keep valid scopes valid."
        ),
        schema_name="compass_standup_brief_batch_repair",
        output_schema=_batch_provider_output_schema(scope_ids=scope_ids),
        prompt_payload=_batch_repair_provider_request_payload(
            scope_packets=scope_packets,
            invalid_response=invalid_response,
            validation_errors=validation_errors,
        ),
        model=profile.model,
        reasoning_effort=profile.reasoning_effort,
        timeout_seconds=max(45.0, narrator._COMPASS_PROVIDER_TIMEOUT_SECONDS * 2),  # noqa: SLF001
    )


def _window_batch_repair_provider_request(
    *,
    window_packets: Mapping[str, Mapping[str, Any]],
    invalid_response: Mapping[str, Any],
    validation_errors: Sequence[str],
    config: odylith_reasoning.ReasoningConfig | None = None,
) -> odylith_reasoning.StructuredReasoningRequest:
    window_keys = list(window_packets)
    profile = narrator._provider_request_profile(config=config)  # noqa: SLF001
    return odylith_reasoning.StructuredReasoningRequest(
        system_prompt=(
            _window_batch_provider_system_prompt()
            + " You are repairing a prior invalid batch reply. Fix only the cited window failures and keep valid windows valid."
        ),
        schema_name="compass_standup_brief_window_batch_repair",
        output_schema=_window_batch_provider_output_schema(window_keys=window_keys),
        prompt_payload=_window_batch_repair_provider_request_payload(
            window_packets=window_packets,
            invalid_response=invalid_response,
            validation_errors=validation_errors,
        ),
        model=profile.model,
        reasoning_effort=profile.reasoning_effort,
        timeout_seconds=max(45.0, narrator._COMPASS_PROVIDER_TIMEOUT_SECONDS * 2),  # noqa: SLF001
    )


def _bundle_provider_request(
    *,
    repo_root: Path,
    global_packets_by_window: Mapping[str, Mapping[str, Any]],
    scoped_packets_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
    config: odylith_reasoning.ReasoningConfig | None = None,
) -> odylith_reasoning.StructuredReasoningRequest:
    window_keys = list(
        dict.fromkeys(
            list(global_packets_by_window)
            + list(scoped_packets_by_window)
        )
    )
    scope_ids = [
        scope_id
        for window_packets in scoped_packets_by_window.values()
        if isinstance(window_packets, Mapping)
        for scope_id in window_packets
    ]
    profile = narrator._provider_request_profile(config=config)  # noqa: SLF001
    entry_count = len(window_keys) + len(scope_ids)
    scaled_timeout = max(30.0, 10.0 * max(1, entry_count))
    return odylith_reasoning.StructuredReasoningRequest(
        system_prompt=_bundle_provider_system_prompt(),
        schema_name="compass_standup_brief_bundle",
        output_schema=_bundle_provider_output_schema(window_keys=window_keys, scope_ids=scope_ids),
        prompt_payload=_bundle_provider_request_payload(
            repo_root=repo_root,
            global_packets_by_window=global_packets_by_window,
            scoped_packets_by_window=scoped_packets_by_window,
        ),
        model=profile.model,
        reasoning_effort=profile.reasoning_effort,
        timeout_seconds=scaled_timeout,
    )


def _bundle_repair_provider_request(
    *,
    repo_root: Path,
    global_packets_by_window: Mapping[str, Mapping[str, Any]],
    scoped_packets_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
    invalid_response: Mapping[str, Any],
    validation_errors: Sequence[str],
    config: odylith_reasoning.ReasoningConfig | None = None,
) -> odylith_reasoning.StructuredReasoningRequest:
    window_keys = list(
        dict.fromkeys(
            list(global_packets_by_window)
            + list(scoped_packets_by_window)
        )
    )
    scope_ids = [
        scope_id
        for window_packets in scoped_packets_by_window.values()
        if isinstance(window_packets, Mapping)
        for scope_id in window_packets
    ]
    profile = narrator._provider_request_profile(config=config)  # noqa: SLF001
    return odylith_reasoning.StructuredReasoningRequest(
        system_prompt=(
            _bundle_provider_system_prompt()
            + " You are repairing a prior invalid bundle reply. Fix only the cited entry failures and keep valid entries valid."
        ),
        schema_name="compass_standup_brief_bundle_repair",
        output_schema=_bundle_provider_output_schema(window_keys=window_keys, scope_ids=scope_ids),
        prompt_payload=_bundle_repair_provider_request_payload(
            repo_root=repo_root,
            global_packets_by_window=global_packets_by_window,
            scoped_packets_by_window=scoped_packets_by_window,
            invalid_response=invalid_response,
            validation_errors=validation_errors,
        ),
        model=profile.model,
        reasoning_effort=profile.reasoning_effort,
        timeout_seconds=max(45.0, narrator._COMPASS_PROVIDER_TIMEOUT_SECONDS * 2),  # noqa: SLF001
    )


def _validate_batch_response(
    *,
    response: Mapping[str, Any],
    scope_packets: Mapping[str, Mapping[str, Any]],
    generated_utc: str,
) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    ready: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    raw_briefs = response.get("briefs")
    if not isinstance(raw_briefs, Sequence):
        return {}, list(scope_packets), ["provider response omitted the briefs array"]

    seen_scope_ids: set[str] = set()
    for index, item in enumerate(raw_briefs, start=1):
        if not isinstance(item, Mapping):
            errors.append(f"brief {index} is malformed")
            continue
        scope_id = str(item.get("scope_id", "")).strip()
        if not scope_id:
            errors.append(f"brief {index} omitted scope_id")
            continue
        if scope_id not in scope_packets:
            errors.append(f"brief {index} returned unknown scope_id {scope_id}")
            continue
        if scope_id in seen_scope_ids:
            errors.append(f"brief {index} duplicated scope_id {scope_id}")
            continue
        seen_scope_ids.add(scope_id)
        sections, scope_errors = narrator._validate_brief_response(  # noqa: SLF001
            response={"sections": item.get("sections")},
            fact_packet=scope_packets[scope_id],
        )
        if scope_errors:
            errors.extend(f"{scope_id}: {error}" for error in scope_errors[:8])
            continue
        fact_packet = scope_packets[scope_id]
        ready[scope_id] = narrator._ready_brief(  # noqa: SLF001
            source="provider",
            fingerprint=narrator.standup_brief_fingerprint(fact_packet=fact_packet),
            generated_utc=generated_utc,
            sections=sections,
            evidence_lookup=narrator._brief_evidence_lookup(fact_packet=fact_packet),  # noqa: SLF001
        )

    missing = [scope_id for scope_id in scope_packets if scope_id not in ready]
    errors.extend(f"missing brief for {scope_id}" for scope_id in missing if scope_id not in seen_scope_ids)
    return ready, missing, errors


def _validate_window_batch_response(
    *,
    response: Mapping[str, Any],
    window_packets: Mapping[str, Mapping[str, Any]],
    generated_utc: str,
) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    ready: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    raw_briefs = response.get("briefs")
    if not isinstance(raw_briefs, Sequence):
        return {}, list(window_packets), ["provider response omitted the briefs array"]

    seen_window_keys: set[str] = set()
    for index, item in enumerate(raw_briefs, start=1):
        if not isinstance(item, Mapping):
            errors.append(f"brief {index} is malformed")
            continue
        window_key = str(item.get("window_key", "")).strip()
        if not window_key:
            errors.append(f"brief {index} omitted window_key")
            continue
        if window_key not in window_packets:
            errors.append(f"brief {index} returned unknown window_key {window_key}")
            continue
        if window_key in seen_window_keys:
            errors.append(f"brief {index} duplicated window_key {window_key}")
            continue
        seen_window_keys.add(window_key)
        sections, window_errors = narrator._validate_brief_response(  # noqa: SLF001
            response={"sections": item.get("sections")},
            fact_packet=window_packets[window_key],
        )
        if window_errors:
            errors.extend(f"{window_key}: {error}" for error in window_errors[:8])
            continue
        fact_packet = window_packets[window_key]
        ready[window_key] = narrator._ready_brief(  # noqa: SLF001
            source="provider",
            fingerprint=narrator.standup_brief_fingerprint(fact_packet=fact_packet),
            generated_utc=generated_utc,
            sections=sections,
            evidence_lookup=narrator._brief_evidence_lookup(fact_packet=fact_packet),  # noqa: SLF001
        )

    missing = [window_key for window_key in window_packets if window_key not in ready]
    errors.extend(f"missing brief for {window_key}" for window_key in missing if window_key not in seen_window_keys)
    return ready, missing, errors


def _validate_bundle_response(
    *,
    response: Mapping[str, Any],
    global_packets_by_window: Mapping[str, Mapping[str, Any]],
    scoped_packets_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
    generated_utc: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, dict[str, Any]]], list[str], dict[str, list[str]]]:
    ready_global: dict[str, dict[str, Any]] = {}
    ready_scoped: dict[str, dict[str, dict[str, Any]]] = {}
    errors: list[str] = []
    missing_scoped: dict[str, list[str]] = {}
    raw_briefs = response.get("briefs")
    if not isinstance(raw_briefs, Sequence):
        missing_global = list(global_packets_by_window)
        for window_key, packets in scoped_packets_by_window.items():
            if isinstance(packets, Mapping):
                missing_scoped[str(window_key).strip()] = list(packets)
        return ready_global, ready_scoped, ["provider response omitted the briefs array"], missing_scoped | {"__global__": missing_global}

    seen_global: set[str] = set()
    seen_scoped: set[tuple[str, str]] = set()
    for index, item in enumerate(raw_briefs, start=1):
        if not isinstance(item, Mapping):
            errors.append(f"brief {index} is malformed")
            continue
        entry_kind = str(item.get("entry_kind", "")).strip().lower()
        window_key = str(item.get("window_key", "")).strip()
        if entry_kind not in {"global", "scoped"}:
            errors.append(f"brief {index} returned unknown entry_kind")
            continue
        if not window_key:
            errors.append(f"brief {index} omitted window_key")
            continue
        if entry_kind == "global":
            fact_packet = global_packets_by_window.get(window_key)
            if not isinstance(fact_packet, Mapping):
                errors.append(f"brief {index} returned unknown global window_key {window_key}")
                continue
            if window_key in seen_global:
                errors.append(f"brief {index} duplicated global window_key {window_key}")
                continue
            seen_global.add(window_key)
            sections, window_errors = narrator._validate_brief_response(  # noqa: SLF001
                response={"sections": item.get("sections")},
                fact_packet=fact_packet,
            )
            if window_errors:
                errors.extend(f"global {window_key}: {error}" for error in window_errors[:8])
                continue
            ready_global[window_key] = narrator._ready_brief(  # noqa: SLF001
                source="provider",
                fingerprint=narrator.standup_brief_fingerprint(fact_packet=fact_packet),
                generated_utc=generated_utc,
                sections=sections,
                evidence_lookup=narrator._brief_evidence_lookup(fact_packet=fact_packet),  # noqa: SLF001
            )
            continue

        scope_id = str(item.get("scope_id", "")).strip()
        if not scope_id:
            errors.append(f"brief {index} omitted scope_id")
            continue
        window_packets = (
            scoped_packets_by_window.get(window_key)
            if isinstance(scoped_packets_by_window.get(window_key), Mapping)
            else {}
        )
        fact_packet = window_packets.get(scope_id) if isinstance(window_packets, Mapping) else None
        if not isinstance(fact_packet, Mapping):
            errors.append(f"brief {index} returned unknown scoped entry {window_key}/{scope_id}")
            continue
        scoped_key = (window_key, scope_id)
        if scoped_key in seen_scoped:
            errors.append(f"brief {index} duplicated scoped entry {window_key}/{scope_id}")
            continue
        seen_scoped.add(scoped_key)
        sections, scope_errors = narrator._validate_brief_response(  # noqa: SLF001
            response={"sections": item.get("sections")},
            fact_packet=fact_packet,
        )
        if scope_errors:
            errors.extend(f"scoped {window_key}/{scope_id}: {error}" for error in scope_errors[:8])
            continue
        ready_window = dict(ready_scoped.get(window_key, {}))
        ready_window[scope_id] = narrator._ready_brief(  # noqa: SLF001
            source="provider",
            fingerprint=narrator.standup_brief_fingerprint(fact_packet=fact_packet),
            generated_utc=generated_utc,
            sections=sections,
            evidence_lookup=narrator._brief_evidence_lookup(fact_packet=fact_packet),  # noqa: SLF001
        )
        ready_scoped[window_key] = ready_window

    missing_global = [
        window_key
        for window_key in global_packets_by_window
        if window_key not in ready_global
    ]
    errors.extend(
        f"missing brief for global {window_key}"
        for window_key in missing_global
        if window_key not in seen_global
    )
    for window_key, window_packets in scoped_packets_by_window.items():
        if not isinstance(window_packets, Mapping):
            continue
        window_missing = [
            scope_id
            for scope_id in window_packets
            if scope_id not in ready_scoped.get(window_key, {})
        ]
        if window_missing:
            missing_scoped[str(window_key).strip()] = window_missing
            errors.extend(
                f"missing brief for scoped {window_key}/{scope_id}"
                for scope_id in window_missing
                if (window_key, scope_id) not in seen_scoped
            )
    if missing_global:
        missing_scoped["__global__"] = missing_global
    return ready_global, ready_scoped, errors, missing_scoped


def _persist_provider_results(
    *,
    repo_root: Path,
    fact_packets_by_key: Mapping[str, Mapping[str, Any]],
    provider_results: Mapping[str, Mapping[str, Any]],
) -> None:
    if not provider_results:
        return
    cache_payload = narrator._load_cache(repo_root=repo_root)  # noqa: SLF001
    entries = cache_payload.get("entries")
    cache_entries = dict(entries) if isinstance(entries, Mapping) else {}
    for key, brief in provider_results.items():
        fact_packet = fact_packets_by_key.get(key)
        if not isinstance(fact_packet, Mapping):
            continue
        fingerprint = str(brief.get("fingerprint", "")).strip()
        generated_utc = str(brief.get("generated_utc", "")).strip()
        raw_sections = brief.get("sections")
        if not fingerprint or not generated_utc or not isinstance(raw_sections, Sequence):
            continue
        cache_entries[fingerprint] = {
            "generated_utc": generated_utc,
            "sections": [dict(item) for item in raw_sections if isinstance(item, Mapping)],
            "evidence_lookup": {
                str(fact_id).strip(): dict(entry)
                for fact_id, entry in (
                    brief.get("evidence_lookup", {})
                    if isinstance(brief.get("evidence_lookup", {}), Mapping)
                    else {}
                ).items()
                if str(fact_id).strip() and isinstance(entry, Mapping)
            },
            "context": narrator._cache_context(fact_packet=fact_packet),  # noqa: SLF001
            "substrate_fingerprint": (
                str(brief.get("substrate_fingerprint", "")).strip()
                or narrator.standup_brief_fingerprint(fact_packet=fact_packet)
            ),
            "bundle_fingerprint": str(brief.get("bundle_fingerprint", "")).strip(),
            "provider_decision": str(brief.get("provider_decision", "")).strip().lower() or "provider_called",
            "last_successful_narration_fingerprint": (
                str(brief.get("last_successful_narration_fingerprint", "")).strip()
                or narrator.standup_brief_fingerprint(fact_packet=fact_packet)
            ),
            "substrate": narrator._narration_substrate(fact_packet=fact_packet),  # noqa: SLF001
        }
    narrator._write_cache(  # noqa: SLF001
        repo_root=repo_root,
        payload={
            "version": narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            "entries": cache_entries,
        },
    )


def _persist_scoped_provider_results(
    *,
    repo_root: Path,
    fact_packets_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
    provider_results_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> None:
    for window_key, provider_results in provider_results_by_window.items():
        fact_packets = fact_packets_by_window.get(window_key)
        if not isinstance(fact_packets, Mapping) or not isinstance(provider_results, Mapping):
            continue
        _persist_provider_results(
            repo_root=repo_root,
            fact_packets_by_key=fact_packets,
            provider_results=provider_results,
        )


def _bundle_request_payload_chars(
    *,
    repo_root: Path,
    global_packets_by_window: Mapping[str, Mapping[str, Any]],
    scoped_packets_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> int:
    payload = _bundle_provider_request_payload(
        repo_root=repo_root,
        global_packets_by_window=global_packets_by_window,
        scoped_packets_by_window=scoped_packets_by_window,
    )
    return len(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def _copy_window_pack(
    packets_by_window: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        str(window_key).strip(): {
            str(scope_id).strip(): dict(fact_packet)
            for scope_id, fact_packet in window_packets.items()
            if str(scope_id).strip() and isinstance(fact_packet, Mapping)
        }
        for window_key, window_packets in packets_by_window.items()
        if str(window_key).strip() and isinstance(window_packets, Mapping)
    }


def _bundle_pack_has_entries(
    *,
    global_packets_by_window: Mapping[str, Mapping[str, Any]],
    scoped_packets_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> bool:
    return bool(global_packets_by_window) or any(
        isinstance(window_packets, Mapping) and bool(window_packets)
        for window_packets in scoped_packets_by_window.values()
    )


def _bundle_pack_entry_count(
    *,
    global_packets_by_window: Mapping[str, Mapping[str, Any]],
    scoped_packets_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> int:
    scoped_count = sum(
        len(window_packets)
        for window_packets in scoped_packets_by_window.values()
        if isinstance(window_packets, Mapping)
    )
    return len(global_packets_by_window) + scoped_count


def _pack_with_added_global(
    *,
    global_packets_by_window: Mapping[str, Mapping[str, Any]],
    scoped_packets_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
    window_key: str,
    fact_packet: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, dict[str, Mapping[str, Any]]]]:
    updated_global = dict(global_packets_by_window)
    updated_global[str(window_key).strip()] = dict(fact_packet)
    return updated_global, _copy_window_pack(scoped_packets_by_window)


def _pack_with_added_scoped(
    *,
    global_packets_by_window: Mapping[str, Mapping[str, Any]],
    scoped_packets_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
    window_key: str,
    scope_id: str,
    fact_packet: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, dict[str, Mapping[str, Any]]]]:
    updated_global = dict(global_packets_by_window)
    updated_scoped = _copy_window_pack(scoped_packets_by_window)
    window_token = str(window_key).strip()
    scope_token = str(scope_id).strip()
    updated_window = dict(updated_scoped.get(window_token, {}))
    updated_window[scope_token] = dict(fact_packet)
    updated_scoped[window_token] = updated_window
    return updated_global, updated_scoped


def _provider_failure_brief_for_packet(
    *,
    fact_packet: Mapping[str, Any],
    generated_utc: str,
    provider: odylith_reasoning.ReasoningProvider,
) -> dict[str, Any]:
    fingerprint = narrator.standup_brief_fingerprint(fact_packet=fact_packet)
    return narrator.unavailable_brief_for_provider_failure(
        fingerprint=fingerprint,
        generated_utc=generated_utc,
        provider=provider,
        fallback_reason="provider_error",
    )


def _provider_failure_briefs_for_packets(
    *,
    global_packets_by_window: Mapping[str, Mapping[str, Any]],
    scoped_packets_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
    generated_utc: str,
    provider: odylith_reasoning.ReasoningProvider,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, dict[str, Any]]]]:
    global_failures = {
        str(window_key).strip(): _provider_failure_brief_for_packet(
            fact_packet=fact_packet,
            generated_utc=generated_utc,
            provider=provider,
        )
        for window_key, fact_packet in global_packets_by_window.items()
        if str(window_key).strip() and isinstance(fact_packet, Mapping)
    }
    scoped_failures: dict[str, dict[str, dict[str, Any]]] = {}
    for window_key, window_packets in scoped_packets_by_window.items():
        if not str(window_key).strip() or not isinstance(window_packets, Mapping):
            continue
        failed_window = {
            str(scope_id).strip(): _provider_failure_brief_for_packet(
                fact_packet=fact_packet,
                generated_utc=generated_utc,
                provider=provider,
            )
            for scope_id, fact_packet in window_packets.items()
            if str(scope_id).strip() and isinstance(fact_packet, Mapping)
        }
        if failed_window:
            scoped_failures[str(window_key).strip()] = failed_window
    return global_failures, scoped_failures


def _bundle_provider_subset_by_window(
    *,
    repo_root: Path,
    global_packets_by_window: Mapping[str, Mapping[str, Any]],
    scoped_packets_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
    max_payload_chars: int,
    max_entries: int = DEFAULT_BUNDLE_PROVIDER_MAX_ENTRIES,
) -> list[tuple[dict[str, Mapping[str, Any]], dict[str, dict[str, Mapping[str, Any]]]]]:
    total_chars = _bundle_request_payload_chars(
        repo_root=repo_root,
        global_packets_by_window=global_packets_by_window,
        scoped_packets_by_window=scoped_packets_by_window,
    )
    if total_chars <= max(1, int(max_payload_chars)) and _bundle_pack_entry_count(
        global_packets_by_window=global_packets_by_window,
        scoped_packets_by_window=scoped_packets_by_window,
    ) <= max(1, int(max_entries)):
        return [(dict(global_packets_by_window), _copy_window_pack(scoped_packets_by_window))]
    packs: list[tuple[dict[str, Mapping[str, Any]], dict[str, dict[str, Mapping[str, Any]]]]] = []
    current_globals: dict[str, Mapping[str, Any]] = {}
    current_scoped: dict[str, dict[str, Mapping[str, Any]]] = {}

    for window_key, fact_packet in global_packets_by_window.items():
        if not str(window_key).strip() or not isinstance(fact_packet, Mapping):
            continue
        trial_globals, trial_scoped = _pack_with_added_global(
            global_packets_by_window=current_globals,
            scoped_packets_by_window=current_scoped,
            window_key=str(window_key).strip(),
            fact_packet=fact_packet,
        )
        if _bundle_pack_has_entries(
            global_packets_by_window=current_globals,
            scoped_packets_by_window=current_scoped,
        ) and (
            _bundle_pack_entry_count(
                global_packets_by_window=trial_globals,
                scoped_packets_by_window=trial_scoped,
            ) > max(1, int(max_entries))
            or _bundle_request_payload_chars(
                repo_root=repo_root,
                global_packets_by_window=trial_globals,
                scoped_packets_by_window=trial_scoped,
            ) > max(1, int(max_payload_chars))
        ):
            packs.append((dict(current_globals), _copy_window_pack(current_scoped)))
            current_globals = {}
            current_scoped = {}
        current_globals[str(window_key).strip()] = dict(fact_packet)
    if _bundle_pack_has_entries(
        global_packets_by_window=current_globals,
        scoped_packets_by_window=current_scoped,
    ):
        packs.append((dict(current_globals), _copy_window_pack(current_scoped)))

    current_globals = {}
    current_scoped = {}
    for window_key, window_packets in scoped_packets_by_window.items():
        if not str(window_key).strip() or not isinstance(window_packets, Mapping):
            continue
        for scope_id, fact_packet in window_packets.items():
            if not str(scope_id).strip() or not isinstance(fact_packet, Mapping):
                continue
            trial_globals, trial_scoped = _pack_with_added_scoped(
                global_packets_by_window=current_globals,
                scoped_packets_by_window=current_scoped,
                window_key=str(window_key).strip(),
                scope_id=str(scope_id).strip(),
                fact_packet=fact_packet,
            )
            if _bundle_pack_has_entries(
                global_packets_by_window=current_globals,
                scoped_packets_by_window=current_scoped,
            ) and (
                _bundle_pack_entry_count(
                    global_packets_by_window=trial_globals,
                    scoped_packets_by_window=trial_scoped,
                ) > max(1, int(max_entries))
                or _bundle_request_payload_chars(
                    repo_root=repo_root,
                    global_packets_by_window=trial_globals,
                    scoped_packets_by_window=trial_scoped,
                ) > max(1, int(max_payload_chars))
            ):
                packs.append((dict(current_globals), _copy_window_pack(current_scoped)))
                current_globals = {}
                current_scoped = {}
            current_globals, current_scoped = _pack_with_added_scoped(
                global_packets_by_window=current_globals,
                scoped_packets_by_window=current_scoped,
                window_key=str(window_key).strip(),
                scope_id=str(scope_id).strip(),
                fact_packet=fact_packet,
            )
    if _bundle_pack_has_entries(
        global_packets_by_window=current_globals,
        scoped_packets_by_window=current_scoped,
    ):
        packs.append((dict(current_globals), _copy_window_pack(current_scoped)))
    return packs


def _resolve_bundle_pack(
    *,
    repo_root: Path,
    global_packets_by_window: Mapping[str, Mapping[str, Any]],
    scoped_packets_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
    generated_utc: str,
    runtime_packet_fingerprint: str,
    config: odylith_reasoning.ReasoningConfig,
    provider: odylith_reasoning.ReasoningProvider,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, dict[str, Any]]]]:
    if not global_packets_by_window and not scoped_packets_by_window:
        return {}, {}

    global_substrates = {
        str(window_key).strip(): compass_standup_brief_substrate.build_narration_substrate(
            fact_packet=fact_packet,
            schema_version=narrator.STANDUP_BRIEF_SCHEMA_VERSION,
        )
        for window_key, fact_packet in global_packets_by_window.items()
        if str(window_key).strip() and isinstance(fact_packet, Mapping)
    }
    scoped_substrates = {
        str(window_key).strip(): {
            str(scope_id).strip(): compass_standup_brief_substrate.build_narration_substrate(
                fact_packet=fact_packet,
                schema_version=narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            )
            for scope_id, fact_packet in window_packets.items()
            if str(scope_id).strip() and isinstance(fact_packet, Mapping)
        }
        for window_key, window_packets in scoped_packets_by_window.items()
        if str(window_key).strip() and isinstance(window_packets, Mapping)
    }
    bundle_fingerprint = _bundle_fingerprint(
        global_substrates_by_window=global_substrates,
        scoped_substrates_by_window=scoped_substrates,
    )
    substrate_fingerprints = {
        _bundle_entry_key(window_key=window_key): str(substrate.get("fingerprint", "")).strip()
        for window_key, substrate in global_substrates.items()
    }
    for window_key, window_substrates in scoped_substrates.items():
        for scope_id, substrate in window_substrates.items():
            substrate_fingerprints[_bundle_entry_key(window_key=window_key, scope_id=scope_id)] = str(
                substrate.get("fingerprint", "")
            ).strip()
    request_started = time.perf_counter()
    output_chars = 0
    repair_count = 0
    initial_input_chars = _bundle_request_payload_chars(
        repo_root=repo_root,
        global_packets_by_window=global_packets_by_window,
        scoped_packets_by_window=scoped_packets_by_window,
    )
    repair_input_chars = 0

    initial_request = _bundle_provider_request(
        repo_root=repo_root,
        global_packets_by_window=global_packets_by_window,
        scoped_packets_by_window=scoped_packets_by_window,
        config=config,
    )
    request_model, request_reasoning_effort = _request_profile_metadata(initial_request)
    raw_result = provider.generate_structured(request=initial_request)
    if isinstance(raw_result, Mapping):
        output_chars += len(json.dumps(raw_result, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    if not isinstance(raw_result, Mapping):
        failure = odylith_reasoning.provider_failure_metadata(provider)
        compass_standup_brief_telemetry.record_attempt(
            repo_root=repo_root,
            runtime_packet_fingerprint=str(runtime_packet_fingerprint).strip(),
            bundle_fingerprint=bundle_fingerprint,
            substrate_fingerprints=substrate_fingerprints,
            provider_decision="provider_called",
            input_chars=initial_input_chars,
            output_chars=0,
            latency_ms=(time.perf_counter() - request_started) * 1000.0,
            repair_count=0,
            salvage_count=0,
            provider_call_count=1,
            failure_kind=(
                narrator._failure_reason_from_provider_code(failure.get("code", ""))  # noqa: SLF001
                if hasattr(narrator, "_failure_reason_from_provider_code")
                else ""
            ),
            provider_code=str(failure.get("code", "")).strip(),
            provider_detail=str(failure.get("detail", "")).strip(),
            model=request_model,
            reasoning_effort=request_reasoning_effort,
        )
        return {}, {}

    ready_global, ready_scoped, errors, missing_entries = _validate_bundle_response(
        response=raw_result,
        global_packets_by_window=global_packets_by_window,
        scoped_packets_by_window=scoped_packets_by_window,
        generated_utc=generated_utc,
    )
    missing_global = {
        window_key: global_packets_by_window[window_key]
        for window_key in missing_entries.get("__global__", [])
        if window_key in global_packets_by_window
    }
    missing_scoped = {
        window_key: {
            scope_id: scoped_packets_by_window[window_key][scope_id]
            for scope_id in scope_ids
            if window_key in scoped_packets_by_window and scope_id in scoped_packets_by_window[window_key]
        }
        for window_key, scope_ids in missing_entries.items()
        if window_key != "__global__" and scope_ids
    }
    if errors and (missing_global or missing_scoped):
        repair_count = 1
        repair_request = _bundle_repair_provider_request(
            repo_root=repo_root,
            global_packets_by_window=missing_global,
            scoped_packets_by_window=missing_scoped,
            invalid_response=raw_result,
            validation_errors=errors,
            config=config,
        )
        repair_input_chars = len(
            json.dumps(repair_request.prompt_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        )
        repair_model, repair_reasoning_effort = _request_profile_metadata(repair_request)
        repaired_result = provider.generate_structured(request=repair_request)
        if isinstance(repaired_result, Mapping):
            output_chars += len(json.dumps(repaired_result, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
            if repair_model:
                request_model = repair_model
            if repair_reasoning_effort:
                request_reasoning_effort = repair_reasoning_effort
            repaired_global, repaired_scoped, _repair_errors, _repair_missing = _validate_bundle_response(
                response=repaired_result,
                global_packets_by_window=missing_global,
                scoped_packets_by_window=missing_scoped,
                generated_utc=generated_utc,
            )
            ready_global.update(repaired_global)
            for window_key, window_results in repaired_scoped.items():
                merged_window = dict(ready_scoped.get(window_key, {}))
                merged_window.update(window_results)
                ready_scoped[window_key] = merged_window
    for window_key, brief in ready_global.items():
        if isinstance(brief, Mapping):
            brief["bundle_fingerprint"] = bundle_fingerprint
            brief["substrate_fingerprint"] = str(global_substrates.get(window_key, {}).get("fingerprint", "")).strip()
            brief["provider_decision"] = "provider_called"
            brief["last_successful_narration_fingerprint"] = str(
                global_substrates.get(window_key, {}).get("fingerprint", "")
            ).strip()
    for window_key, window_results in ready_scoped.items():
        if not isinstance(window_results, Mapping):
            continue
        for scope_id, brief in window_results.items():
            if not isinstance(brief, Mapping):
                continue
            brief["bundle_fingerprint"] = bundle_fingerprint
            brief["substrate_fingerprint"] = str(
                scoped_substrates.get(window_key, {}).get(scope_id, {}).get("fingerprint", "")
            ).strip()
            brief["provider_decision"] = "provider_called"
            brief["last_successful_narration_fingerprint"] = str(
                scoped_substrates.get(window_key, {}).get(scope_id, {}).get("fingerprint", "")
            ).strip()
    total_expected = len(global_substrates) + sum(len(window) for window in scoped_substrates.values())
    total_ready = len(ready_global) + sum(len(window) for window in ready_scoped.values())
    compass_standup_brief_telemetry.record_attempt(
        repo_root=repo_root,
        runtime_packet_fingerprint=str(runtime_packet_fingerprint).strip(),
        bundle_fingerprint=bundle_fingerprint,
        substrate_fingerprints=substrate_fingerprints,
        provider_decision="provider_called",
        input_chars=initial_input_chars + repair_input_chars,
        output_chars=output_chars,
        latency_ms=(time.perf_counter() - request_started) * 1000.0,
        repair_count=repair_count,
        salvage_count=max(0, total_ready - max(0, total_expected - len(missing_global) - sum(len(v) for k, v in missing_scoped.items() if k != "__global__"))),
        failure_kind="invalid_batch" if errors and total_ready < total_expected else "",
        repair_input_chars=repair_input_chars,
        provider_call_count=1 + repair_count,
        model=request_model,
        reasoning_effort=request_reasoning_effort,
    )
    return ready_global, ready_scoped


def _build_single_window_brief(
    *,
    repo_root: Path,
    window_key: str,
    fact_packet: Mapping[str, Any],
    generated_utc: str,
    config: odylith_reasoning.ReasoningConfig,
    provider: odylith_reasoning.ReasoningProvider,
) -> dict[str, dict[str, Any]]:
    brief = narrator.build_standup_brief(
        repo_root=repo_root,
        fact_packet=fact_packet,
        generated_utc=generated_utc,
        config=config,
        provider=provider,
        allow_provider=True,
        prefer_provider=False,
    )
    if str(brief.get("status", "")).strip().lower() != "ready":
        return {}
    return {window_key: brief}


def _build_single_scope_brief(
    *,
    repo_root: Path,
    scope_id: str,
    fact_packet: Mapping[str, Any],
    generated_utc: str,
    config: odylith_reasoning.ReasoningConfig,
    provider: odylith_reasoning.ReasoningProvider,
) -> dict[str, dict[str, Any]]:
    brief = narrator.build_standup_brief(
        repo_root=repo_root,
        fact_packet=fact_packet,
        generated_utc=generated_utc,
        config=config,
        provider=provider,
        allow_provider=True,
        prefer_provider=False,
    )
    if str(brief.get("status", "")).strip().lower() != "ready":
        return {}
    return {scope_id: brief}


def _resolve_window_pack(
    *,
    repo_root: Path,
    pack_mapping: Mapping[str, Mapping[str, Any]],
    generated_utc: str,
    config: odylith_reasoning.ReasoningConfig,
    provider: odylith_reasoning.ReasoningProvider,
    fallback_to_single: bool,
) -> dict[str, dict[str, Any]]:
    if not pack_mapping:
        return {}

    raw_result = provider.generate_structured(
        request=_window_batch_provider_request(window_packets=pack_mapping, config=config)
    )
    if not isinstance(raw_result, Mapping):
        if _provider_failure_should_abort_fanout(provider):
            return {}
        if not fallback_to_single:
            return {}
        ready: dict[str, dict[str, Any]] = {}
        for window_key, fact_packet in pack_mapping.items():
            ready.update(
                _build_single_window_brief(
                    repo_root=repo_root,
                    window_key=window_key,
                    fact_packet=fact_packet,
                    generated_utc=generated_utc,
                    config=config,
                    provider=provider,
                )
            )
        return ready

    ready, missing_window_keys, errors = _validate_window_batch_response(
        response=raw_result,
        window_packets=pack_mapping,
        generated_utc=generated_utc,
    )
    if errors and missing_window_keys:
        repair_window_packets = {
            window_key: pack_mapping[window_key]
            for window_key in missing_window_keys
            if window_key in pack_mapping
        }
        repaired_result = provider.generate_structured(
            request=_window_batch_repair_provider_request(
                window_packets=repair_window_packets,
                invalid_response=raw_result,
                validation_errors=errors,
                config=config,
            )
        )
        if isinstance(repaired_result, Mapping):
            repaired_ready, _repaired_missing_window_keys, _repaired_errors = _validate_window_batch_response(
                response=repaired_result,
                window_packets=repair_window_packets,
                generated_utc=generated_utc,
            )
            ready.update(repaired_ready)
        elif _provider_failure_should_abort_fanout(provider):
            return ready

    unresolved_window_packets = {
        window_key: fact_packet
        for window_key, fact_packet in pack_mapping.items()
        if window_key not in ready
    }
    if not unresolved_window_packets or not fallback_to_single:
        return ready

    for window_key, fact_packet in unresolved_window_packets.items():
        ready.update(
            _build_single_window_brief(
                repo_root=repo_root,
                window_key=window_key,
                fact_packet=fact_packet,
                generated_utc=generated_utc,
                config=config,
                provider=provider,
            )
        )
    return ready


def _resolve_scope_pack(
    *,
    repo_root: Path,
    pack_mapping: Mapping[str, Mapping[str, Any]],
    generated_utc: str,
    config: odylith_reasoning.ReasoningConfig,
    provider: odylith_reasoning.ReasoningProvider,
) -> dict[str, dict[str, Any]]:
    if not pack_mapping:
        return {}

    raw_result = provider.generate_structured(
        request=_batch_provider_request(scope_packets=pack_mapping, config=config)
    )
    if not isinstance(raw_result, Mapping):
        if _provider_failure_should_abort_fanout(provider):
            return {}
        if len(pack_mapping) == 1:
            scope_id, fact_packet = next(iter(pack_mapping.items()))
            return _build_single_scope_brief(
                repo_root=repo_root,
                scope_id=scope_id,
                fact_packet=fact_packet,
                generated_utc=generated_utc,
                config=config,
                provider=provider,
            )
        ready: dict[str, dict[str, Any]] = {}
        for split_pack in _split_scope_packets(pack_mapping):
            ready.update(
                _resolve_scope_pack(
                    repo_root=repo_root,
                    pack_mapping=split_pack,
                    generated_utc=generated_utc,
                    config=config,
                    provider=provider,
                )
            )
        return ready

    ready, missing_scope_ids, errors = _validate_batch_response(
        response=raw_result,
        scope_packets=pack_mapping,
        generated_utc=generated_utc,
    )
    if errors and missing_scope_ids:
        repair_scope_packets = {
            scope_id: pack_mapping[scope_id]
            for scope_id in missing_scope_ids
            if scope_id in pack_mapping
        }
        repaired_result = provider.generate_structured(
            request=_batch_repair_provider_request(
                scope_packets=repair_scope_packets,
                invalid_response=raw_result,
                validation_errors=errors,
                config=config,
            )
        )
        if isinstance(repaired_result, Mapping):
            repaired_ready, _repaired_missing_scope_ids, _repaired_errors = _validate_batch_response(
                response=repaired_result,
                scope_packets=repair_scope_packets,
                generated_utc=generated_utc,
            )
            ready.update(repaired_ready)
        elif _provider_failure_should_abort_fanout(provider):
            return ready

    unresolved_scope_packets = {
        scope_id: fact_packet
        for scope_id, fact_packet in pack_mapping.items()
        if scope_id not in ready
    }
    if not unresolved_scope_packets:
        return ready

    if len(unresolved_scope_packets) == 1:
        scope_id, fact_packet = next(iter(unresolved_scope_packets.items()))
        ready.update(
            _build_single_scope_brief(
                repo_root=repo_root,
                scope_id=scope_id,
                fact_packet=fact_packet,
                generated_utc=generated_utc,
                config=config,
                provider=provider,
            )
        )
        return ready

    for split_pack in _split_scope_packets(unresolved_scope_packets):
        ready.update(
            _resolve_scope_pack(
                repo_root=repo_root,
                pack_mapping=split_pack,
                generated_utc=generated_utc,
                config=config,
                provider=provider,
            )
        )
    return ready


def build_window_briefs(
    *,
    repo_root: Path,
    fact_packets_by_window: Mapping[str, Mapping[str, Any]],
    generated_utc: str,
    config: odylith_reasoning.ReasoningConfig | None = None,
    provider: odylith_reasoning.ReasoningProvider | None = None,
    fallback_to_single: bool = False,
) -> dict[str, dict[str, Any]]:
    """Build global window briefs with exact-cache reuse first, then one bounded provider batch."""

    repo_root = Path(repo_root).resolve()
    if not fact_packets_by_window:
        return {}

    resolved_config = config or odylith_reasoning.reasoning_config_from_env(repo_root=repo_root)
    resolved_provider = provider or odylith_reasoning.provider_from_config(
        resolved_config,
        repo_root=repo_root,
        require_auto_mode=False,
        allow_implicit_local_provider=True,
    )
    resolved_profile = odylith_reasoning.cheap_structured_reasoning_profile(resolved_config)

    results: dict[str, dict[str, Any]] = {}
    cold_packets: dict[str, Mapping[str, Any]] = {}
    for window_key, fact_packet in fact_packets_by_window.items():
        cached = narrator.build_standup_brief(
            repo_root=repo_root,
            fact_packet=fact_packet,
            generated_utc=generated_utc,
            config=resolved_config,
            provider=resolved_provider,
            allow_provider=False,
            prefer_provider=False,
        )
        if cached.get("status") == "ready" and cached.get("source") == "cache":
            results[window_key] = cached
        else:
            cold_packets[window_key] = fact_packet

    if not cold_packets or resolved_provider is None:
        return results

    provider_results = _resolve_window_pack(
        repo_root=repo_root,
        pack_mapping=cold_packets,
        generated_utc=generated_utc,
        config=resolved_config,
        provider=resolved_provider,
        fallback_to_single=fallback_to_single,
    )
    _persist_provider_results(
        repo_root=repo_root,
        fact_packets_by_key=fact_packets_by_window,
        provider_results=provider_results,
    )
    results.update(provider_results)
    return results


def build_brief_bundle(
    *,
    repo_root: Path,
    global_fact_packets_by_window: Mapping[str, Mapping[str, Any]],
    scoped_fact_packets_by_window: Mapping[str, Mapping[str, Mapping[str, Any]]],
    generated_utc: str,
    runtime_packet_fingerprint: str = "",
    config: odylith_reasoning.ReasoningConfig | None = None,
    provider: odylith_reasoning.ReasoningProvider | None = None,
    max_bundle_payload_chars: int = DEFAULT_BUNDLE_PROVIDER_MAX_CHARS,
    defer_scoped: bool = False,
) -> dict[str, Any]:
    """Build one packet-level narrated bundle with exact-cache reuse first."""

    repo_root = Path(repo_root).resolve()
    resolved_config = config or odylith_reasoning.reasoning_config_from_env(repo_root=repo_root)
    resolved_provider = provider or odylith_reasoning.provider_from_config(
        resolved_config,
        repo_root=repo_root,
        require_auto_mode=False,
        allow_implicit_local_provider=True,
    )
    resolved_profile = odylith_reasoning.cheap_structured_reasoning_profile(resolved_config)

    ready_global: dict[str, dict[str, Any]] = {}
    ready_scoped: dict[str, dict[str, dict[str, Any]]] = {}
    cold_global: dict[str, Mapping[str, Any]] = {}
    cold_scoped: dict[str, dict[str, Mapping[str, Any]]] = {}
    skipped_global: dict[str, dict[str, Any]] = {}
    skipped_scoped: dict[str, dict[str, dict[str, Any]]] = {}

    for window_key, fact_packet in global_fact_packets_by_window.items():
        cached = narrator.build_standup_brief(
            repo_root=repo_root,
            fact_packet=fact_packet,
            generated_utc=generated_utc,
            config=resolved_config,
            provider=resolved_provider,
            allow_provider=False,
            prefer_provider=False,
        )
        if cached.get("status") == "ready" and cached.get("source") == "cache":
            ready_global[str(window_key).strip()] = cached
        else:
            prepared = _prepared_substrate_entry(repo_root=repo_root, fact_packet=fact_packet)
            if prepared.get("should_call_provider"):
                cold_global[str(window_key).strip()] = fact_packet
            else:
                current_substrate = (
                    dict(prepared.get("current"))
                    if isinstance(prepared.get("current"), Mapping)
                    else {}
                )
                fingerprint = str(current_substrate.get("fingerprint", "")).strip()
                skipped_global[str(window_key).strip()] = _skip_brief(
                    fingerprint=fingerprint,
                    generated_utc=generated_utc,
                    decision_reason=str(prepared.get("decision_reason", "")).strip() or "no_winner_change",
                )
                compass_standup_brief_telemetry.record_attempt(
                    repo_root=repo_root,
                    runtime_packet_fingerprint=str(runtime_packet_fingerprint).strip(),
                    bundle_fingerprint="",
                    substrate_fingerprints={str(window_key).strip(): fingerprint},
                    provider_decision="skipped_not_worth_calling",
                    input_chars=0,
                    output_chars=0,
                    latency_ms=0.0,
                    repair_count=0,
                    salvage_count=0,
                    skip_reason=str(prepared.get("decision_reason", "")).strip(),
                    model=str(resolved_profile.model or "").strip(),
                    reasoning_effort=str(resolved_profile.reasoning_effort or "minimal").strip(),
                )

    for window_key, window_packets in scoped_fact_packets_by_window.items():
        if not isinstance(window_packets, Mapping):
            continue
        cached_window: dict[str, dict[str, Any]] = {}
        cold_window: dict[str, Mapping[str, Any]] = {}
        for scope_id, fact_packet in window_packets.items():
            cached = narrator.build_standup_brief(
                repo_root=repo_root,
                fact_packet=fact_packet,
                generated_utc=generated_utc,
                config=resolved_config,
                provider=resolved_provider,
                allow_provider=False,
                prefer_provider=False,
            )
            if cached.get("status") == "ready" and cached.get("source") == "cache":
                cached_window[str(scope_id).strip()] = cached
            else:
                prepared = _prepared_substrate_entry(repo_root=repo_root, fact_packet=fact_packet)
                if prepared.get("should_call_provider"):
                    cold_window[str(scope_id).strip()] = fact_packet
                else:
                    scope_token = str(scope_id).strip()
                    current_substrate = (
                        dict(prepared.get("current"))
                        if isinstance(prepared.get("current"), Mapping)
                        else {}
                    )
                    fingerprint = str(current_substrate.get("fingerprint", "")).strip()
                    skipped_window = dict(skipped_scoped.get(str(window_key).strip(), {}))
                    skipped_window[scope_token] = _skip_brief(
                        fingerprint=fingerprint,
                        generated_utc=generated_utc,
                        decision_reason=str(prepared.get("decision_reason", "")).strip() or "no_winner_change",
                    )
                    skipped_scoped[str(window_key).strip()] = skipped_window
                    compass_standup_brief_telemetry.record_attempt(
                        repo_root=repo_root,
                        runtime_packet_fingerprint=str(runtime_packet_fingerprint).strip(),
                        bundle_fingerprint="",
                        substrate_fingerprints={_bundle_entry_key(window_key=str(window_key).strip(), scope_id=scope_token): fingerprint},
                        provider_decision="skipped_not_worth_calling",
                        input_chars=0,
                        output_chars=0,
                        latency_ms=0.0,
                        repair_count=0,
                        salvage_count=0,
                        skip_reason=str(prepared.get("decision_reason", "")).strip(),
                        model=str(resolved_profile.model or "").strip(),
                        reasoning_effort=str(resolved_profile.reasoning_effort or "minimal").strip(),
                    )
        if cached_window:
            ready_scoped[str(window_key).strip()] = cached_window
        if cold_window:
            cold_scoped[str(window_key).strip()] = cold_window

    if resolved_provider is None or (not cold_global and not cold_scoped):
        ready_global.update(skipped_global)
        for window_key, window_results in skipped_scoped.items():
            merged_window = dict(ready_scoped.get(window_key, {}))
            merged_window.update(window_results)
            ready_scoped[window_key] = merged_window
        return {
            "global": ready_global,
            "scoped": ready_scoped,
        }

    provider_global: dict[str, dict[str, Any]] = {}
    provider_scoped: dict[str, dict[str, dict[str, Any]]] = {}
    blocked_global: dict[str, dict[str, Any]] = {}
    blocked_scoped: dict[str, dict[str, dict[str, Any]]] = {}
    use_host_aware_budget = max_bundle_payload_chars == DEFAULT_BUNDLE_PROVIDER_MAX_CHARS
    if use_host_aware_budget:
        host_max_chars, host_max_entries = _host_aware_bundle_budget(config=resolved_config)
    else:
        host_max_chars, host_max_entries = max_bundle_payload_chars, DEFAULT_BUNDLE_PROVIDER_MAX_ENTRIES
    immediate_global = cold_global
    if defer_scoped:
        deferred_scoped = cold_scoped
        immediate_scoped: dict[str, dict[str, Mapping[str, Any]]] = {}
    else:
        immediate_scoped = cold_scoped
        deferred_scoped = {}
    if deferred_scoped:
        for window_key, window_packets in deferred_scoped.items():
            if not isinstance(window_packets, Mapping):
                continue
            deferred_window: dict[str, dict[str, Any]] = {}
            for scope_id, fact_packet in window_packets.items():
                if not isinstance(fact_packet, Mapping):
                    continue
                deferred_window[str(scope_id).strip()] = _skip_brief(
                    fingerprint="",
                    generated_utc=generated_utc,
                    decision_reason="deferred_to_background",
                )
            if deferred_window:
                skipped_scoped[str(window_key).strip()] = deferred_window
    pack_entry_limit = 1 if defer_scoped else host_max_entries
    bundle_packs = _bundle_provider_subset_by_window(
        repo_root=repo_root,
        global_packets_by_window=immediate_global,
        scoped_packets_by_window=immediate_scoped,
        max_payload_chars=host_max_chars,
        max_entries=pack_entry_limit,
    )

    def _resolve_pack(pack_data: tuple[dict[str, Mapping[str, Any]], dict[str, dict[str, Mapping[str, Any]]]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, dict[str, Any]]]]:
        pack_globals, pack_scoped = pack_data
        return _resolve_bundle_pack(
            repo_root=repo_root,
            global_packets_by_window=pack_globals,
            scoped_packets_by_window=pack_scoped,
            generated_utc=generated_utc,
            runtime_packet_fingerprint=str(runtime_packet_fingerprint).strip(),
            config=resolved_config,
            provider=resolved_provider,
        )

    if defer_scoped and len(bundle_packs) > 1:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(bundle_packs), 4)) as pool:
            futures = [pool.submit(_resolve_pack, pack) for pack in bundle_packs]
            for future in concurrent.futures.as_completed(futures):
                try:
                    pack_ready_global, pack_ready_scoped = future.result()
                except Exception:
                    continue
                provider_global.update(pack_ready_global)
                for window_key, window_results in pack_ready_scoped.items():
                    merged_window = dict(provider_scoped.get(window_key, {}))
                    merged_window.update(window_results)
                    provider_scoped[window_key] = merged_window
    else:
        for pack_index, (pack_globals, pack_scoped) in enumerate(bundle_packs):
            pack_ready_global, pack_ready_scoped = _resolve_pack((pack_globals, pack_scoped))
            provider_global.update(pack_ready_global)
            for window_key, window_results in pack_ready_scoped.items():
                merged_window = dict(provider_scoped.get(window_key, {}))
                merged_window.update(window_results)
                provider_scoped[window_key] = merged_window
            if _provider_failure_should_abort_fanout(resolved_provider):
                remaining_global: dict[str, Mapping[str, Any]] = {}
                remaining_scoped: dict[str, dict[str, Mapping[str, Any]]] = {}
                for remaining_globals, remaining_scoped_window in bundle_packs[pack_index:]:
                    remaining_global.update(
                        {
                            str(wk).strip(): dict(fp)
                            for wk, fp in remaining_globals.items()
                            if str(wk).strip() and isinstance(fp, Mapping)
                        }
                    )
                    for wk, wp in remaining_scoped_window.items():
                        if not str(wk).strip() or not isinstance(wp, Mapping):
                            continue
                        mw = dict(remaining_scoped.get(str(wk).strip(), {}))
                        mw.update(
                            {
                                str(sid).strip(): dict(fp)
                                for sid, fp in wp.items()
                                if str(sid).strip() and isinstance(fp, Mapping)
                            }
                        )
                        remaining_scoped[str(wk).strip()] = mw
                blocked_global, blocked_scoped = _provider_failure_briefs_for_packets(
                    global_packets_by_window=remaining_global,
                    scoped_packets_by_window=remaining_scoped,
                    generated_utc=generated_utc,
                    provider=resolved_provider,
                )
                break

    _persist_provider_results(
        repo_root=repo_root,
        fact_packets_by_key=global_fact_packets_by_window,
        provider_results=provider_global,
    )
    _persist_scoped_provider_results(
        repo_root=repo_root,
        fact_packets_by_window=scoped_fact_packets_by_window,
        provider_results_by_window=provider_scoped,
    )

    ready_global.update(provider_global)
    ready_global.update(blocked_global)
    ready_global.update(skipped_global)
    for window_key, window_results in provider_scoped.items():
        merged_window = dict(ready_scoped.get(window_key, {}))
        merged_window.update(window_results)
        ready_scoped[window_key] = merged_window
    for window_key, window_results in blocked_scoped.items():
        merged_window = dict(ready_scoped.get(window_key, {}))
        merged_window.update(window_results)
        ready_scoped[window_key] = merged_window
    for window_key, window_results in skipped_scoped.items():
        merged_window = dict(ready_scoped.get(window_key, {}))
        merged_window.update(window_results)
        ready_scoped[window_key] = merged_window

    return {
        "global": ready_global,
        "scoped": ready_scoped,
    }


def build_scoped_briefs(
    *,
    repo_root: Path,
    fact_packets_by_scope: Mapping[str, Mapping[str, Any]],
    generated_utc: str,
    config: odylith_reasoning.ReasoningConfig | None = None,
    provider: odylith_reasoning.ReasoningProvider | None = None,
    pack_size: int = DEFAULT_SCOPED_PROVIDER_PACK_SIZE,
    max_pack_payload_chars: int = DEFAULT_SCOPED_PROVIDER_PACK_MAX_CHARS,
) -> dict[str, dict[str, Any]]:
    """Build scoped briefs with exact-cache reuse first, then bounded provider packs."""

    repo_root = Path(repo_root).resolve()
    if not fact_packets_by_scope:
        return {}

    resolved_config = config or odylith_reasoning.reasoning_config_from_env(repo_root=repo_root)
    resolved_provider = provider or odylith_reasoning.provider_from_config(
        resolved_config,
        repo_root=repo_root,
        require_auto_mode=False,
        allow_implicit_local_provider=True,
    )

    results: dict[str, dict[str, Any]] = {}
    cold_packets: dict[str, Mapping[str, Any]] = {}
    for scope_id, fact_packet in fact_packets_by_scope.items():
        cached = narrator.build_standup_brief(
            repo_root=repo_root,
            fact_packet=fact_packet,
            generated_utc=generated_utc,
            config=resolved_config,
            provider=resolved_provider,
            allow_provider=False,
            prefer_provider=False,
        )
        if cached.get("status") == "ready" and cached.get("source") == "cache":
            results[scope_id] = cached
        else:
            cold_packets[scope_id] = fact_packet

    if not cold_packets or resolved_provider is None:
        return results

    if len(cold_packets) == 1:
        scope_id, fact_packet = next(iter(cold_packets.items()))
        provider_results = _build_single_scope_brief(
            repo_root=repo_root,
            scope_id=scope_id,
            fact_packet=fact_packet,
            generated_utc=generated_utc,
            config=resolved_config,
            provider=resolved_provider,
        )
        _persist_provider_results(
            repo_root=repo_root,
            fact_packets_by_key=fact_packets_by_scope,
            provider_results=provider_results,
        )
        results.update(provider_results)
        return results

    provider_results: dict[str, dict[str, Any]] = {}
    for pack in _adaptive_chunked_scope_packets(
        cold_packets,
        pack_size=pack_size,
        max_payload_chars=max_pack_payload_chars,
    ):
        pack_mapping = {scope_id: fact_packet for scope_id, fact_packet in pack}
        provider_results.update(
            _resolve_scope_pack(
                repo_root=repo_root,
                pack_mapping=pack_mapping,
                generated_utc=generated_utc,
                config=resolved_config,
                provider=resolved_provider,
            )
        )

    _persist_provider_results(
        repo_root=repo_root,
        fact_packets_by_key=fact_packets_by_scope,
        provider_results=provider_results,
    )
    results.update(provider_results)
    return results


__all__ = [
    "DEFAULT_BUNDLE_PROVIDER_MAX_CHARS",
    "DEFAULT_BUNDLE_PROVIDER_MAX_ENTRIES",
    "DEFAULT_SCOPED_PROVIDER_PACK_SIZE",
    "DEFAULT_SCOPED_PROVIDER_PACK_MAX_CHARS",
    "build_brief_bundle",
    "build_window_briefs",
    "build_scoped_briefs",
]
