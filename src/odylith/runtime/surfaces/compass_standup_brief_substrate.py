"""Deterministic narration substrate for Compass standup briefs.

The provider should not read the whole fact packet. This module reduces a
fact packet into a compact, deterministic narrated input:

- bounded winner facts per section;
- stable fact keys that survive packet-local id renumbering;
- stable substrate fingerprinting for exact cache reuse;
- deterministic delta summaries versus the last accepted substrate; and
- a local gate that decides whether a fresh provider pass is worth calling.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence


SUBSTRATE_VERSION = "v2"
GLOBAL_TOTAL_FACT_CAP = 8
SCOPED_TOTAL_FACT_CAP = 4
GLOBAL_SECTION_FACT_CAPS = {
    "completed": 2,
    "current_execution": 3,
    "next_planned": 2,
    "risks_to_watch": 1,
}
SCOPED_SECTION_FACT_CAPS = {
    "completed": 1,
    "current_execution": 1,
    "next_planned": 1,
    "risks_to_watch": 1,
}
_SECTION_PRIORITY = {
    "completed": 340,
    "current_execution": 420,
    "next_planned": 300,
    "risks_to_watch": 320,
}
_KIND_BOOSTS = {
    "plan_completion": 85,
    "execution_highlight": 70,
    "direction": 60,
    "forcing_function": 55,
    "risk_posture": 60,
    "traceability_risk": 58,
    "critical_bug": 68,
    "self_host_status": 48,
    "freshness": 24,
}
_SOURCE_BOOSTS = {
    "transaction_or_event": 35,
    "execution_highlight": 32,
    "traceability_risk": 28,
    "bug": 30,
    "freshness": 16,
    "workstream_metadata": 14,
    "plan": 18,
    "topology": 10,
}
_KIND_PENALTIES = {
    "portfolio_posture": 36,
    "window_coverage": 52,
    "timeline": 18,
    "self_host_status": 16,
    "checklist": 20,
    "window_summary": 18,
    "fallback_next": 10,
}
_SOURCE_PENALTIES = {
    "portfolio": 28,
    "self_host": 22,
    "workstream_metadata": 10,
}
_SUMMARY_KEYS = (
    "window_hours",
    "active_workstreams",
    "touched_workstreams",
    "recent_completed_plans",
    "critical_risks",
)
_STORYLINE_KEYS = (
    "flagship_lane",
    "direction",
    "proof",
    "forcing_function",
    "watch_item",
)
_SELF_HOST_KEYS = (
    "repo_role",
    "posture",
    "runtime_source",
    "pinned_version",
    "active_version",
    "launcher_present",
    "release_eligible",
)
_STORYLINE_CHAR_LIMITS = {
    "flagship_lane": 120,
    "direction": 180,
    "proof": 180,
    "forcing_function": 180,
    "watch_item": 180,
}
_META_TEXT_PENALTIES = (
    ("verified plan closeouts landed across the window", 44),
    ("most concrete portfolio movement", 34),
    ("primary execution signal", 28),
    ("plan posture", 24),
    ("timeline signal", 18),
    ("no verified milestone closeout landed", 18),
    ("immediate forcing function is", 16),
    ("closure discipline", 18),
    ("product claim", 38),
    ("tracked corpus", 34),
    ("live self-host posture check passed", 36),
    ("planning and implementation are running in parallel across active lanes", 34),
    ("most of the movement this window sat in", 60),
    ("work moved across", 42),
    ("governance gap still needs cleanup", 26),
    ("missing/invalid `workstream_type`", 26),
    ("flagship lane", 16),
    ("repo pin", 20),
)


def _sequence(value: Any) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return list(value)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _truncate_text(value: Any, *, max_chars: int) -> str:
    text = _normalize_text(value)
    if len(text) <= max(0, int(max_chars)):
        return text
    clipped = text[: max(0, int(max_chars) - 1)].rsplit(" ", 1)[0].strip()
    return (clipped or text[: max(0, int(max_chars) - 1)].strip()) + "…"


def _healthy_self_host(self_host: Mapping[str, Any]) -> bool:
    posture = str(self_host.get("posture", "")).strip().lower()
    runtime_source = str(self_host.get("runtime_source", "")).strip().lower()
    pinned_version = str(self_host.get("pinned_version", "")).strip()
    active_version = str(self_host.get("active_version", "")).strip()
    launcher_present = self_host.get("launcher_present")
    release_eligible = self_host.get("release_eligible")
    return (
        posture == "pinned_release"
        and runtime_source == "pinned_runtime"
        and bool(launcher_present)
        and (release_eligible in ("", None, True))
        and (not pinned_version or not active_version or pinned_version == active_version)
    )


def _storyline_view(storyline: Mapping[str, Any]) -> dict[str, str]:
    values = {
        "flagship_lane": storyline.get("flagship_lane"),
        "direction": storyline.get("direction"),
        "proof": storyline.get("proof"),
        "forcing_function": storyline.get("forcing_function"),
        "watch_item": storyline.get("watch_item"),
    }
    payload: dict[str, str] = {}
    for key in _STORYLINE_KEYS:
        text = _truncate_text(values.get(key), max_chars=_STORYLINE_CHAR_LIMITS.get(key, 180))
        if text:
            payload[key] = text
    return payload


def _meta_text_penalty(text: str) -> int:
    lowered = text.lower()
    return sum(penalty for token, penalty in _META_TEXT_PENALTIES if token in lowered)


def _scope_mode(fact_packet: Mapping[str, Any]) -> str:
    return str(_mapping(fact_packet.get("scope")).get("mode", "")).strip().lower() or "global"


def _fact_key(*, fact: Mapping[str, Any], section_key: str) -> str:
    kind = str(fact.get("kind", "")).strip().lower()
    source = str(fact.get("source", "")).strip().lower()
    text = _normalize_text(fact.get("text"))
    if kind == "freshness" or source == "freshness":
        text = "freshness"
    canonical = json.dumps(
        {
            "section_key": section_key,
            "kind": kind,
            "source": source,
            "text": text,
            "workstreams": sorted(
                str(token).strip()
                for token in _sequence(fact.get("workstreams"))
                if str(token).strip()
            ),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _winner_key_set(substrate: Mapping[str, Any]) -> set[str]:
    sections = _sequence(substrate.get("sections"))
    keys: set[str] = set()
    for section in sections:
        if not isinstance(section, Mapping):
            continue
        for fact in _sequence(section.get("facts")):
            if not isinstance(fact, Mapping):
                continue
            token = str(fact.get("fact_key", "")).strip()
            if token:
                keys.add(token)
    return keys


def _previous_winner_keys(previous_substrate: Mapping[str, Any] | None) -> set[str]:
    return _winner_key_set(previous_substrate or {})


def _summary_view(summary_mapping: Mapping[str, Any]) -> dict[str, Any]:
    freshness = _mapping(summary_mapping.get("freshness"))
    storyline = _mapping(summary_mapping.get("storyline"))
    self_host = _mapping(summary_mapping.get("self_host"))
    payload: dict[str, Any] = {
        "freshness_bucket": str(freshness.get("bucket", "")).strip().lower() or "unknown",
        "storyline": _storyline_view(storyline),
    }
    for key in _SUMMARY_KEYS:
        value = summary_mapping.get(key)
        if isinstance(value, int):
            payload[key] = value
    self_host_view = {
        key: self_host.get(key)
        for key in _SELF_HOST_KEYS
        if self_host.get(key) not in ("", None, [])
    }
    if self_host_view and not _healthy_self_host(self_host_view):
        payload["self_host"] = self_host_view
    return payload


def _section_caps_for_scope(scope_mode: str) -> tuple[int, Mapping[str, int]]:
    normalized_scope = str(scope_mode or "").strip().lower()
    if normalized_scope == "scoped":
        return SCOPED_TOTAL_FACT_CAP, SCOPED_SECTION_FACT_CAPS
    return GLOBAL_TOTAL_FACT_CAP, GLOBAL_SECTION_FACT_CAPS


def _fact_rank(
    *,
    fact: Mapping[str, Any],
    section_key: str,
    previous_winner_keys: set[str],
    freshness_bucket: str,
) -> tuple[int, int, str]:
    text = _normalize_text(fact.get("text"))
    base_priority = int(fact.get("priority", 0) or 0) * 100
    score = base_priority + int(_SECTION_PRIORITY.get(section_key, 0))
    kind = str(fact.get("kind", "")).strip().lower()
    source = str(fact.get("source", "")).strip().lower()
    score += int(_KIND_BOOSTS.get(kind, 0))
    score += int(_SOURCE_BOOSTS.get(source, 0))
    score -= int(_KIND_PENALTIES.get(kind, 0))
    score -= int(_SOURCE_PENALTIES.get(source, 0))
    score -= _meta_text_penalty(text)
    if len([token for token in _sequence(fact.get("workstreams")) if str(token).strip()]) > 1:
        score += 15
    if section_key == "current_execution" and freshness_bucket in {"aging", "stale"} and kind == "freshness":
        score += 40
    return score, int(fact.get("priority", 0) or 0), text.lower()


def _selected_section_facts(
    *,
    section_key: str,
    raw_facts: Sequence[Mapping[str, Any]],
    cap: int,
    previous_winner_keys: set[str],
    freshness_bucket: str,
) -> list[dict[str, Any]]:
    winners: list[dict[str, Any]] = []
    ranked = sorted(
        (
            dict(item)
            for item in raw_facts
            if isinstance(item, Mapping) and _normalize_text(item.get("text"))
        ),
        key=lambda item: _fact_rank(
            fact=item,
            section_key=section_key,
            previous_winner_keys=previous_winner_keys,
            freshness_bucket=freshness_bucket,
        ),
        reverse=True,
    )
    for fact in ranked[: max(0, int(cap))]:
        winners.append(
            {
                "fact_id": str(fact.get("id", "")).strip(),
                "fact_key": _fact_key(fact=fact, section_key=section_key),
                "text": _normalize_text(fact.get("text")),
                "kind": str(fact.get("kind", "")).strip().lower(),
                "source": str(fact.get("source", "")).strip().lower(),
                "priority": int(fact.get("priority", 0) or 0),
                "workstreams": [
                    str(token).strip()
                    for token in _sequence(fact.get("workstreams"))
                    if str(token).strip()
                ],
            }
        )
    return winners


def _brief_snapshot(previous_brief: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(previous_brief, Mapping):
        return {}
    if str(previous_brief.get("status", "")).strip().lower() != "ready":
        return {}
    sections = []
    for row in _sequence(previous_brief.get("sections")):
        if not isinstance(row, Mapping):
            continue
        bullets = []
        for bullet in _sequence(row.get("bullets")):
            if not isinstance(bullet, Mapping):
                continue
            text = _normalize_text(bullet.get("text"))
            if not text:
                continue
            bullets.append(
                {
                    "text": text,
                    "fact_ids": [
                        str(token).strip()
                        for token in _sequence(bullet.get("fact_ids"))
                        if str(token).strip()
                    ],
                }
            )
        sections.append(
            {
                "key": str(row.get("key", "")).strip(),
                "label": _normalize_text(row.get("label")),
                "bullets": bullets,
            }
        )
    return {
        "fingerprint": str(previous_brief.get("fingerprint", "")).strip(),
        "generated_utc": str(previous_brief.get("generated_utc", "")).strip(),
        "sections": sections,
    }


def build_narration_substrate(
    *,
    fact_packet: Mapping[str, Any],
    previous_substrate: Mapping[str, Any] | None = None,
    previous_brief: Mapping[str, Any] | None = None,
    schema_version: str,
) -> dict[str, Any]:
    scope = _mapping(fact_packet.get("scope"))
    summary = _mapping(fact_packet.get("summary"))
    scope_mode = _scope_mode(fact_packet)
    total_fact_cap, section_caps = _section_caps_for_scope(scope_mode)
    freshness_bucket = str(_mapping(summary.get("freshness")).get("bucket", "")).strip().lower() or "unknown"
    previous_winner_keys = _previous_winner_keys(previous_substrate)
    sections_payload: list[dict[str, Any]] = []
    total_selected = 0
    for section in _sequence(fact_packet.get("sections")):
        if not isinstance(section, Mapping):
            continue
        section_key = str(section.get("key", "")).strip()
        if not section_key:
            continue
        section_cap = int(section_caps.get(section_key, 1) or 1)
        selected = _selected_section_facts(
            section_key=section_key,
            raw_facts=[dict(item) for item in _sequence(section.get("facts")) if isinstance(item, Mapping)],
            cap=section_cap,
            previous_winner_keys=previous_winner_keys,
            freshness_bucket=freshness_bucket,
        )
        total_selected += len(selected)
        sections_payload.append(
            {
                "key": section_key,
                "label": _normalize_text(section.get("label")) or section_key,
                "fact_cap": section_cap,
                "facts": selected,
            }
        )
    substrate = {
        "version": SUBSTRATE_VERSION,
        "schema_version": str(schema_version).strip(),
        "window": str(fact_packet.get("window", "")).strip(),
        "scope": {
            "mode": scope_mode,
            "label": _normalize_text(scope.get("label")) or "Global",
            "idea_id": str(scope.get("idea_id", "")).strip(),
            "status": str(scope.get("status", "")).strip(),
        },
        "summary": _summary_view(summary),
        "budgets": {
            "total_fact_cap": int(total_fact_cap),
            "section_fact_caps": {str(key): int(value) for key, value in section_caps.items()},
            "selected_fact_count": int(total_selected),
        },
        "sections": sections_payload,
        "previous_accepted": _brief_snapshot(previous_brief),
    }
    substrate["fingerprint"] = narration_substrate_fingerprint(substrate=substrate)
    return substrate


def _canonical_substrate_for_fingerprint(substrate: Mapping[str, Any]) -> dict[str, Any]:
    summary = dict(_mapping(substrate.get("summary")))
    summary.pop("freshness_bucket", None)
    return {
        "version": str(substrate.get("version", "")).strip(),
        "schema_version": str(substrate.get("schema_version", "")).strip(),
        "window": str(substrate.get("window", "")).strip(),
        "scope": {
            "mode": str(_mapping(substrate.get("scope")).get("mode", "")).strip(),
            "idea_id": str(_mapping(substrate.get("scope")).get("idea_id", "")).strip(),
            "status": str(_mapping(substrate.get("scope")).get("status", "")).strip(),
        },
        "summary": summary,
        "budgets": {
            "total_fact_cap": int(_mapping(substrate.get("budgets")).get("total_fact_cap", 0) or 0),
            "section_fact_caps": {
                str(key): int(value or 0)
                for key, value in _mapping(_mapping(substrate.get("budgets")).get("section_fact_caps")).items()
            },
        },
        "sections": [
            {
                "key": str(_mapping(section).get("key", "")).strip(),
                "facts": [
                    {
                        "fact_key": str(_mapping(fact).get("fact_key", "")).strip(),
                        "text": (
                            "freshness"
                            if str(_mapping(fact).get("kind", "")).strip().lower() == "freshness"
                            or str(_mapping(fact).get("source", "")).strip().lower() == "freshness"
                            else _normalize_text(_mapping(fact).get("text"))
                        ),
                        "kind": str(_mapping(fact).get("kind", "")).strip().lower(),
                        "source": str(_mapping(fact).get("source", "")).strip().lower(),
                        "workstreams": sorted(
                            str(token).strip()
                            for token in _sequence(_mapping(fact).get("workstreams"))
                            if str(token).strip()
                        ),
                    }
                    for fact in _sequence(_mapping(section).get("facts"))
                    if str(_mapping(fact).get("fact_key", "")).strip()
                ],
            }
            for section in _sequence(substrate.get("sections"))
            if str(_mapping(section).get("key", "")).strip()
        ],
    }


def narration_substrate_fingerprint(*, substrate: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _canonical_substrate_for_fingerprint(substrate),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def provider_substrate_view(*, substrate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "version": str(substrate.get("version", "")).strip() or SUBSTRATE_VERSION,
        "substrate_fingerprint": str(substrate.get("fingerprint", "")).strip(),
        "window": str(substrate.get("window", "")).strip(),
        "scope": dict(_mapping(substrate.get("scope"))),
        "summary": dict(_mapping(substrate.get("summary"))),
        "budgets": dict(_mapping(substrate.get("budgets"))),
        "sections": [
            {
                "key": str(_mapping(section).get("key", "")).strip(),
                "label": _normalize_text(_mapping(section).get("label")),
                "fact_cap": int(_mapping(section).get("fact_cap", 0) or 0),
                "facts": [
                    {
                        "id": str(_mapping(fact).get("fact_id", "")).strip(),
                        "text": _normalize_text(_mapping(fact).get("text")),
                        "kind": str(_mapping(fact).get("kind", "")).strip().lower(),
                    }
                    for fact in _sequence(_mapping(section).get("facts"))
                    if _normalize_text(_mapping(fact).get("text"))
                ],
            }
            for section in _sequence(substrate.get("sections"))
            if str(_mapping(section).get("key", "")).strip()
        ],
    }


def diff_narration_substrates(
    *,
    current: Mapping[str, Any],
    previous: Mapping[str, Any] | None,
) -> dict[str, Any]:
    current_sections = {
        str(_mapping(section).get("key", "")).strip(): [
            dict(_mapping(fact))
            for fact in _sequence(_mapping(section).get("facts"))
            if str(_mapping(fact).get("fact_key", "")).strip()
        ]
        for section in _sequence(current.get("sections"))
        if str(_mapping(section).get("key", "")).strip()
    }
    previous_sections = {
        str(_mapping(section).get("key", "")).strip(): [
            dict(_mapping(fact))
            for fact in _sequence(_mapping(section).get("facts"))
            if str(_mapping(fact).get("fact_key", "")).strip()
        ]
        for section in _sequence(_mapping(previous).get("sections"))
        if str(_mapping(section).get("key", "")).strip()
    }
    current_lookup = {
        str(fact.get("fact_key", "")).strip(): fact
        for facts in current_sections.values()
        for fact in facts
        if str(fact.get("fact_key", "")).strip()
    }
    previous_lookup = {
        str(fact.get("fact_key", "")).strip(): fact
        for facts in previous_sections.values()
        for fact in facts
        if str(fact.get("fact_key", "")).strip()
    }
    current_keys = set(current_lookup)
    previous_keys = set(previous_lookup)
    changed_sections = sorted(
        {
            section_key
            for section_key, facts in current_sections.items()
            if [fact.get("fact_key", "") for fact in facts]
            != [fact.get("fact_key", "") for fact in previous_sections.get(section_key, [])]
        }
        | {
            section_key
            for section_key in previous_sections
            if section_key not in current_sections
        }
    )
    current_summary = _mapping(current.get("summary"))
    previous_summary = _mapping(_mapping(previous).get("summary"))
    changed_storyline = sorted(
        key
        for key in _STORYLINE_KEYS
        if _normalize_text(_mapping(current_summary.get("storyline")).get(key))
        != _normalize_text(_mapping(previous_summary.get("storyline")).get(key))
    )
    freshness_changed = str(current_summary.get("freshness_bucket", "")).strip().lower() != str(
        previous_summary.get("freshness_bucket", "")
    ).strip().lower()
    return {
        "current_fingerprint": str(current.get("fingerprint", "")).strip(),
        "previous_fingerprint": str(_mapping(previous).get("fingerprint", "")).strip(),
        "changed_fact_keys": sorted(current_keys - previous_keys),
        "dropped_fact_keys": sorted(previous_keys - current_keys),
        "unchanged_fact_keys": sorted(current_keys & previous_keys),
        "changed_sections": changed_sections,
        "storyline_changed_keys": changed_storyline,
        "freshness_changed": bool(freshness_changed),
    }


def worth_calling_provider(
    *,
    current: Mapping[str, Any],
    previous: Mapping[str, Any] | None,
) -> tuple[bool, str, dict[str, Any]]:
    current_fingerprint = str(current.get("fingerprint", "")).strip()
    previous_fingerprint = str(_mapping(previous).get("fingerprint", "")).strip()
    if not previous or not previous_fingerprint:
        delta = diff_narration_substrates(current=current, previous=previous)
        return True, "first_narration", delta
    if current_fingerprint and previous_fingerprint and current_fingerprint == previous_fingerprint:
        delta = diff_narration_substrates(current=current, previous=previous)
        return False, "exact_substrate_match", delta
    delta = diff_narration_substrates(current=current, previous=previous)
    if delta["changed_fact_keys"] or delta["dropped_fact_keys"]:
        return True, "winner_facts_changed", delta
    if delta["storyline_changed_keys"]:
        return True, "storyline_changed", delta
    if delta["changed_sections"]:
        return True, "section_winners_changed", delta
    if delta["freshness_changed"]:
        return False, "freshness_only", delta
    return False, "no_winner_change", delta


__all__ = [
    "GLOBAL_SECTION_FACT_CAPS",
    "GLOBAL_TOTAL_FACT_CAP",
    "SCOPED_SECTION_FACT_CAPS",
    "SCOPED_TOTAL_FACT_CAP",
    "SUBSTRATE_VERSION",
    "build_narration_substrate",
    "diff_narration_substrates",
    "narration_substrate_fingerprint",
    "provider_substrate_view",
    "worth_calling_provider",
]
