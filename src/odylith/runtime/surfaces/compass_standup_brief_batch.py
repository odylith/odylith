"""Bounded batch narrator for scoped Compass standup briefs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.surfaces import compass_standup_brief_narrator as narrator


DEFAULT_SCOPED_PROVIDER_PACK_SIZE = 12
DEFAULT_SCOPED_PROVIDER_PACK_MAX_CHARS = 18000


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


def _batch_provider_system_prompt() -> str:
    return (
        narrator._provider_system_prompt()  # noqa: SLF001
        + " You are writing multiple scoped briefs in one batch. "
        "Return one independent four-section brief per scope_id. "
        "Never mix facts, fact ids, or workstream meaning across scopes. "
        "If one scope has thin evidence, keep that scope plainer rather than borrowing tone or detail from another scope."
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


def _persist_provider_results(
    *,
    repo_root: Path,
    fact_packets_by_scope: Mapping[str, Mapping[str, Any]],
    provider_results: Mapping[str, Mapping[str, Any]],
) -> None:
    if not provider_results:
        return
    cache_payload = narrator._load_cache(repo_root=repo_root)  # noqa: SLF001
    entries = cache_payload.get("entries")
    cache_entries = dict(entries) if isinstance(entries, Mapping) else {}
    for scope_id, brief in provider_results.items():
        fact_packet = fact_packets_by_scope.get(scope_id)
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
        }
    narrator._write_cache(  # noqa: SLF001
        repo_root=repo_root,
        payload={
            "version": narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            "entries": cache_entries,
        },
    )


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
        allow_cache_recovery=True,
        allow_deterministic_fallback=False,
        allow_composed_fallback=False,
    )
    if str(brief.get("status", "")).strip().lower() != "ready":
        return {}
    return {scope_id: brief}


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

    raw_result = narrator._request_provider_with_empty_retry(  # noqa: SLF001
        provider=provider,
        request=_batch_provider_request(scope_packets=pack_mapping, config=config),
    )
    if not isinstance(raw_result, Mapping):
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
            allow_cache_recovery=False,
            allow_deterministic_fallback=False,
        )
        if cached.get("status") == "ready" and cached.get("source") == "cache":
            results[scope_id] = cached
        else:
            cold_packets[scope_id] = fact_packet

    if not cold_packets or resolved_provider is None:
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
        fact_packets_by_scope=fact_packets_by_scope,
        provider_results=provider_results,
    )
    results.update(provider_results)
    return results


__all__ = [
    "DEFAULT_SCOPED_PROVIDER_PACK_SIZE",
    "DEFAULT_SCOPED_PROVIDER_PACK_MAX_CHARS",
    "build_scoped_briefs",
]
