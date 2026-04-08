"""Compass standup brief narrator and cache.

Compass runtime remains authoritative for fact selection, evidence ranking, and
fingerprinting. This module owns the bounded narration layer:

- reuse the shared Odylith reasoning provider configuration and adapters;
- request a fixed five-section standup brief with schema-constrained output;
- validate the reply against the deterministic fact packet and UI contract;
- cache validated results by exact fact-packet fingerprint; and
- fall back to a deterministic structured brief when live AI narration is not
  available.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.surfaces import compass_standup_brief_deterministic


STANDUP_BRIEF_SCHEMA_VERSION = "v13"
STANDUP_BRIEF_CACHE_PATH = ".odylith/compass/standup-brief-cache.v13.json"
STANDUP_BRIEF_SECTIONS: tuple[tuple[str, str], ...] = (
    ("completed", "Completed in this window"),
    ("current_execution", "Current execution"),
    ("next_planned", "Next planned"),
    ("why_this_matters", "Why this matters"),
    ("risks_to_watch", "Risks to watch"),
)
_SECTION_LABELS = {key: label for key, label in STANDUP_BRIEF_SECTIONS}
_VALID_VOICES = {"executive", "operator"}
_REPO_PATH_RE = re.compile(
    r"\b(?:agents-guidelines|alerts|bin|configs|contracts|docker|docs|infra|mk|mocks|monitoring|odylith|app|policies|scripts|services|skills|tests)/[A-Za-z0-9._/-]+\b"
)
_COUNTS_ONLY_LEAD_RE = re.compile(
    r"^\s*(?:\d+\s*(?:/|x)\s*\d+\b|\d+\s+(?:commits?|changes?|files?|events?|transactions?|workstreams?|plans?|bugs?|risks?)\b|(?:commits?|changes?|files?|events?|transactions?|workstreams?|plans?|bugs?|risks?)\s*:\s*\d+\b)",
    re.IGNORECASE,
)
_DISCOURAGED_PHRASE_RE = re.compile(
    r"\b(?:same window|current portfolio direction around)\b",
    re.IGNORECASE,
)
_FIRST_PERSON_LEAD_RE = re.compile(r"^\s*(?:i|i'm|i’ve|i've|i’ll|i'll)\b", re.IGNORECASE)
_GENERIC_STANDUP_LEAD_RE = re.compile(
    r"^\s*(?:this matters\b|the proof is concrete now\b|the proof lane is still\b)",
    re.IGNORECASE,
)
_OVERUSED_STOCK_LEAD_RE = re.compile(
    r"^\s*(?:over|across)\s+the\s+last\s+48\s+hours,\s+"
    r"(?:the\s+)?(?:big\s+cleanup\s+work\s+finally\s+landed|boring\s+but\s+important\s+move\s+was|"
    r"move\s+that\s+actually\s+changed\s+the\s+room\s+was|real\s+center\s+of\s+gravity\s+is|"
    r"core\s+proof(?:\s+lane)?\s+is|immediate\s+forcing\s+function\s+is|real\s+risk\s+is\s+not|"
    r"clearest\s+execution\s+signal(?:\s+right\s+now)?\s+is|proof\s+lane\s+finally\s+has\s+a\s+firmer\s+anchor)\b|"
    r"^\s*(?:the\s+)?(?:big\s+cleanup\s+work\s+finally\s+landed|boring\s+but\s+important\s+move\s+was|"
    r"move\s+that\s+actually\s+changed\s+the\s+room\s+was|real\s+center\s+of\s+gravity\s+is|"
    r"core\s+proof(?:\s+lane)?\s+is|immediate\s+forcing\s+function\s+is|real\s+risk\s+is\s+not|"
    r"clearest\s+execution\s+signal(?:\s+right\s+now)?\s+is|proof\s+lane\s+finally\s+has\s+a\s+firmer\s+anchor)\b",
    re.IGNORECASE,
)
_ATTENTION_PRIORITY_LEAD_RE = re.compile(
    r"^\s*(?:attention\s+(?:stays|is)\s+(?:on|here)\b|"
    r"(?:`?B-\d+`?|[A-Za-z][A-Za-z0-9`'’(),/\- ]{0,90})\s+"
    r"(?:is\s+(?:still\s+)?getting\s+(?:the\s+)?attention|stays\s+hot|stays\s+at\s+the\s+top|"
    r"is\s+getting\s+active\s+implementation\s+time|where\s+attention\s+(?:belongs|stays|lands)))\b",
    re.IGNORECASE,
)
_GENERIC_PRIORITY_WRAPPER_RE = re.compile(
    r"^\s*(?:this\s+work\s+is\s+(?:still\s+)?(?:live|active)\s+because|"
    r"(?:`?B-\d+`?|[A-Za-z][A-Za-z0-9`'’(),/\- ]{0,90})\s+is\s+(?:still\s+)?"
    r"the\s+(?:live\s+problem|live\s+issue|active\s+lane|live\s+lane|implementation\s+lane)\s+because)\b",
    re.IGNORECASE,
)
_FACT_ID_RE = re.compile(r"F-\d{3}")
_PAREN_FACT_ID_RE = re.compile(r"(?:\(\s*F-\d{3}\s*\)\s*)+")
_PAREN_FACT_ID_LIST_RE = re.compile(r"\(\s*F-\d{3}(?:\s*[,/&+|]\s*F-\d{3})+\s*\)")
_STANDALONE_FACT_ID_RE = re.compile(r"(?<![A-Za-z0-9])F-\d{3}(?![A-Za-z0-9])")
_VOLATILE_FRESHNESS_TEXT_RE = re.compile(r"^Freshness signal is (?:aging|stale):", re.IGNORECASE)
_MAX_BULLET_WORDS = 34
_EMPTY_PROVIDER_MAX_ATTEMPTS = 2
_COMPASS_PROVIDER_REASONING_EFFORT = "medium"
_COMPASS_PROVIDER_TIMEOUT_SECONDS = 30.0
_PROVIDER_FACT_LIMITS_BY_SECTION = {
    "completed": 3,
    "current_execution": 4,
    "next_planned": 2,
    "why_this_matters": 2,
    "risks_to_watch": 3,
}
_CACHE_TTL_SECONDS_BY_FRESHNESS = {
    "live": 15 * 60,
    "recent": 45 * 60,
    "aging": 2 * 60 * 60,
    "stale": 4 * 60 * 60,
    "unknown": 60 * 60,
}

def standup_brief_cache_path(*, repo_root: Path) -> Path:
    """Return the local-only cache path for validated Compass AI briefs."""

    return (Path(repo_root).resolve() / STANDUP_BRIEF_CACHE_PATH).resolve()


def standup_brief_fingerprint(*, fact_packet: Mapping[str, Any]) -> str:
    """Return a stable fingerprint for the exact deterministic fact packet."""

    freshness_bucket = ""
    summary = fact_packet.get("summary")
    if isinstance(summary, Mapping):
        freshness = summary.get("freshness")
        if isinstance(freshness, Mapping):
            freshness_bucket = str(freshness.get("bucket", "")).strip().lower()

    canonical = json.dumps(
        {
            "schema_version": STANDUP_BRIEF_SCHEMA_VERSION,
            "fact_packet": _canonicalize_fact_packet_for_fingerprint(
                fact_packet,
                freshness_bucket=freshness_bucket,
            ),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _canonicalize_fact_packet_for_fingerprint(
    value: Any,
    *,
    freshness_bucket: str,
    field_name: str = "",
) -> Any:
    if isinstance(value, Mapping):
        if str(field_name).strip() == "freshness":
            bucket = str(value.get("bucket", "")).strip().lower()
            return {"bucket": bucket or freshness_bucket or "unknown"}
        normalized = {
            str(key): _canonicalize_fact_packet_for_fingerprint(
                item,
                freshness_bucket=freshness_bucket,
                field_name=str(key),
            )
            for key, item in value.items()
        }
        kind = str(normalized.get("kind", "")).strip().lower()
        source = str(normalized.get("source", "")).strip().lower()
        text = str(normalized.get("text", "")).strip()
        if kind == "freshness" or source == "freshness":
            normalized["text"] = f"freshness:{freshness_bucket or 'unknown'}"
        elif source == "risk_summary" and _VOLATILE_FRESHNESS_TEXT_RE.match(text):
            normalized["text"] = f"freshness-risk:{freshness_bucket or 'unknown'}"
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [
            _canonicalize_fact_packet_for_fingerprint(
                item,
                freshness_bucket=freshness_bucket,
                field_name=field_name,
            )
            for item in value
        ]
    return value


def _parse_iso_datetime(raw_value: str) -> dt.datetime | None:
    token = str(raw_value or "").strip()
    if not token:
        return None
    if token.endswith("Z"):
        token = f"{token[:-1]}+00:00"
    try:
        parsed = dt.datetime.fromisoformat(token)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _fact_packet_freshness_bucket(*, fact_packet: Mapping[str, Any]) -> str:
    summary = fact_packet.get("summary")
    if not isinstance(summary, Mapping):
        return "unknown"
    freshness = summary.get("freshness")
    if not isinstance(freshness, Mapping):
        return "unknown"
    bucket = str(freshness.get("bucket", "")).strip().lower()
    if bucket in _CACHE_TTL_SECONDS_BY_FRESHNESS:
        return bucket
    return "unknown"


def _cache_ttl_seconds(*, fact_packet: Mapping[str, Any]) -> int:
    return _CACHE_TTL_SECONDS_BY_FRESHNESS.get(
        _fact_packet_freshness_bucket(fact_packet=fact_packet),
        _CACHE_TTL_SECONDS_BY_FRESHNESS["unknown"],
    )


def _cache_entry_is_reusable(
    *,
    cached_entry: Mapping[str, Any],
    fact_packet: Mapping[str, Any],
    now_utc: dt.datetime,
) -> bool:
    generated_ts = _parse_iso_datetime(str(cached_entry.get("generated_utc", "")).strip())
    if generated_ts is None:
        return False
    age_seconds = (now_utc - generated_ts).total_seconds()
    if age_seconds < 0:
        return False
    return age_seconds <= float(_cache_ttl_seconds(fact_packet=fact_packet))


def _cache_entry_age_seconds(
    *,
    cached_entry: Mapping[str, Any],
    now_utc: dt.datetime,
) -> float | None:
    generated_ts = _parse_iso_datetime(str(cached_entry.get("generated_utc", "")).strip())
    if generated_ts is None:
        return None
    age_seconds = (now_utc - generated_ts).total_seconds()
    if age_seconds < 0:
        return None
    return age_seconds


def _cache_context(*, fact_packet: Mapping[str, Any]) -> dict[str, str]:
    scope = fact_packet.get("scope")
    scope_mapping = scope if isinstance(scope, Mapping) else {}
    scope_mode = str(scope_mapping.get("mode", "")).strip().lower() or "global"
    scope_id = str(scope_mapping.get("idea_id", "")).strip() if scope_mode == "scoped" else ""
    return {
        "window": str(fact_packet.get("window", "")).strip(),
        "scope_mode": scope_mode,
        "scope_id": scope_id,
    }


def _cache_entry_matches_context(
    *,
    cached_entry: Mapping[str, Any],
    fact_packet: Mapping[str, Any],
) -> bool:
    cached_context = cached_entry.get("context")
    if not isinstance(cached_context, Mapping):
        return False
    target_context = _cache_context(fact_packet=fact_packet)
    if str(cached_context.get("window", "")).strip() != target_context["window"]:
        return False
    if str(cached_context.get("scope_mode", "")).strip().lower() != target_context["scope_mode"]:
        return False
    if target_context["scope_mode"] == "scoped":
        return str(cached_context.get("scope_id", "")).strip() == target_context["scope_id"]
    return True


def _provider_system_prompt() -> str:
    return (
        "You are Compass, the executive standup narrator. "
        "Write a concise five-section standup brief for mixed executive/product and operator readers. "
        "Write like a strong maintainer speaking off notes: human, plain, specific, and causal rather than branded dashboard prose. "
        "Keep the voice consistent across 24h and 48h windows; a 48h brief is the same live standup voice as 24h, not a retrospective or strategy memo. "
        "Write with stance: decide what matters, what is just bookkeeping, and why the room should care. "
        "Do not write in first-person singular. "
        "Do not invent a house style or signature lead-in. Avoid stock scaffolding and repeated openings such as "
        "'The real center of gravity is', 'The core proof lane', 'The immediate forcing function is', "
        "'The boring but important move was', 'X is getting the attention because', 'attention stays on', "
        "'stays hot', 'This work is active because', or similar canned phrases. "
        "Vary sentence openings naturally across sections, windows, and workstreams. "
        "Prefer ordinary speech: say what changed, what is getting attention now, why it matters, and what could still go wrong. "
        "Use only the supplied fact packet and cited fact ids. "
        "Treat any live self-host or install posture facts in the packet as authoritative over older release-history narrative when they disagree. "
        "Do not include literal fact ids in bullet text; cite them only in the fact_ids field. "
        "Keep the section order and labels exactly as provided. "
        "Compress hard: each bullet should carry movement, consequence, or steering context, not generic posture. "
        "Make the why explicit: connect the user or product need to the architecture or operator consequence instead of implying it. "
        "Prefer concrete nouns and verbs, avoid repeating the same claim across sections, and keep bullets crisp enough to scan in one breath. "
        "Do not invent facts, do not mention raw repository paths, and do not lead bullets with raw counts-only telemetry. "
        "Bullets should read as natural steering narrative, not checklist fragments or fact-list rewrites."
    )


def _provider_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["sections"],
        "additionalProperties": False,
        "properties": {
            "sections": {
                "type": "array",
                "minItems": len(STANDUP_BRIEF_SECTIONS),
                "maxItems": len(STANDUP_BRIEF_SECTIONS),
                "items": {
                    "type": "object",
                    "required": ["key", "label", "bullets"],
                    "additionalProperties": False,
                    "properties": {
                        "key": {
                            "type": "string",
                            "enum": [key for key, _label in STANDUP_BRIEF_SECTIONS],
                        },
                        "label": {"type": "string"},
                        "bullets": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 4,
                            "items": {
                                "type": "object",
                                "required": ["voice", "text", "fact_ids"],
                                "additionalProperties": False,
                                "properties": {
                                    "voice": {
                                        "type": "string",
                                        "enum": sorted(_VALID_VOICES),
                                    },
                                    "text": {"type": "string", "minLength": 1, "maxLength": 280},
                                    "fact_ids": {
                                        "type": "array",
                                        "minItems": 1,
                                        "maxItems": 3,
                                        "items": {"type": "string", "minLength": 1},
                                    },
                                },
                            },
                        },
                    },
                },
            }
        },
    }


def _provider_fact_packet_view(*, fact_packet: Mapping[str, Any]) -> dict[str, Any]:
    scope = fact_packet.get("scope")
    scope_mapping = scope if isinstance(scope, Mapping) else {}
    summary = fact_packet.get("summary")
    summary_mapping = summary if isinstance(summary, Mapping) else {}
    storyline = summary_mapping.get("storyline")
    storyline_mapping = storyline if isinstance(storyline, Mapping) else {}
    freshness = summary_mapping.get("freshness")
    freshness_mapping = freshness if isinstance(freshness, Mapping) else {}

    summary_view: dict[str, Any] = {
        "window_hours": int(summary_mapping.get("window_hours", 0) or 0),
        "freshness_bucket": str(freshness_mapping.get("bucket", "")).strip().lower() or "unknown",
        "storyline": {
            key: str(storyline_mapping.get(key, "")).strip()
            for key in (
                "flagship_lane",
                "direction",
                "proof",
                "forcing_function",
                "use_story",
                "architecture_consequence",
                "watch_item",
            )
            if str(storyline_mapping.get(key, "")).strip()
        },
    }
    for key in ("active_workstreams", "touched_workstreams", "recent_completed_plans", "critical_risks"):
        value = summary_mapping.get(key)
        if isinstance(value, int):
            summary_view[key] = value
    self_host = summary_mapping.get("self_host")
    if isinstance(self_host, Mapping):
        self_host_view: dict[str, Any] = {}
        for key in ("repo_role", "posture", "runtime_source", "pinned_version", "active_version"):
            token = str(self_host.get(key, "")).strip()
            if token:
                self_host_view[key] = token
        if isinstance(self_host.get("launcher_present"), bool):
            self_host_view["launcher_present"] = bool(self_host.get("launcher_present"))
        release_eligible = self_host.get("release_eligible")
        if isinstance(release_eligible, bool):
            self_host_view["release_eligible"] = release_eligible
        elif release_eligible is None:
            self_host_view["release_eligible"] = None
        if self_host_view:
            summary_view["self_host"] = self_host_view

    sections_view: list[dict[str, Any]] = []
    sections = fact_packet.get("sections")
    if isinstance(sections, Sequence):
        for row in sections:
            if not isinstance(row, Mapping):
                continue
            section_key = str(row.get("key", "")).strip()
            if not section_key:
                continue
            max_facts = _PROVIDER_FACT_LIMITS_BY_SECTION.get(section_key, 2)
            facts_view: list[dict[str, str]] = []
            facts = row.get("facts")
            if isinstance(facts, Sequence):
                for item in list(facts)[:max_facts]:
                    if not isinstance(item, Mapping):
                        continue
                    fact_id = str(item.get("id", "")).strip()
                    text = str(item.get("text", "")).strip()
                    if not fact_id or not text:
                        continue
                    fact_view = {
                        "id": fact_id,
                        "text": text,
                    }
                    voice = str(item.get("voice_hint", "")).strip().lower()
                    if voice:
                        fact_view["voice"] = voice
                    kind = str(item.get("kind", "")).strip().lower()
                    if kind:
                        fact_view["kind"] = kind
                    facts_view.append(fact_view)
            sections_view.append(
                {
                    "key": section_key,
                    "label": str(row.get("label", "")).strip() or section_key,
                    "facts": facts_view,
                }
            )

    return {
        "version": str(fact_packet.get("version", "")).strip() or STANDUP_BRIEF_SCHEMA_VERSION,
        "window": str(fact_packet.get("window", "")).strip(),
        "scope": {
            "mode": str(scope_mapping.get("mode", "")).strip().lower() or "global",
            "label": str(scope_mapping.get("label", "")).strip() or "Global",
            "idea_id": str(scope_mapping.get("idea_id", "")).strip(),
            "status": str(scope_mapping.get("status", "")).strip(),
        },
        "summary": summary_view,
        "sections": sections_view,
    }


def _provider_request_payload(*, fact_packet: Mapping[str, Any]) -> dict[str, Any]:
    window = str(fact_packet.get("window", "")).strip() or "24h"
    window_rule = (
        "Treat 48h as the same live standup voice as 24h. Zoom out on evidence, but do not switch into retrospective, wrap-up, or strategy-memo mode."
        if window == "48h"
        else "Treat 24h as the baseline live standup voice: immediate, spoken, and anchored in what matters now."
    )
    section_contract = []
    for key, label in STANDUP_BRIEF_SECTIONS:
        contract: dict[str, Any] = {
            "key": key,
            "label": label,
            "min_bullets": 1,
            "max_bullets": 2,
            "required_voice_counts": {},
            "objective": "",
        }
        if key == "current_execution":
            contract["max_bullets"] = 4
            contract["required_voice_counts"] = {"executive": 1, "operator_min": 1, "operator_max": 3}
            contract["objective"] = (
                "Start with what is truly getting attention now, then support it with the clearest proof, live posture, operator signal, or timing pressure."
            )
        elif key == "why_this_matters":
            contract["min_bullets"] = 2
            contract["max_bullets"] = 2
            contract["required_voice_counts"] = {"executive": 1, "operator": 1}
            contract["objective"] = (
                "Make the why explicit: one bullet for the customer or product use-story, one bullet for the architecture or operator consequence."
            )
        elif key == "risks_to_watch":
            contract["max_bullets"] = 3
            contract["objective"] = "Name what could break the current story, not a generic calm-status recap."
        elif key == "completed":
            contract["objective"] = (
                "Lead with the verified outcome or strongest execution movement and, when possible, why that move mattered."
            )
        elif key == "next_planned":
            contract["objective"] = "Say what happens next and what that next step unlocks."
        section_contract.append(contract)
    return {
        "schema_version": STANDUP_BRIEF_SCHEMA_VERSION,
        "brief_contract": {
            "sections": section_contract,
            "voice_values": sorted(_VALID_VOICES),
            "window_contract": {
                "window": window,
                "rule": window_rule,
            },
            "style_examples": {
                "completed": [
                    "This window finally cleared two lingering obligations, so the release story is no longer half-finished.",
                    "Lineage also got cleaned up across the window, which matters because the rendered surfaces are no longer drifting from the plans.",
                ],
                "current_execution_executive": [
                    "The unresolved piece in `B-027` is the lane boundary: maintainers and consumer repos still have to infer too much at the moment of action.",
                ],
                "why_this_matters_executive": [
                    "What is at stake here is trust at the moment maintainers choose a lane.",
                    "The benchmark only earns trust if the proof stays harder than the story.",
                ],
            },
            "writing_contract": {
                "target_style": "natural spoken standup narrative",
                "max_words_per_bullet": _MAX_BULLET_WORDS,
                "rules": [
                    "each bullet should carry a claim plus consequence, proof, or steering context",
                    "sound like a maintainer-delivered standup, not a detached status report",
                    "keep 24h and 48h in the same spoken maintainer register; only the evidence window widens",
                    "do not write in first-person singular",
                    "lead with what actually matters here instead of restating metadata",
                    "make the why explicit by naming the use story and the architecture consequence",
                    "avoid generic portfolio-posture filler when a concrete fact exists",
                    "prefer spoken maintainer phrasing over fact-to-bullet restatement",
                    "prefer concrete nouns and verbs over abstract summary phrasing",
                    "avoid recurring signature openings or house phrases across sections",
                    "state the unresolved problem directly instead of using priority metaphors about what has attention",
                    "do not wrap priority in generic labels like 'this work is active' or 'the live issue is'; name the issue itself",
                    "vary sentence openings naturally so the brief sounds like a person, not a template",
                    "never print raw F-### fact ids in the prose; keep citations in fact_ids only",
                ],
            },
            "forbidden_patterns": {
                "raw_repo_paths": True,
                "counts_only_leads": True,
                "discouraged_phrases": ["same window", "current portfolio direction around"],
                "overused_stock_leads": [
                    "The real center of gravity is",
                    "The core proof lane",
                    "The immediate forcing function is",
                    "The boring but important move was",
                    "The big cleanup work finally landed",
                    "The real risk is not",
                    "X is getting the attention because",
                    "X is where attention belongs",
                    "Attention stays on",
                    "X stays hot",
                    "X stays at the top",
                    "This work is active because",
                    "X is the live issue because",
                ],
            },
        },
        "fact_packet": _provider_fact_packet_view(fact_packet=fact_packet),
    }


def _repair_provider_system_prompt() -> str:
    return (
        _provider_system_prompt()
        + " You are repairing a prior invalid reply. "
        "Fix the cited validation failures, preserve any valid structure you can, "
        "and return one fully valid brief that still uses only the supplied fact packet."
    )


def _repair_provider_request_payload(
    *,
    fact_packet: Mapping[str, Any],
    invalid_response: Mapping[str, Any],
    validation_errors: Sequence[str],
) -> dict[str, Any]:
    payload = _provider_request_payload(fact_packet=fact_packet)
    payload["repair_contract"] = {
        "goal": "repair the prior invalid brief so it satisfies the schema and validation contract",
        "validation_errors": [str(error).strip() for error in validation_errors[:8] if str(error).strip()],
    }
    payload["previous_response"] = dict(invalid_response)
    return payload


def _load_cache(*, repo_root: Path) -> dict[str, Any]:
    path = standup_brief_cache_path(repo_root=repo_root)
    entries = _runtime_snapshot_cache_entries(repo_root=repo_root)
    if not path.is_file():
        return {"version": STANDUP_BRIEF_SCHEMA_VERSION, "entries": entries}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": STANDUP_BRIEF_SCHEMA_VERSION, "entries": entries}
    if not isinstance(payload, Mapping):
        return {"version": STANDUP_BRIEF_SCHEMA_VERSION, "entries": entries}
    raw_entries = payload.get("entries")
    if isinstance(raw_entries, Mapping):
        for fingerprint, entry in raw_entries.items():
            fingerprint_token = str(fingerprint).strip()
            if fingerprint_token and isinstance(entry, Mapping):
                entries[fingerprint_token] = dict(entry)
    return {
        "version": str(payload.get("version", STANDUP_BRIEF_SCHEMA_VERSION)).strip() or STANDUP_BRIEF_SCHEMA_VERSION,
        "entries": dict(entries),
    }


def _runtime_snapshot_cache_entries(*, repo_root: Path) -> dict[str, Any]:
    current_path = (Path(repo_root).resolve() / "odylith" / "compass" / "runtime" / "current.v1.json").resolve()
    if not current_path.is_file():
        return {}
    try:
        payload = json.loads(current_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(payload, Mapping):
        return {}

    entries: dict[str, Any] = {}

    def _record(window: str, brief: Mapping[str, Any], *, scope_mode: str, scope_id: str = "") -> None:
        if str(brief.get("schema_version", "")).strip() != STANDUP_BRIEF_SCHEMA_VERSION:
            return
        fingerprint = str(brief.get("fingerprint", "")).strip()
        generated_utc = str(brief.get("generated_utc", "")).strip()
        raw_sections = brief.get("sections")
        if not fingerprint or not generated_utc or not isinstance(raw_sections, Sequence):
            return
        sections = [dict(item) for item in raw_sections if isinstance(item, Mapping)]
        if not sections:
            return
        source = _brief_source_label(source=str(brief.get("source", "")).strip())
        if source not in {"provider", "cache"}:
            return
        entries[fingerprint] = {
            "generated_utc": generated_utc,
            "sections": sections,
            "evidence_lookup": {
                str(fact_id).strip(): dict(entry)
                for fact_id, entry in (brief.get("evidence_lookup", {}) if isinstance(brief.get("evidence_lookup", {}), Mapping) else {}).items()
                if str(fact_id).strip() and isinstance(entry, Mapping)
            },
            "context": {
                "window": str(window).strip(),
                "scope_mode": str(scope_mode).strip(),
                "scope_id": str(scope_id).strip(),
            },
        }

    standup_brief = payload.get("standup_brief")
    if isinstance(standup_brief, Mapping):
        for window, brief in standup_brief.items():
            if isinstance(brief, Mapping):
                _record(str(window), brief, scope_mode="global")

    standup_brief_scoped = payload.get("standup_brief_scoped")
    if isinstance(standup_brief_scoped, Mapping):
        for window, scoped in standup_brief_scoped.items():
            if not isinstance(scoped, Mapping):
                continue
            for scope_id, brief in scoped.items():
                if isinstance(brief, Mapping):
                    _record(str(window), brief, scope_mode="scoped", scope_id=str(scope_id).strip())

    return entries


def _write_cache(*, repo_root: Path, payload: Mapping[str, Any]) -> None:
    path = standup_brief_cache_path(repo_root=repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=path,
        content=json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        lock_key=str(path),
    )


def has_reusable_cached_brief(*, repo_root: Path, fact_packet: Mapping[str, Any]) -> bool:
    """Return whether the exact fact packet already has a reusable cached brief."""

    cache_payload = _load_cache(repo_root=repo_root)
    entries = cache_payload.get("entries")
    if not isinstance(entries, Mapping):
        return False
    fingerprint = standup_brief_fingerprint(fact_packet=fact_packet)
    cached_entry = entries.get(fingerprint)
    if not isinstance(cached_entry, Mapping):
        return False
    return _cache_entry_is_reusable(
        cached_entry=cached_entry,
        fact_packet=fact_packet,
        now_utc=dt.datetime.now(tz=dt.timezone.utc),
    )


def _config_diagnostics(*, config: odylith_reasoning.ReasoningConfig) -> dict[str, Any]:
    provider = str(config.provider or "").strip() or "unknown"
    missing: list[str] = []
    reason = "provider_unavailable"
    message = "Compass could not resolve a runnable AI narration provider from the shared Odylith reasoning configuration."
    if provider == "auto-local":
        missing.append("local_provider")
        message = (
            "Compass could not find a runnable local provider for AI-authored standup briefs. "
            "Install or expose Codex or Claude Code in this environment before refreshing Compass."
        )
    elif provider == "openai-compatible":
        if not str(config.base_url or "").strip():
            missing.append("ODYLITH_REASONING_BASE_URL")
        if not str(config.api_key or "").strip():
            missing.append("ODYLITH_REASONING_API_KEY")
        if not str(config.model or "").strip():
            missing.append("ODYLITH_REASONING_MODEL")
        if missing:
            message = (
                "Compass could not find a runnable local provider, and the shared Odylith reasoning endpoint is also incomplete."
            )
    elif provider == "codex-cli":
        missing.append("codex_cli")
        message = "Compass needs a runnable shared Odylith Codex CLI provider before it can render an AI-authored brief."
    elif provider == "claude-cli":
        missing.append("claude_cli")
        message = "Compass needs a runnable shared Odylith Claude Code provider before it can render an AI-authored brief."
    return {
        "reason": reason,
        "message": message,
        "provider": provider,
        "mode": str(config.mode or "").strip().lower() or "disabled",
        "config_source": str(config.config_source or "").strip() or "defaults",
        "config_path": str(config.config_path or "").strip(),
        "missing_requirements": missing,
    }


def _brief_source_label(*, source: str) -> str:
    token = str(source or "").strip().lower()
    if token == "provider":
        return "provider"
    if token == "cache":
        return "cache"
    if token == "deterministic":
        return "deterministic"
    return "unavailable"


def _ready_brief(
    *,
    source: str,
    fingerprint: str,
    generated_utc: str,
    sections: Sequence[Mapping[str, Any]],
    evidence_lookup: Mapping[str, Mapping[str, Any]] | None = None,
    cache_mode: str = "",
    notice: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "schema_version": STANDUP_BRIEF_SCHEMA_VERSION,
        "status": "ready",
        "source": _brief_source_label(source=source),
        "fingerprint": fingerprint,
        "generated_utc": str(generated_utc or "").strip(),
        "sections": [dict(section) for section in sections],
        "evidence_lookup": {
            str(fact_id).strip(): dict(entry)
            for fact_id, entry in (evidence_lookup or {}).items()
            if str(fact_id).strip() and isinstance(entry, Mapping)
        },
    }
    cache_mode_token = str(cache_mode or "").strip().lower()
    if payload["source"] == "cache" and cache_mode_token in {"exact", "fallback"}:
        payload["cache_mode"] = cache_mode_token
    if isinstance(notice, Mapping):
        title = str(notice.get("title", "")).strip()
        message = str(notice.get("message", "")).strip()
        if title or message:
            payload["notice"] = {
                "title": title,
                "message": message,
                "reason": str(notice.get("reason", "")).strip(),
            }
    return payload


def _cache_ready_brief(
    *,
    fingerprint: str,
    cached_entry: Mapping[str, Any],
    cache_mode: str,
    notice: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    raw_sections = cached_entry.get("sections")
    if not isinstance(raw_sections, Sequence) or not raw_sections:
        return None
    sections = [dict(item) for item in raw_sections if isinstance(item, Mapping)]
    if not sections:
        return None
    return _ready_brief(
        source="cache",
        fingerprint=fingerprint,
        generated_utc=str(cached_entry.get("generated_utc", "")).strip(),
        sections=sections,
        evidence_lookup=cached_entry.get("evidence_lookup", {}),
        cache_mode=cache_mode,
        notice=notice,
    )


def _unavailable_brief(
    *,
    fingerprint: str,
    attempted_utc: str,
    diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "source": "unavailable",
        "fingerprint": fingerprint,
        "generated_utc": "",
        "diagnostics": {
            **dict(diagnostics),
            "attempted_utc": str(attempted_utc or "").strip(),
        },
        "sections": [],
    }


def _provider_deferred_diagnostics(*, config: odylith_reasoning.ReasoningConfig) -> dict[str, Any]:
    diagnostics = _config_diagnostics(config=config)
    diagnostics.update(
        {
            "title": "Live scoped brief deferred",
            "reason": "provider_deferred",
            "message": (
                "Compass deferred live scoped AI narration during dashboard refresh to keep sync bounded. "
                "If a warmed brief is already available for this scope, Compass will reuse it automatically."
            ),
        }
    )
    return diagnostics


def _deterministic_fallback_notice(*, reason: str) -> dict[str, str]:
    reason_token = str(reason or "").strip().lower() or "provider_unavailable"
    message = (
        "Compass rendered a deterministic local brief from the current fact packet "
        "because live AI narration was unavailable for this view."
    )
    if reason_token == "provider_deferred":
        message = (
            "Compass rendered a deterministic local brief from the current fact packet "
            "because live AI narration stayed deferred during this refresh."
        )
    elif reason_token == "provider_empty":
        message = (
            "Compass rendered a deterministic local brief from the current fact packet "
            "because the AI provider returned no usable standup brief."
        )
    elif reason_token == "validation_failed":
        message = (
            "Compass rendered a deterministic local brief from the current fact packet "
            "because the AI provider response did not validate against the standup contract."
        )
    return {
        "title": "Showing deterministic local brief",
        "message": message,
        "reason": reason_token,
    }


def _cache_reuse_notice(
    *,
    fact_packet: Mapping[str, Any],
    reason: str,
    exact_match: bool = False,
    stale: bool = False,
) -> dict[str, str]:
    context = _cache_context(fact_packet=fact_packet)
    scope_mode = context["scope_mode"]
    if str(reason).strip() == "provider_deferred":
        title = "Showing warmed scoped brief"
        if stale:
            message = (
                "Live scoped narration stayed deferred for this render, so Compass reused "
                "the freshest validated brief for the same scope/window even though it is outside "
                "the normal freshness budget."
            )
        elif exact_match:
            message = (
                "Live scoped narration stayed deferred for this render, so Compass reused "
                "the last validated brief for the exact same scope/window fact packet."
            )
        else:
            message = (
                "Live scoped narration stayed deferred for this render, so Compass reused "
                "the freshest validated brief already warmed for this scope and window."
            )
    else:
        title = "Showing last known good brief"
        if stale and exact_match:
            message = (
                "Live AI narration did not produce a validated brief for this render, so Compass reused "
                "the last validated brief for the exact same fact packet even though it is outside "
                "the normal freshness budget."
            )
        elif stale:
            message = (
                "Live AI narration did not produce a validated brief for this render, so Compass reused "
                "the freshest validated brief for the same scope/window even though it is outside "
                "the normal freshness budget."
            )
        elif exact_match:
            message = (
                "Live AI narration did not produce a validated brief for this render, so Compass reused "
                "the last validated brief for the exact same fact packet."
            )
        else:
            message = (
                "Live AI narration did not produce a validated brief for this render, so Compass reused "
                "the freshest validated brief still inside the same scope/window freshness budget."
            )
    if scope_mode == "global":
        title = "Showing last known good global brief"
        if stale:
            title = "Showing stale last known good global brief"
    return {
        "title": title,
        "message": message,
        "reason": str(reason or "").strip(),
    }


def _stale_exact_ready_brief(
    *,
    fingerprint: str,
    cached_entry: Mapping[str, Any] | None,
    fact_packet: Mapping[str, Any],
    reason: str,
) -> dict[str, Any] | None:
    if not isinstance(cached_entry, Mapping):
        return None
    return _cache_ready_brief(
        fingerprint=fingerprint,
        cached_entry=cached_entry,
        cache_mode="exact",
        notice=_cache_reuse_notice(
            fact_packet=fact_packet,
            reason=reason,
            exact_match=True,
            stale=True,
        ),
    )


def _exact_cache_ready_brief_if_reusable(
    *,
    fingerprint: str,
    cached_entry: Mapping[str, Any] | None,
    fact_packet: Mapping[str, Any],
    now_utc: dt.datetime,
) -> dict[str, Any] | None:
    if not isinstance(cached_entry, Mapping):
        return None
    if not _cache_entry_is_reusable(
        cached_entry=cached_entry,
        fact_packet=fact_packet,
        now_utc=now_utc,
    ):
        return None
    return _cache_ready_brief(
        fingerprint=fingerprint,
        cached_entry=cached_entry,
        cache_mode="exact",
    )


def _allow_stale_exact_cache_reuse(*, fact_packet: Mapping[str, Any]) -> bool:
    context = _cache_context(fact_packet=fact_packet)
    if context["scope_mode"] == "global":
        return False
    return True


def _recover_ready_brief_from_cache(
    *,
    cache_entries: Mapping[str, Any],
    fact_packet: Mapping[str, Any],
    fingerprint: str,
    cached_entry: Mapping[str, Any] | None,
    now_utc: dt.datetime,
    reason: str,
) -> dict[str, Any] | None:
    if not _allow_stale_exact_cache_reuse(fact_packet=fact_packet):
        return None
    return _stale_exact_ready_brief(
        fingerprint=fingerprint,
        cached_entry=cached_entry,
        fact_packet=fact_packet,
        reason=reason,
    )


def _fact_lookup(fact_packet: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    facts = fact_packet.get("facts")
    if not isinstance(facts, Sequence):
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for item in facts:
        if not isinstance(item, Mapping):
            continue
        fact_id = str(item.get("id", "")).strip()
        if not fact_id:
            continue
        lookup[fact_id] = dict(item)
    return lookup


def _section_facts(
    *,
    fact_packet: Mapping[str, Any],
    section_key: str,
) -> list[dict[str, Any]]:
    sections = fact_packet.get("sections")
    if isinstance(sections, Sequence):
        for row in sections:
            if not isinstance(row, Mapping):
                continue
            if str(row.get("key", "")).strip() != section_key:
                continue
            facts = row.get("facts")
            if not isinstance(facts, Sequence):
                return []
            return [
                dict(item)
                for item in facts
                if isinstance(item, Mapping) and str(item.get("text", "")).strip()
            ]
    facts = fact_packet.get("facts")
    if not isinstance(facts, Sequence):
        return []
    ranked = [
        dict(item)
        for item in facts
        if isinstance(item, Mapping)
        and str(item.get("section_key", "")).strip() == section_key
        and str(item.get("text", "")).strip()
    ]
    ranked.sort(key=lambda item: int(item.get("priority", 0) or 0), reverse=True)
    return ranked


def _deterministic_sections(*, fact_packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    return compass_standup_brief_deterministic.build_sections(
        fact_packet=fact_packet,
        section_specs=STANDUP_BRIEF_SECTIONS,
    )


def _deterministic_ready_brief(
    *,
    fact_packet: Mapping[str, Any],
    fingerprint: str,
    generated_utc: str,
    reason: str,
) -> dict[str, Any]:
    return _ready_brief(
        source="deterministic",
        fingerprint=fingerprint,
        generated_utc=generated_utc,
        sections=_deterministic_sections(fact_packet=fact_packet),
        evidence_lookup=_brief_evidence_lookup(fact_packet=fact_packet),
        notice=_deterministic_fallback_notice(reason=reason),
    )


def _unavailable_brief_message(reason: str) -> str:
    token = str(reason or "").strip().lower()
    if token == "provider_deferred":
        return "Compass full refresh requires live AI narration and cannot defer into shell-safe deterministic fallback."
    if token == "provider_unavailable":
        return "Compass full refresh could not reach a live AI narration provider and no exact current-packet brief was available."
    if token == "provider_empty":
        return "Compass full refresh did not receive a structured AI brief and no exact current-packet brief was available."
    if token == "validation_failed":
        return "Compass full refresh received an invalid AI brief and no exact current-packet brief was available."
    return "Compass full refresh could not build a current standup brief for this packet."


def _unavailable_ready_brief(
    *,
    fingerprint: str,
    generated_utc: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "source": "unavailable",
        "fingerprint": fingerprint,
        "generated_utc": generated_utc,
        "sections": [],
        "diagnostics": {
            "reason": str(reason or "").strip().lower() or "brief_unavailable",
            "message": _unavailable_brief_message(reason),
        },
        "evidence_lookup": {},
    }


def _fact_ids_by_section(fact_lookup: Mapping[str, Mapping[str, Any]]) -> dict[str, set[str]]:
    by_section: dict[str, set[str]] = {}
    for fact_id, fact in fact_lookup.items():
        section_key = str(fact.get("section_key", "")).strip()
        if not section_key:
            continue
        by_section.setdefault(section_key, set()).add(fact_id)
    return by_section


def _fact_ids_by_section_and_kind(
    fact_lookup: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, set[str]]]:
    by_section: dict[str, dict[str, set[str]]] = {}
    for fact_id, fact in fact_lookup.items():
        section_key = str(fact.get("section_key", "")).strip()
        kind = str(fact.get("kind", "")).strip()
        if not section_key or not kind:
            continue
        by_section.setdefault(section_key, {}).setdefault(kind, set()).add(fact_id)
    return by_section


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w-]+\b", str(text or "")))


def _strip_inline_fact_id_markers(text: str) -> str:
    cleaned = str(text or "")
    cleaned = _PAREN_FACT_ID_RE.sub(" ", cleaned)
    cleaned = _PAREN_FACT_ID_LIST_RE.sub(" ", cleaned)
    cleaned = _STANDALONE_FACT_ID_RE.sub(" ", cleaned)
    cleaned = re.sub(r"\(\s*\)", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"\(\s+", "(", cleaned)
    cleaned = re.sub(r"\s+\)", ")", cleaned)
    return " ".join(cleaned.split()).strip()


def _normalized_fact_id_values(value: Any) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        raw_values = list(value)
    else:
        raw_values = [value]
    tokens: list[str] = []
    for item in raw_values:
        text = str(item).strip()
        if not text:
            continue
        matches = _FACT_ID_RE.findall(text)
        if matches:
            tokens.extend(matches)
            continue
        tokens.append(text)
    return list(dict.fromkeys(tokens))


def _brief_evidence_lookup(*, fact_packet: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for fact_id, fact in _fact_lookup(fact_packet).items():
        text = str(fact.get("text", "")).strip()
        if not text:
            continue
        entry: dict[str, Any] = {
            "text": text,
            "section_key": str(fact.get("section_key", "")).strip(),
            "kind": str(fact.get("kind", "")).strip(),
        }
        workstreams = [
            str(token).strip()
            for token in fact.get("workstreams", [])
            if str(token).strip()
        ]
        if workstreams:
            entry["workstreams"] = workstreams
        evidence[fact_id] = entry
    return evidence


def _validate_brief_response(
    *,
    response: Mapping[str, Any],
    fact_packet: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    fact_lookup = _fact_lookup(fact_packet)
    fact_ids_by_section = _fact_ids_by_section(fact_lookup)
    fact_ids_by_section_and_kind = _fact_ids_by_section_and_kind(fact_lookup)
    freshness_bucket = _fact_packet_freshness_bucket(fact_packet=fact_packet)
    sections = response.get("sections")
    if not isinstance(sections, Sequence):
        return [], ["provider response omitted the sections array"]
    normalized_sections: list[dict[str, Any]] = []
    if len(sections) != len(STANDUP_BRIEF_SECTIONS):
        errors.append("provider response did not return the required five-section brief")
    for index, spec in enumerate(STANDUP_BRIEF_SECTIONS):
        key, label = spec
        row = sections[index] if index < len(sections) else {}
        if not isinstance(row, Mapping):
            errors.append(f"section {key} is missing or malformed")
            continue
        actual_key = str(row.get("key", "")).strip()
        actual_label = str(row.get("label", "")).strip()
        if actual_key != key:
            errors.append(f"section order mismatch for {key}")
        if actual_label != label:
            errors.append(f"section label mismatch for {key}")
        raw_bullets = row.get("bullets")
        if not isinstance(raw_bullets, Sequence):
            errors.append(f"section {key} omitted bullets")
            continue
        section_fact_ids = fact_ids_by_section.get(key, set())
        section_kind_ids = fact_ids_by_section_and_kind.get(key, {})
        bullets: list[dict[str, str]] = []
        executive_count = 0
        operator_count = 0
        section_cited_fact_ids: set[str] = set()
        voice_cited_fact_ids: dict[str, set[str]] = {voice: set() for voice in _VALID_VOICES}
        max_bullets = 2
        if key == "current_execution":
            max_bullets = 4
        elif key == "risks_to_watch":
            max_bullets = 3
        elif key == "why_this_matters":
            if len(raw_bullets) != 2:
                errors.append("Why this matters must contain exactly two bullets")
        if len(raw_bullets) > max_bullets:
            errors.append(f"section {key} exceeded the bullet cap")
        for bullet_index, bullet in enumerate(raw_bullets, start=1):
            if not isinstance(bullet, Mapping):
                errors.append(f"section {key} bullet {bullet_index} is malformed")
                continue
            voice = str(bullet.get("voice", "")).strip().lower()
            text = _strip_inline_fact_id_markers(" ".join(str(bullet.get("text", "")).split()).strip())
            fact_ids = bullet.get("fact_ids")
            if voice not in _VALID_VOICES:
                errors.append(f"section {key} bullet {bullet_index} used an invalid voice")
            if not text:
                errors.append(f"section {key} bullet {bullet_index} is empty")
            if _REPO_PATH_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} exposed a raw repository path")
            if _COUNTS_ONLY_LEAD_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} leads with counts-only telemetry")
            if _DISCOURAGED_PHRASE_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} uses discouraged filler phrasing")
            if _FIRST_PERSON_LEAD_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} starts in first person instead of standup register")
            if _GENERIC_STANDUP_LEAD_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} uses generic standup scaffolding")
            if _OVERUSED_STOCK_LEAD_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} reuses an overused stock lead")
            if _ATTENTION_PRIORITY_LEAD_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} reuses an overused attention-lead pattern")
            if _GENERIC_PRIORITY_WRAPPER_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} reuses a generic priority wrapper")
            if _FACT_ID_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} exposed raw fact markers in prose")
            if _word_count(text) > _MAX_BULLET_WORDS:
                errors.append(f"section {key} bullet {bullet_index} exceeded the word budget")
            normalized_fact_ids: list[str] = []
            local_fact_ids: list[str] = []
            normalized_fact_id_values = _normalized_fact_id_values(fact_ids)
            if not normalized_fact_id_values:
                errors.append(f"section {key} bullet {bullet_index} omitted fact ids")
            else:
                for fact_id in normalized_fact_id_values:
                    token = str(fact_id).strip()
                    if not token:
                        continue
                    if token not in fact_lookup:
                        errors.append(f"section {key} bullet {bullet_index} cited unknown fact id {token}")
                        continue
                    normalized_fact_ids.append(token)
                    if token in section_fact_ids:
                        local_fact_ids.append(token)
                        section_cited_fact_ids.add(token)
                        if voice in _VALID_VOICES:
                            voice_cited_fact_ids.setdefault(voice, set()).add(token)
            if normalized_fact_ids and not local_fact_ids:
                errors.append(f"section {key} bullet {bullet_index} did not cite a section-local fact")
            if voice == "executive":
                executive_count += 1
            elif voice == "operator":
                operator_count += 1
            bullets.append(
                {
                    "voice": voice,
                    "text": text,
                    "_fact_ids": local_fact_ids or normalized_fact_ids,
                }
            )
        if key == "current_execution":
            if executive_count != 1:
                errors.append("Current execution must contain exactly one executive bullet")
            if operator_count < 1 or operator_count > 3:
                errors.append("Current execution must contain between one and three operator bullets")
            direction_ids = section_kind_ids.get("direction", set())
            if direction_ids and not (voice_cited_fact_ids.get("executive", set()) & direction_ids):
                errors.append("Current execution executive bullet must cite direction evidence")
            freshness_ids = section_kind_ids.get("freshness", set())
            if (
                freshness_bucket in {"aging", "stale"}
                and freshness_ids
                and not (section_cited_fact_ids & freshness_ids)
            ):
                errors.append("Current execution must cite freshness evidence when the fact packet is aging or stale")
        elif key == "why_this_matters":
            if executive_count != 1 or operator_count != 1:
                errors.append("Why this matters must contain one executive bullet and one operator bullet")
            executive_impact_ids = section_kind_ids.get("executive_impact", set())
            operator_leverage_ids = section_kind_ids.get("operator_leverage", set())
            if executive_impact_ids and not (voice_cited_fact_ids.get("executive", set()) & executive_impact_ids):
                errors.append("Why this matters executive bullet must cite impact evidence")
            if operator_leverage_ids and not (voice_cited_fact_ids.get("operator", set()) & operator_leverage_ids):
                errors.append("Why this matters operator bullet must cite leverage evidence")
        elif key == "completed":
            concrete_ids = section_kind_ids.get("plan_completion", set()) | section_kind_ids.get(
                "execution_highlight", set()
            )
            if concrete_ids and not (section_cited_fact_ids & concrete_ids):
                errors.append("Completed in this window must cite concrete movement evidence")
        elif key == "next_planned":
            forcing_ids = section_kind_ids.get("forcing_function", set()) | section_kind_ids.get(
                "fallback_next", set()
            )
            if forcing_ids and not (section_cited_fact_ids & forcing_ids):
                errors.append("Next planned must cite forcing-function evidence")
        normalized_sections.append(
            {
                "key": key,
                "label": label,
                "bullets": [
                    {
                        "voice": str(item.get("voice", "")).strip(),
                        "text": str(item.get("text", "")).strip(),
                        "fact_ids": list(item.get("_fact_ids", [])),
                    }
                    for item in bullets
                    if str(item.get("text", "")).strip()
                ],
            }
        )
    return normalized_sections, errors


def _provider_request(*, fact_packet: Mapping[str, Any]) -> odylith_reasoning.StructuredReasoningRequest:
    return odylith_reasoning.StructuredReasoningRequest(
        system_prompt=_provider_system_prompt(),
        schema_name="compass_standup_brief",
        output_schema=_provider_output_schema(),
        prompt_payload=_provider_request_payload(fact_packet=fact_packet),
        reasoning_effort=_COMPASS_PROVIDER_REASONING_EFFORT,
        timeout_seconds=_COMPASS_PROVIDER_TIMEOUT_SECONDS,
    )


def _repair_provider_request(
    *,
    fact_packet: Mapping[str, Any],
    invalid_response: Mapping[str, Any],
    validation_errors: Sequence[str],
) -> odylith_reasoning.StructuredReasoningRequest:
    return odylith_reasoning.StructuredReasoningRequest(
        system_prompt=_repair_provider_system_prompt(),
        schema_name="compass_standup_brief_repair",
        output_schema=_provider_output_schema(),
        prompt_payload=_repair_provider_request_payload(
            fact_packet=fact_packet,
            invalid_response=invalid_response,
            validation_errors=validation_errors,
        ),
        reasoning_effort=_COMPASS_PROVIDER_REASONING_EFFORT,
        timeout_seconds=_COMPASS_PROVIDER_TIMEOUT_SECONDS,
    )


def _request_provider_with_empty_retry(
    *,
    provider: odylith_reasoning.ReasoningProvider,
    request: odylith_reasoning.StructuredReasoningRequest,
    max_attempts: int = _EMPTY_PROVIDER_MAX_ATTEMPTS,
) -> Mapping[str, Any] | None:
    """Retry one-shot empty provider replies before failing closed.

    Compass standup already treats invalid structured replies as a separate
    validation/repair path. This helper hardens only the narrower transient case
    where the provider returns no structured payload at all even though the same
    request may succeed on an immediate rerun.
    """

    attempts = max(1, int(max_attempts))
    for _attempt in range(attempts):
        result = provider.generate_structured(request=request)
        if isinstance(result, Mapping):
            return result
    return None


def build_standup_brief(
    *,
    repo_root: Path,
    fact_packet: Mapping[str, Any],
    generated_utc: str,
    config: odylith_reasoning.ReasoningConfig | None = None,
    provider: odylith_reasoning.ReasoningProvider | None = None,
    allow_provider: bool = True,
    prefer_provider: bool = False,
    allow_cache_recovery: bool = True,
    allow_deterministic_fallback: bool = True,
) -> dict[str, Any]:
    """Build a validated standup brief, falling back to deterministic local narration."""

    repo_root = Path(repo_root).resolve()
    fingerprint = standup_brief_fingerprint(fact_packet=fact_packet)
    now_utc = dt.datetime.now(tz=dt.timezone.utc)
    cache_payload = _load_cache(repo_root=repo_root)
    entries = cache_payload.get("entries")
    cache_entries = dict(entries) if isinstance(entries, Mapping) else {}
    cache_context = _cache_context(fact_packet=fact_packet)
    cached_entry = cache_entries.get(fingerprint)
    if (
        not prefer_provider
        and isinstance(cached_entry, Mapping)
        and _cache_entry_is_reusable(
        cached_entry=cached_entry,
        fact_packet=fact_packet,
        now_utc=now_utc,
        )
    ):
        cached_ready = _cache_ready_brief(
            fingerprint=fingerprint,
            cached_entry=cached_entry,
            cache_mode="exact",
        )
        if cached_ready is not None:
            return cached_ready

    resolved_config = config or odylith_reasoning.reasoning_config_from_env(repo_root=repo_root)
    if not allow_provider:
        if allow_cache_recovery:
            recovered_ready = _recover_ready_brief_from_cache(
                cache_entries=cache_entries,
                reason="provider_deferred",
                fact_packet=fact_packet,
                fingerprint=fingerprint,
                cached_entry=cached_entry,
                now_utc=now_utc,
            )
            if recovered_ready is not None:
                return recovered_ready
        if allow_deterministic_fallback:
            return _deterministic_ready_brief(
                fact_packet=fact_packet,
                fingerprint=fingerprint,
                generated_utc=generated_utc,
                reason="provider_deferred",
            )
        return _unavailable_ready_brief(
            fingerprint=fingerprint,
            generated_utc=generated_utc,
            reason="provider_deferred",
        )
    resolved_provider = provider or odylith_reasoning.provider_from_config(
        resolved_config,
        repo_root=repo_root,
        require_auto_mode=False,
        allow_implicit_local_provider=True,
    )
    if resolved_provider is None:
        exact_ready = _exact_cache_ready_brief_if_reusable(
            fingerprint=fingerprint,
            cached_entry=cached_entry,
            fact_packet=fact_packet,
            now_utc=now_utc,
        )
        if exact_ready is not None:
            return exact_ready
        if allow_cache_recovery:
            recovered_ready = _recover_ready_brief_from_cache(
                cache_entries=cache_entries,
                reason="provider_unavailable",
                fact_packet=fact_packet,
                fingerprint=fingerprint,
                cached_entry=cached_entry,
                now_utc=now_utc,
            )
            if recovered_ready is not None:
                return recovered_ready
        if allow_deterministic_fallback:
            return _deterministic_ready_brief(
                fact_packet=fact_packet,
                fingerprint=fingerprint,
                generated_utc=generated_utc,
                reason="provider_unavailable",
            )
        return _unavailable_ready_brief(
            fingerprint=fingerprint,
            generated_utc=generated_utc,
            reason="provider_unavailable",
        )

    raw_result = _request_provider_with_empty_retry(
        provider=resolved_provider,
        request=_provider_request(fact_packet=fact_packet),
    )
    if not isinstance(raw_result, Mapping):
        exact_ready = _exact_cache_ready_brief_if_reusable(
            fingerprint=fingerprint,
            cached_entry=cached_entry,
            fact_packet=fact_packet,
            now_utc=now_utc,
        )
        if exact_ready is not None:
            return exact_ready
        if allow_cache_recovery:
            recovered_ready = _recover_ready_brief_from_cache(
                cache_entries=cache_entries,
                reason="provider_empty",
                fact_packet=fact_packet,
                fingerprint=fingerprint,
                cached_entry=cached_entry,
                now_utc=now_utc,
            )
            if recovered_ready is not None:
                return recovered_ready
        if allow_deterministic_fallback:
            return _deterministic_ready_brief(
                fact_packet=fact_packet,
                fingerprint=fingerprint,
                generated_utc=generated_utc,
                reason="provider_empty",
            )
        return _unavailable_ready_brief(
            fingerprint=fingerprint,
            generated_utc=generated_utc,
            reason="provider_empty",
        )

    sections, errors = _validate_brief_response(
        response=raw_result,
        fact_packet=fact_packet,
    )
    if errors:
        repaired_result = resolved_provider.generate_structured(
            request=_repair_provider_request(
                fact_packet=fact_packet,
                invalid_response=raw_result,
                validation_errors=errors,
            )
        )
        if isinstance(repaired_result, Mapping):
            repaired_sections, repaired_errors = _validate_brief_response(
                response=repaired_result,
                fact_packet=fact_packet,
            )
            if not repaired_errors:
                raw_result = repaired_result
                sections = repaired_sections
                errors = []
            else:
                errors = repaired_errors
        if errors:
            exact_ready = _exact_cache_ready_brief_if_reusable(
                fingerprint=fingerprint,
                cached_entry=cached_entry,
                fact_packet=fact_packet,
                now_utc=now_utc,
            )
            if exact_ready is not None:
                return exact_ready
            if allow_cache_recovery:
                recovered_ready = _recover_ready_brief_from_cache(
                    cache_entries=cache_entries,
                    reason="validation_failed",
                    fact_packet=fact_packet,
                    fingerprint=fingerprint,
                    cached_entry=cached_entry,
                    now_utc=now_utc,
                )
                if recovered_ready is not None:
                    return recovered_ready
            if allow_deterministic_fallback:
                return _deterministic_ready_brief(
                    fact_packet=fact_packet,
                    fingerprint=fingerprint,
                    generated_utc=generated_utc,
                    reason="validation_failed",
                )
            return _unavailable_ready_brief(
                fingerprint=fingerprint,
                generated_utc=generated_utc,
                reason="validation_failed",
            )

    ready = _ready_brief(
        source="provider",
        fingerprint=fingerprint,
        generated_utc=generated_utc,
        sections=sections,
        evidence_lookup=_brief_evidence_lookup(fact_packet=fact_packet),
    )
    cache_entries[fingerprint] = {
        "generated_utc": ready["generated_utc"],
        "sections": ready["sections"],
        "evidence_lookup": ready["evidence_lookup"],
        "context": cache_context,
    }
    _write_cache(
        repo_root=repo_root,
        payload={
            "version": STANDUP_BRIEF_SCHEMA_VERSION,
            "entries": cache_entries,
        },
    )
    return ready


def brief_to_digest_lines(brief: Mapping[str, Any]) -> list[str]:
    """Render a structured standup brief into legacy digest lines."""

    if str(brief.get("status", "")).strip() != "ready":
        diagnostics = brief.get("diagnostics")
        if isinstance(diagnostics, Mapping):
            title = str(diagnostics.get("title", "")).strip() or "Standup brief unavailable"
            message = str(diagnostics.get("message", "")).strip()
            if message:
                return [f"{title}: {message}"]
            if title:
                return [title]
        return []
    notice = brief.get("notice")
    lines: list[str] = []
    if isinstance(notice, Mapping):
        title = str(notice.get("title", "")).strip()
        message = str(notice.get("message", "")).strip()
        if title and message:
            lines.append(f"{title}: {message}")
        elif title:
            lines.append(title)
        elif message:
            lines.append(message)
    raw_sections = brief.get("sections")
    if not isinstance(raw_sections, Sequence):
        return []
    for key, label in STANDUP_BRIEF_SECTIONS:
        row = next(
            (
                dict(item)
                for item in raw_sections
                if isinstance(item, Mapping) and str(item.get("key", "")).strip() == key
            ),
            {},
        )
        raw_bullets = row.get("bullets")
        bullets = []
        if isinstance(raw_bullets, Sequence):
            for item in raw_bullets:
                if not isinstance(item, Mapping):
                    continue
                voice = str(item.get("voice", "")).strip().lower()
                text = " ".join(str(item.get("text", "")).split()).strip()
                if not text:
                    continue
                if voice in _VALID_VOICES and len(raw_bullets) > 1:
                    bullets.append(f"{voice.title()}: {text}")
                else:
                    bullets.append(text)
        line = f"{label}: {' | '.join(bullets)}" if bullets else f"{label}:"
        lines.append(line)
    return lines


__all__ = [
    "STANDUP_BRIEF_CACHE_PATH",
    "STANDUP_BRIEF_SCHEMA_VERSION",
    "STANDUP_BRIEF_SECTIONS",
    "brief_to_digest_lines",
    "build_standup_brief",
    "has_reusable_cached_brief",
    "standup_brief_cache_path",
    "standup_brief_fingerprint",
]
