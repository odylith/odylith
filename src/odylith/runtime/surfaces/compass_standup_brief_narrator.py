"""Compass standup brief narrator and cache.

Compass runtime remains authoritative for fact selection, evidence ranking, and
fingerprinting. This module owns the bounded narration layer:

- reuse the shared Odylith reasoning provider configuration and adapters;
- request a fixed four-section standup brief with schema-constrained output;
- validate the reply against the deterministic fact packet and UI contract;
- cache validated results by exact fact-packet fingerprint; and
- fall back to a deterministic structured brief when live AI narration is not
  available.
"""

from __future__ import annotations

import datetime as dt
import difflib
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.surfaces import compass_standup_brief_deterministic
from odylith.runtime.surfaces import compass_standup_brief_voice_validation


STANDUP_BRIEF_SCHEMA_VERSION = "v22"
STANDUP_BRIEF_CACHE_PATH = ".odylith/compass/standup-brief-cache.v22.json"
STANDUP_BRIEF_SECTIONS: tuple[tuple[str, str], ...] = (
    ("completed", "Completed in this window"),
    ("current_execution", "Current execution"),
    ("next_planned", "Next planned"),
    ("risks_to_watch", "Risks to watch"),
)
_SECTION_LABELS = {key: label for key, label in STANDUP_BRIEF_SECTIONS}
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
    r"^\s*(?:this matters\b|the proof is concrete now\b|the proof lane is still\b|what matters here is\b)",
    re.IGNORECASE,
)
_NEGATED_COMPLETED_LEAD_RE = re.compile(
    r"^\s*no\s+(?:verified\s+)?(?:portfolio\s+)?milestone(?:s)?\s+(?:closed|closeout|closure)\b.*\bbut\b",
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
    r"(?:(?:is|are)\s+(?:still\s+)?getting\s+(?:the\s+)?(?:attention|work|push)(?:\s+now)?|stays\s+hot|stays\s+at\s+the\s+top|"
    r"is\s+getting\s+active\s+implementation\s+time|where\s+attention\s+(?:belongs|stays|lands)))\b",
    re.IGNORECASE,
)
_GENERIC_PRIORITY_WRAPPER_RE = re.compile(
    r"^\s*(?:this\s+work\s+is\s+(?:still\s+)?(?:live|active)\s+because|"
    r"(?:`?B-\d+`?|[A-Za-z][A-Za-z0-9`'’(),/\- ]{0,90})\s+is\s+(?:still\s+)?"
    r"the\s+(?:live\s+problem|live\s+issue|active\s+lane|live\s+lane|implementation\s+lane|"
    r"live\s+top\s+lane|top\s+lane|live\s+push|live\s+job|work\s+that\s+matters\s+now)\s+because)\b",
    re.IGNORECASE,
)
_GENERIC_SIGNAL_LEAD_RE = re.compile(
    r"^\s*the\s+clearest\s+(?:field\s+|operator\s+|execution\s+)?signal\s+(?:is|has\s+been)\b",
    re.IGNORECASE,
)
_GENERIC_POSTURE_SLOGAN_RE = re.compile(
    r"^\s*self-host\s+posture\s+is\s+clean\b",
    re.IGNORECASE,
)
_GENERIC_NEXT_STEP_RE = re.compile(
    r"^\s*(?:[A-Z][A-Za-z0-9`'’(),/\- ]{4,90}\s+comes\s+next\s+because|the\s+next\s+move\s+is\b|next\s+up\s+is\b|then\b)",
    re.IGNORECASE,
)
_GENERIC_PROGRESS_SLOGAN_RE = re.compile(
    r"\b(?:plans?\s+are\s+being\s+turned\s+into\s+implementation|"
    r"backlog\s+narrative|shipped-runtime\s+proof\s+did\s+not\s+drift|"
    r"debt\s+hardens\s+into\s+operating\s+habit|temporary\s+exceptions\s+become\s+normal)\b",
    re.IGNORECASE,
)
_GENERIC_LANE_WRAPPER_RE = re.compile(
    r"^\s*(?:under\s+that\s+lane\b|"
    r"(?:cross-surface|runtime|browser|release|proof|freshness|ux)[A-Za-z0-9`'’(),/\- ]{0,90}\s+is\s+moving\s+alongside\b|"
    r"(?:cross-surface|runtime|browser|release|proof|freshness|ux)[A-Za-z0-9`'’(),/\- ]{0,90}\s+are\s+moving\s+alongside\b)",
    re.IGNORECASE,
)
_GENERIC_WINDOW_LEAD_RE = re.compile(
    r"^\s*over\s+the\s+last\s+48\s+hours,\b",
    re.IGNORECASE,
)
_GENERIC_TIMING_WRAPPER_RE = re.compile(
    r"^\s*the\s+(?:schedule|timing)\s+still\s+matters\s+here\b",
    re.IGNORECASE,
)
_GENERIC_BENCHMARK_CHALLENGE_RE = re.compile(
    r"^\s*if\s+odylith\s+is\s+genuinely\s+better,\b",
    re.IGNORECASE,
)
_INTERNAL_TEMPLATE_RE = re.compile(
    r"^\s*(?:the\s+unresolved\s+decision\s+is\s+in|"
    r"this\s+lane\s+is\s+still\s+carrying\s+real\s+weight|"
    r"the\s+lane\s+can\s+still\s+sprawl|"
    r"making\s+that\s+lane\s+contract\s+explicit|"
    r"if\s+we\s+get\s+this\s+right|"
    r"name\s+the\s+next\s+concrete\s+checkpoint|"
    r"what\s+is\s+at\s+stake\s+here\s+is\s+trust|"
    r"the\s+live\s+repo\s+posture\s+makes\s+that\s+concrete)\b|"
    r"\bkept\s+showing\s+up\s+as\s+the\s+clearest\s+proof\s+point\b",
    re.IGNORECASE,
)
_FACT_ID_RE = re.compile(r"F-\d{3}")
_PAREN_FACT_ID_RE = re.compile(r"(?:\(\s*F-\d{3}\s*\)\s*)+")
_PAREN_FACT_ID_LIST_RE = re.compile(r"\(\s*F-\d{3}(?:\s*[,/&+|]\s*F-\d{3})+\s*\)")
_STANDALONE_FACT_ID_RE = re.compile(r"(?<![A-Za-z0-9])F-\d{3}(?![A-Za-z0-9])")
_VOLATILE_FRESHNESS_TEXT_RE = re.compile(r"^Freshness signal is (?:aging|stale):", re.IGNORECASE)
_MAX_BULLET_WORDS = 48
_EMPTY_PROVIDER_MAX_ATTEMPTS = 2
_COMPASS_PROVIDER_TIMEOUT_SECONDS = 30.0
_PROVIDER_FACT_LIMITS_BY_SECTION = {
    "completed": 3,
    "current_execution": 4,
    "next_planned": 2,
    "risks_to_watch": 3,
}
_COMPACT_RETRY_PROVIDER_FACT_LIMITS_BY_SECTION = {
    "completed": 2,
    "current_execution": 2,
    "next_planned": 1,
    "risks_to_watch": 2,
}
_CACHE_TTL_SECONDS_BY_FRESHNESS = {
    "live": 15 * 60,
    "recent": 45 * 60,
    "aging": 2 * 60 * 60,
    "stale": 4 * 60 * 60,
    "unknown": 60 * 60,
}
_CONTEXT_CACHE_MAX_AGE_SECONDS = 24 * 60 * 60


def _default_compass_reasoning_config() -> odylith_reasoning.ReasoningConfig:
    return odylith_reasoning.ReasoningConfig(
        mode="auto",
        provider="codex-cli",
        model="",
        base_url="",
        api_key="",
        scope_cap=5,
        timeout_seconds=_COMPASS_PROVIDER_TIMEOUT_SECONDS,
        codex_bin="codex",
        codex_reasoning_effort="high",
        claude_bin="claude",
        claude_reasoning_effort="high",
    )


def _provider_request_profile(
    *,
    config: odylith_reasoning.ReasoningConfig | None = None,
) -> odylith_reasoning.StructuredReasoningProfile:
    resolved_config = config or _default_compass_reasoning_config()
    return odylith_reasoning.cheap_structured_reasoning_profile(resolved_config)

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


def _cache_entry_within_context_age_limit(
    *,
    cached_entry: Mapping[str, Any],
    now_utc: dt.datetime,
) -> bool:
    generated_ts = _parse_iso_datetime(str(cached_entry.get("generated_utc", "")).strip())
    if generated_ts is None:
        return False
    age_seconds = (now_utc - generated_ts).total_seconds()
    if age_seconds < 0:
        return False
    return age_seconds <= float(_CONTEXT_CACHE_MAX_AGE_SECONDS)


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
    if str(cached_context.get("scope_mode", "")).strip().lower() != target_context["scope_mode"]:
        return False
    if target_context["scope_mode"] == "scoped":
        return str(cached_context.get("scope_id", "")).strip() == target_context["scope_id"]
    return True


def _provider_system_prompt(*, compact_retry: bool = False) -> str:
    if compact_retry:
        return (
            "You are Compass, the standup narrator. "
            "Write plainspoken grounded maintainer narration from the supplied fact packet only. "
            "Keep the same human spoken voice for 24h and 48h. "
            "Be clear, specific, natural, and free-flowing, not canned or rhythmic. "
            "Do not use stock framing, dashboard-wise abstractions, stagey metaphors, or polished status-report phrasing. "
            "Name the issue, movement, proof, next step, or risk directly. "
            "For global scope, mention every touched workstream somewhere in the brief. "
            "Keep section order and labels exactly as provided. "
            "Do not print raw fact ids in prose; cite only supplied fact ids in fact_ids."
        )
    return (
        "You are Compass, the executive standup narrator. "
        "Write a concise four-section standup brief for maintainers who need one clear read on what changed, what is getting attention now, what comes next, and what could still go wrong. "
        "Write in plainspoken grounded maintainer narration: like a strong maintainer speaking off notes, human, plain, specific, open, clear, lightly soulful, and free-flowing rather than branded dashboard prose. "
        "Keep the voice consistent across 24h and 48h windows; a 48h brief is the same live standup voice as 24h, not a retrospective or strategy memo. "
        "Write with stance: decide what deserves space, what is just bookkeeping, and where the pressure actually is. "
        "Write like someone who has been in the work, not like a system filling four polished slots. "
        "Use ordinary words another maintainer can understand on first read. If a sentence sounds like a dashboard trying to sound insightful, rewrite it. "
        "Do not write in first-person singular. "
        "Do not invent a house style or signature lead-in. Avoid stock scaffolding and repeated openings such as "
        "'The real center of gravity is', 'The core proof lane', 'The immediate forcing function is', "
        "'The boring but important move was', 'X is getting the attention because', 'attention stays on', "
        "'stays hot', 'This work is active because', 'The clearest field signal is', "
        "'Self-host posture is clean', 'Next up is', 'What matters here is', 'Under that lane', "
        "'X is moving alongside release work because', repeated 'Over the last 48 hours' leads, "
        "'The schedule still matters here', 'If Odylith is genuinely better', 'Work is now driving through', "
        "'There is a live-version split to keep in view', 'Release planning and execution are running together', "
        "'Most of the movement this window sat in', 'Next step is', 'The follow-on adds', or similar canned phrases. "
        "Do not lean on stagey metaphors or dashboard-wise phrasing like 'pressure point', 'center of gravity', 'muddy', 'slippery', 'top lane', or 'window coverage spans'. "
        "Do not use managerial wrappers like 'The next move is' or telemetry summaries like 'with the clearest movement around'. "
        "Vary sentence openings naturally across sections, windows, and workstreams. "
        "Prefer ordinary speech: say what changed, what is getting attention now, why it matters, and what could still go wrong. "
        "The UI already tells the reader which time window is active, so do not keep reopening bullets with window labels. "
        "Do not make every bullet sound equally polished or equally shaped. Some bullets can be blunt, some connective, some sharp. "
        "If a bullet could fit almost any repo, it is too generic; rewrite it until it feels observed rather than summarized. "
        "Each bullet must stay visibly tethered to the cited fact language. If the cited facts disappeared, the bullet should stop making sense. "
        "Carry consequence inside the relevant bullet instead of carving out a separate explanation section. "
        "Use only the supplied fact packet and cited fact ids. "
        "Treat any live self-host or install posture facts in the packet as authoritative over older release-history narrative when they disagree. "
        "For global scope, if the fact packet shows multiple touched workstreams in the window, make sure every touched workstream appears somewhere in the brief. "
        "Do not collapse the window into one flagship lane and silently drop the rest. "
        "Do not include literal fact ids in bullet text; cite them only in the fact_ids field. "
        "Keep the section order and labels exactly as provided. "
        "Compress hard: each bullet should carry movement, consequence, or steering context, not generic posture. "
        "Prefer concrete pressure, friction, proof, and consequence over managerial umbrella terms. "
        "Never open a bullet by reciting a long workstream title and then declaring it the live lane, live push, or next item. "
        "Name the actual issue, move, proof point, or next action instead. "
        "Do not lead completed bullets with what did not happen when concrete movement facts are available. "
        "Do not give every bullet the same tidy claim-then-consequence cadence. "
        "Blunt, uneven human phrasing is better than polished portable summary prose. "
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
                                "required": ["text", "fact_ids"],
                                "additionalProperties": False,
                                "properties": {
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


def _provider_fact_packet_view(*, fact_packet: Mapping[str, Any], compact_retry: bool = False) -> dict[str, Any]:
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
                "watch_item",
                *(() if compact_retry else ("use_story", "architecture_consequence")),
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
            fact_limits = (
                _COMPACT_RETRY_PROVIDER_FACT_LIMITS_BY_SECTION
                if compact_retry
                else _PROVIDER_FACT_LIMITS_BY_SECTION
            )
            max_facts = fact_limits.get(section_key, 2)
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


def _provider_request_payload(*, fact_packet: Mapping[str, Any], compact_retry: bool = False) -> dict[str, Any]:
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
            "objective": "",
        }
        if key == "current_execution":
            contract["max_bullets"] = 4
            contract["objective"] = (
                "Start with what is actually being worked now in ordinary words, then support it with the clearest proof, live posture, operator signal, or timing risk."
            )
        elif key == "risks_to_watch":
            contract["max_bullets"] = 3
            contract["objective"] = "Name what could break the current story, not a generic calm-status recap."
        elif key == "completed":
            contract["objective"] = (
                "Lead with the verified outcome or strongest execution movement in ordinary words, then say why it changed the work when that helps."
            )
        elif key == "next_planned":
            contract["objective"] = "Say what happens next in plain language and what that next step unlocks."
        section_contract.append(contract)
    return {
        "schema_version": STANDUP_BRIEF_SCHEMA_VERSION,
        "retry_mode": "compact_recovery" if compact_retry else "standard",
        "brief_contract": {
            "sections": section_contract,
            "window_contract": {
                "window": window,
                "rule": window_rule,
            },
            "style_examples": {
                "completed": [
                    "Two cleanup threads finally got put away. The first-turn bootstrap work closed, and the reasoning-package boundary work closed with it.",
                    "This repo moved onto runtime `0.1.9`, and the hosted install smoke still lines up with the shipped path. The proof is following the thing maintainers actually hand people.",
                ],
                "current_execution_executive": [
                    "Most of the work right now is in `B-022`. If the benchmark stays easy to game, the proof stops meaning much.",
                ],
            },
            "writing_contract": {
                "target_style": "plainspoken grounded maintainer narration",
                "max_words_per_bullet": _MAX_BULLET_WORDS,
                "rules": [
                    "each bullet should carry a claim plus consequence, proof, or steering context",
                    "sound like a maintainer-delivered standup, not a detached status report",
                    "keep 24h and 48h in the same spoken maintainer register; only the evidence window widens",
                    "do not write in first-person singular",
                    "use ordinary words another maintainer can understand on first read",
                    "stay open and free-flowing without sounding polished, sloganized, or performed",
                    "lead with what actually matters here instead of restating metadata",
                    "carry customer need or operator consequence inside the relevant bullet instead of splitting it into a dedicated explanation section",
                    "avoid generic portfolio-posture filler when a concrete fact exists",
                    "prefer spoken maintainer phrasing over fact-to-bullet restatement",
                    "prefer concrete nouns and verbs over abstract summary phrasing",
                    "if a sentence sounds like a dashboard trying to sound wise, rewrite it in simpler language",
                    "prefer observed pressure, friction, or proof over portfolio umbrella language",
                    "keep each bullet visibly tethered to the cited fact language",
                    "if the cited facts disappear and the bullet still sounds plausible, it is too generic for Compass",
                    "for global scope, if the packet carries multiple touched workstreams, mention every touched workstream somewhere in the brief",
                    "do not lead bullets by restating long workstream titles or queue labels",
                    "do not narrate self-host status with slogan language like 'posture is clean'",
                    "do not use absence-plus-compensation leads like 'no milestone closed ..., but ...' when movement facts exist",
                    "do not write next-step bullets as 'X comes next because', 'The next move is', or start follow-ons with 'Then'",
                    "do not write bullets as 'Next up is' or 'What matters here is'; start with the issue, action, or consequence itself",
                    "do not write generic lane wrappers like 'under that lane' or 'X is moving alongside release work because'",
                    "do not keep reopening 48h bullets with 'Over the last 48 hours'; the window is already visible in the surface",
                    "do not use stock timing wrappers like 'the schedule still matters here' or rhetorical tests like 'if Odylith is genuinely better'",
                    "do not use stagey metaphors or dashboard-wise abstractions like 'pressure point', 'center of gravity', 'muddy', 'slippery', 'top lane', 'window coverage spans', or 'with the clearest movement around'",
                    "do not write release-summary wrappers like 'Work is now driving through', 'There is a live-version split to keep in view', 'Release planning and execution are running together', 'Most of the movement this window sat in', 'Next step is', or 'The follow-on adds'",
                    "do not lean on abstract debt-hardening slogans when concrete outcomes or risks can be named directly",
                    "avoid recurring signature openings or house phrases across sections",
                    "do not make every bullet sound equally polished, balanced, or summary-shaped",
                    "do not smooth the whole brief into the same polished claim-then-consequence sentence pattern",
                    "if a bullet could fit almost any repo, it is too generic for Compass",
                    "allow bluntness and uneven emphasis when the evidence calls for it",
                    "state the unresolved problem directly instead of using priority metaphors about what has attention",
                    "do not wrap priority in generic labels like 'this work is active' or 'the live issue is'; name the issue itself",
                    "vary sentence openings naturally so the brief sounds like a person, not a template",
                    "never print raw F-### fact ids in the prose; keep citations in fact_ids only",
                ],
            },
            "forbidden_patterns": {
                "raw_repo_paths": True,
                "counts_only_leads": True,
                "discouraged_phrases": [
                    "same window",
                    "current portfolio direction around",
                    "pressure point",
                    "muddy",
                    "slippery",
                    "top lane",
                    "window coverage spans",
                    "with the clearest movement around",
                    "the next move is",
                    "work is now driving through",
                    "there is a live-version split to keep in view",
                    "release planning and execution are running together",
                    "most of the movement this window sat in",
                    "next step is",
                    "the follow-on adds",
                ],
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
                    "The clearest field signal is",
                    "Self-host posture is clean",
                    "Next up is",
                    "What matters here is",
                    "Under that lane",
                    "X is moving alongside release work because",
                    "Over the last 48 hours,",
                    "The schedule still matters here",
                    "If Odylith is genuinely better",
                ],
            },
        },
        "fact_packet": _provider_fact_packet_view(fact_packet=fact_packet, compact_retry=compact_retry),
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


def _path_signature_token(path: Path) -> str:
    return json.dumps(odylith_context_cache.path_signature(path), sort_keys=True, separators=(",", ":"))


@lru_cache(maxsize=32)
def _load_cache_payload(*, cache_path: str, signature_token: str) -> Mapping[str, Any] | None:
    del signature_token
    path = Path(cache_path)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, Mapping) else None


@lru_cache(maxsize=64)
def _load_cache_entries_from_path_cached(path_str: str, signature_token: str) -> dict[str, Any]:
    del signature_token
    path = Path(path_str)
    payload = _load_cache_payload(
        cache_path=str(path),
        signature_token=_path_signature_token(path),
    )
    if not isinstance(payload, Mapping):
        return {}
    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, Mapping):
        return {}
    return {
        str(fingerprint).strip(): dict(entry)
        for fingerprint, entry in raw_entries.items()
        if str(fingerprint).strip() and isinstance(entry, Mapping)
    }


def _load_cache(*, repo_root: Path) -> dict[str, Any]:
    path = standup_brief_cache_path(repo_root=repo_root)
    current_path = (Path(repo_root).resolve() / "odylith" / "compass" / "runtime" / "current.v1.json").resolve()
    entries = _runtime_snapshot_cache_entries(
        current_path=current_path,
        signature_token=_path_signature_token(current_path),
    )
    if not path.is_file():
        return {"version": STANDUP_BRIEF_SCHEMA_VERSION, "entries": entries}
    payload = _load_cache_payload(
        cache_path=str(path.resolve()),
        signature_token=_path_signature_token(path.resolve()),
    )
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


def _legacy_cache_paths(*, repo_root: Path) -> list[Path]:
    cache_dir = standup_brief_cache_path(repo_root=repo_root).parent
    current_path = standup_brief_cache_path(repo_root=repo_root)
    candidates = []
    for path in cache_dir.glob("standup-brief-cache.v*.json"):
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved == current_path:
            continue
        candidates.append(resolved)

    def _sort_key(path: Path) -> tuple[int, str]:
        match = re.search(r"\.v(\d+)\.json$", path.name)
        version = int(match.group(1)) if match else 0
        return (version, path.name)

    return sorted(candidates, key=_sort_key, reverse=True)


def _load_cache_entries_from_path(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    return _load_cache_entries_from_path_cached(
        str(resolved),
        _path_signature_token(resolved),
    )


@lru_cache(maxsize=16)
def _runtime_snapshot_cache_entries(*, current_path: Path, signature_token: str) -> dict[str, Any]:
    del signature_token
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
    if not _cache_entry_is_reusable(
        cached_entry=cached_entry,
        fact_packet=fact_packet,
        now_utc=dt.datetime.now(tz=dt.timezone.utc),
    ):
        return False
    return _validated_cached_sections(
        raw_sections=cached_entry.get("sections", []),
        fact_packet=fact_packet,
        cached_evidence_lookup=cached_entry.get("evidence_lookup", {}),
    ) is not None


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
    if token == "composed":
        return "composed"
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
    fact_packet: Mapping[str, Any],
    cache_mode: str,
    notice: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    raw_sections = cached_entry.get("sections")
    if not isinstance(raw_sections, Sequence) or not raw_sections:
        return None
    sections = _validated_cached_sections(
        raw_sections=raw_sections,
        fact_packet=fact_packet,
        cached_evidence_lookup=cached_entry.get("evidence_lookup", {}),
    )
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


def _persist_current_cache_entry(
    *,
    repo_root: Path,
    cache_entries: dict[str, Any],
    fingerprint: str,
    generated_utc: str,
    sections: Sequence[Mapping[str, Any]],
    fact_packet: Mapping[str, Any],
) -> None:
    cache_entries[fingerprint] = {
        "generated_utc": str(generated_utc).strip(),
        "sections": [dict(item) for item in sections if isinstance(item, Mapping)],
        "evidence_lookup": _brief_evidence_lookup(fact_packet=fact_packet),
        "context": _cache_context(fact_packet=fact_packet),
    }
    _write_cache(
        repo_root=repo_root,
        payload={
            "version": STANDUP_BRIEF_SCHEMA_VERSION,
            "entries": cache_entries,
        },
    )


def _legacy_cache_ready_brief_if_reusable(
    *,
    repo_root: Path,
    cache_entries: dict[str, Any],
    fingerprint: str,
    fact_packet: Mapping[str, Any],
    generated_utc: str,
) -> dict[str, Any] | None:
    for path in _legacy_cache_paths(repo_root=repo_root):
        for entry in _load_cache_entries_from_path(path).values():
            if not isinstance(entry, Mapping):
                continue
            if not _cache_entry_matches_context(cached_entry=entry, fact_packet=fact_packet):
                continue
            raw_sections = entry.get("sections")
            if not isinstance(raw_sections, Sequence) or not raw_sections:
                continue
            sections = _validated_cached_sections(
                raw_sections=raw_sections,
                fact_packet=fact_packet,
                cached_evidence_lookup=entry.get("evidence_lookup", {}),
            )
            if not sections:
                continue
            _persist_current_cache_entry(
                repo_root=repo_root,
                cache_entries=cache_entries,
                fingerprint=fingerprint,
                generated_utc=generated_utc,
                sections=sections,
                fact_packet=fact_packet,
            )
            return _ready_brief(
                source="cache",
                fingerprint=fingerprint,
                generated_utc=generated_utc,
                sections=sections,
                evidence_lookup=_brief_evidence_lookup(fact_packet=fact_packet),
                cache_mode="exact",
            )
    return None


def _context_cache_ready_brief_if_reusable(
    *,
    repo_root: Path,
    cache_entries: Mapping[str, Any],
    fingerprint: str,
    fact_packet: Mapping[str, Any],
    generated_utc: str,
) -> dict[str, Any] | None:
    context = _cache_context(fact_packet=fact_packet)
    now_utc = dt.datetime.now(tz=dt.timezone.utc)
    best_sections: list[dict[str, Any]] | None = None
    best_generated_utc = ""
    best_generated_dt: dt.datetime | None = None
    mutable_entries = {
        str(key).strip(): dict(value)
        for key, value in cache_entries.items()
        if str(key).strip() and isinstance(value, Mapping)
    }
    candidate_entry_sets: list[Mapping[str, Any]] = [mutable_entries]
    if context["scope_mode"] == "global":
        candidate_entry_sets.extend(
            _load_cache_entries_from_path(path)
            for path in _legacy_cache_paths(repo_root=repo_root)
        )

    for entry_set in candidate_entry_sets:
        for candidate_fingerprint, entry in entry_set.items():
            if candidate_fingerprint == fingerprint and context["scope_mode"] == "scoped":
                continue
            if not isinstance(entry, Mapping):
                continue
            if not _cache_entry_matches_context(cached_entry=entry, fact_packet=fact_packet):
                continue
            if not _cache_entry_within_context_age_limit(
                cached_entry=entry,
                now_utc=now_utc,
            ):
                continue
            raw_sections = entry.get("sections")
            if not isinstance(raw_sections, Sequence) or not raw_sections:
                continue
            sections = _validated_cached_sections(
                raw_sections=raw_sections,
                fact_packet=fact_packet,
                cached_evidence_lookup=entry.get("evidence_lookup", {}),
            )
            if not sections:
                continue
            candidate_generated_utc = str(entry.get("generated_utc", "")).strip()
            candidate_generated_dt = _parse_iso_datetime(candidate_generated_utc)
            if best_sections is not None:
                if candidate_generated_dt is None:
                    continue
                if best_generated_dt is not None and candidate_generated_dt <= best_generated_dt:
                    continue
            best_sections = sections
            best_generated_utc = candidate_generated_utc
            best_generated_dt = candidate_generated_dt
    if not best_sections:
        return None
    _persist_current_cache_entry(
        repo_root=repo_root,
        cache_entries=mutable_entries,
        fingerprint=fingerprint,
        generated_utc=generated_utc,
        sections=best_sections,
        fact_packet=fact_packet,
    )
    return _ready_brief(
        source="cache",
        fingerprint=fingerprint,
        generated_utc=generated_utc,
        sections=best_sections,
        evidence_lookup=_brief_evidence_lookup(fact_packet=fact_packet),
        cache_mode="exact",
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
        fact_packet=fact_packet,
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
        fact_packet=fact_packet,
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
    sections = _deterministic_sections(fact_packet=fact_packet)
    validated_sections, errors = _validate_brief_response(
        response={"sections": sections},
        fact_packet=fact_packet,
    )
    if not errors and validated_sections:
        sections = validated_sections
    return _ready_brief(
        source="deterministic",
        fingerprint=fingerprint,
        generated_utc=generated_utc,
        sections=sections,
        evidence_lookup=_brief_evidence_lookup(fact_packet=fact_packet),
        notice=_deterministic_fallback_notice(reason=reason),
    )


def _composed_ready_brief(
    *,
    fact_packet: Mapping[str, Any],
    fingerprint: str,
    generated_utc: str,
) -> dict[str, Any]:
    sections = _deterministic_sections(fact_packet=fact_packet)
    validated_sections, errors = _validate_brief_response(
        response={"sections": sections},
        fact_packet=fact_packet,
    )
    if not errors and validated_sections:
        sections = validated_sections
    return _ready_brief(
        source="composed",
        fingerprint=fingerprint,
        generated_utc=generated_utc,
        sections=sections,
        evidence_lookup=_brief_evidence_lookup(fact_packet=fact_packet),
    )


def _unavailable_brief_message(reason: str) -> str:
    token = str(reason or "").strip().lower()
    if token == "provider_deferred":
        return "Compass kept the cheap refresh path here, so this brief stayed on cache or deterministic coverage instead of buying a fresh live narration call."
    if token == "provider_unavailable":
        return "Compass could not reach a live narration provider and no exact current-packet brief was available."
    if token == "provider_empty":
        return "Compass did not receive a structured AI brief and no exact current-packet brief was available."
    if token == "validation_failed":
        return "Compass received an invalid AI brief and no exact current-packet brief was available."
    return "Compass could not build a current standup brief for this packet."


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


def _normalized_fact_text_for_reuse(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(text or "").lower())
    return " ".join(normalized.split()).strip()


def _remap_cached_fact_id_for_current_packet(
    *,
    fact_id: str,
    section_fact_ids: set[str],
    section_kind_ids: Mapping[str, set[str]],
    fact_lookup: Mapping[str, Mapping[str, Any]],
    cached_evidence_lookup: Mapping[str, Mapping[str, Any]] | None = None,
) -> str:
    evidence_entry = (
        cached_evidence_lookup.get(fact_id)
        if isinstance(cached_evidence_lookup, Mapping) and isinstance(cached_evidence_lookup.get(fact_id), Mapping)
        else {}
    )
    if not evidence_entry:
        return ""
    cached_kind = str(evidence_entry.get("kind", "")).strip()
    candidate_ids = (
        sorted(section_kind_ids.get(cached_kind, set()))
        if cached_kind and section_kind_ids.get(cached_kind)
        else sorted(section_fact_ids)
    )
    if len(candidate_ids) == 1:
        return candidate_ids[0]

    cached_text = _normalized_fact_text_for_reuse(str(evidence_entry.get("text", "")).strip())
    if not cached_text:
        return ""

    exact_matches = [
        candidate_id
        for candidate_id in candidate_ids
        if _normalized_fact_text_for_reuse(str(fact_lookup.get(candidate_id, {}).get("text", "")).strip()) == cached_text
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]

    scored = sorted(
        (
            (
                difflib.SequenceMatcher(
                    None,
                    cached_text,
                    _normalized_fact_text_for_reuse(str(fact_lookup.get(candidate_id, {}).get("text", "")).strip()),
                ).ratio(),
                candidate_id,
            )
            for candidate_id in candidate_ids
        ),
        reverse=True,
    )
    if not scored or scored[0][0] < 0.78:
        return ""
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    if scored[0][0] - runner_up < 0.08:
        return ""
    return scored[0][1]


def _validated_cached_sections(
    *,
    raw_sections: Sequence[Mapping[str, Any]],
    fact_packet: Mapping[str, Any],
    cached_evidence_lookup: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]] | None:
    current_window_coverage_text = ""
    for fact in _section_facts(fact_packet=fact_packet, section_key="current_execution"):
        if str(fact.get("kind", "")).strip() == "window_coverage":
            current_window_coverage_text = _global_window_coverage_bullet_text(
                fact_text=str(fact.get("text", "")).strip()
            )
            break
    normalized_sections: list[dict[str, Any]] = []
    for item in raw_sections:
        if not isinstance(item, Mapping):
            continue
        section = dict(item)
        if (
            current_window_coverage_text
            and str(section.get("key", "")).strip() == "current_execution"
            and isinstance(section.get("bullets"), Sequence)
        ):
            rewritten_bullets: list[dict[str, Any]] = []
            for bullet in section.get("bullets", []):
                if not isinstance(bullet, Mapping):
                    continue
                bullet_row = dict(bullet)
                text = str(bullet_row.get("text", "")).strip()
                if text.startswith("Most of the movement this window sat in ") or text.startswith(
                    "A lot happened, but most of it came through "
                ):
                    bullet_row["text"] = current_window_coverage_text
                rewritten_bullets.append(bullet_row)
            section["bullets"] = rewritten_bullets
        normalized_sections.append(section)
    response = {
        "sections": normalized_sections,
    }
    sections, errors = _validate_brief_response(
        response=response,
        fact_packet=fact_packet,
        cached_evidence_lookup=cached_evidence_lookup,
    )
    if not errors and sections:
        return sections
    salvaged = _salvage_cached_sections(
        raw_sections=normalized_sections,
        fact_packet=fact_packet,
        cached_evidence_lookup=cached_evidence_lookup,
        validation_errors=errors,
    )
    if salvaged:
        return salvaged
    return None


def _recoverable_cached_section_keys(*, validation_errors: Sequence[str]) -> set[str]:
    recoverable: set[str] = set()
    for error in validation_errors:
        message = str(error).strip()
        if message == "Current execution must cite freshness evidence when the fact packet is aging or stale":
            recoverable.add("current_execution")
            continue
        match = re.match(r"^section\s+([a-z_]+)\s+bullet\s+\d+\s+", message)
        if not match:
            return set()
        section_key = str(match.group(1)).strip()
        if message.endswith("drifts away from the cited fact language") or message.endswith(
            "falls into portable summary cadence"
        ) or message.endswith(
            "leans on stagey metaphor instead of plainspoken maintainer language"
        ) or message.endswith(
            "slides back into dashboard-polished summary language"
        ) or message.endswith(
            "reuses cached stock phrasing instead of plainspoken maintainer narration"
        ) or message.endswith(
            "leads with counts-only telemetry"
        ):
            recoverable.add(section_key)
            continue
        return set()
    return recoverable


def _salvage_cached_sections(
    *,
    raw_sections: Sequence[Mapping[str, Any]],
    fact_packet: Mapping[str, Any],
    cached_evidence_lookup: Mapping[str, Mapping[str, Any]] | None = None,
    validation_errors: Sequence[str],
) -> list[dict[str, Any]] | None:
    recoverable_section_keys = _recoverable_cached_section_keys(validation_errors=validation_errors)
    if not recoverable_section_keys:
        return None
    deterministic_sections = compass_standup_brief_deterministic.build_sections(
        fact_packet=fact_packet,
        section_specs=STANDUP_BRIEF_SECTIONS,
    )
    deterministic_by_key = {
        str(section.get("key", "")).strip(): dict(section)
        for section in deterministic_sections
        if isinstance(section, Mapping) and str(section.get("key", "")).strip()
    }
    salvaged_sections: list[dict[str, Any]] = []
    for section in raw_sections:
        if not isinstance(section, Mapping):
            continue
        key = str(section.get("key", "")).strip()
        if key in recoverable_section_keys and key in deterministic_by_key:
            salvaged_sections.append(dict(deterministic_by_key[key]))
        else:
            salvaged_sections.append(dict(section))
    sections, errors = _validate_brief_response(
        response={"sections": salvaged_sections},
        fact_packet=fact_packet,
        cached_evidence_lookup=cached_evidence_lookup,
    )
    if errors or not sections:
        return None
    return sections


def _global_window_coverage_bullet_text(*, fact_text: str) -> str:
    text = " ".join(str(fact_text or "").split()).strip()
    if not text:
        return ""
    detail = text.split("Window coverage:", 1)[1].strip() if "Window coverage:" in text else text
    if detail.startswith("A lot moved in this window."):
        remainder = detail.split(".", 1)[1].strip() if "." in detail else ""
        remainder = re.sub(r"\s*carried most of it\.?$", "", remainder, flags=re.IGNORECASE).strip()
        if remainder:
            return f"Most of the work here was in {remainder}."
    if detail.startswith("Work moved across ") and ":" in detail:
        remainder = detail.split(":", 1)[1].strip()
        if remainder:
            return f"Most of the work here was in {remainder.rstrip('.')}."
    if detail.startswith("Most of the movement this window sat in "):
        remainder = detail.split("Most of the movement this window sat in ", 1)[1].strip()
        if remainder:
            return f"Most of the work here was in {remainder.rstrip('.')}."
    return detail.rstrip(".")


def _validate_brief_response(
    *,
    response: Mapping[str, Any],
    fact_packet: Mapping[str, Any],
    cached_evidence_lookup: Mapping[str, Mapping[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    fact_lookup = _fact_lookup(fact_packet)
    fact_ids_by_section = _fact_ids_by_section(fact_lookup)
    fact_ids_by_section_and_kind = _fact_ids_by_section_and_kind(fact_lookup)
    freshness_bucket = _fact_packet_freshness_bucket(fact_packet=fact_packet)
    scope_mapping = fact_packet.get("scope") if isinstance(fact_packet.get("scope"), Mapping) else {}
    scope_mode = str(scope_mapping.get("mode", "")).strip().lower()
    sections = response.get("sections")
    if not isinstance(sections, Sequence):
        return [], ["provider response omitted the sections array"]
    normalized_sections: list[dict[str, Any]] = []
    if len(sections) != len(STANDUP_BRIEF_SECTIONS):
        errors.append("provider response did not return the required four-section brief")
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
        section_cited_fact_ids: set[str] = set()
        max_bullets = 2
        if key == "current_execution":
            max_bullets = 4
        elif key == "risks_to_watch":
            max_bullets = 3
        if len(raw_bullets) > max_bullets:
            errors.append(f"section {key} exceeded the bullet cap")
        for bullet_index, bullet in enumerate(raw_bullets, start=1):
            if not isinstance(bullet, Mapping):
                errors.append(f"section {key} bullet {bullet_index} is malformed")
                continue
            text = _strip_inline_fact_id_markers(" ".join(str(bullet.get("text", "")).split()).strip())
            fact_ids = bullet.get("fact_ids")
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
            if _NEGATED_COMPLETED_LEAD_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} uses an absence-first lead instead of movement")
            if _OVERUSED_STOCK_LEAD_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} reuses an overused stock lead")
            if _ATTENTION_PRIORITY_LEAD_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} reuses an overused attention-lead pattern")
            if _GENERIC_PRIORITY_WRAPPER_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} reuses a generic priority wrapper")
            if _GENERIC_SIGNAL_LEAD_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} reuses a generic signal wrapper")
            if _GENERIC_POSTURE_SLOGAN_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} reuses a generic posture slogan")
            if _GENERIC_NEXT_STEP_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} reuses a generic next-step wrapper")
            if _GENERIC_PROGRESS_SLOGAN_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} reuses canned progress phrasing")
            if _GENERIC_LANE_WRAPPER_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} reuses a generic lane wrapper")
            if _GENERIC_WINDOW_LEAD_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} reuses a generic window lead")
            if _GENERIC_TIMING_WRAPPER_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} reuses a generic timing wrapper")
            if _GENERIC_BENCHMARK_CHALLENGE_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} reuses a rhetorical benchmark challenge")
            if _INTERNAL_TEMPLATE_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} reuses an internal stock template")
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
                        remapped_fact_id = _remap_cached_fact_id_for_current_packet(
                            fact_id=token,
                            section_fact_ids=section_fact_ids,
                            section_kind_ids=section_kind_ids,
                            fact_lookup=fact_lookup,
                            cached_evidence_lookup=cached_evidence_lookup,
                        )
                        if not remapped_fact_id:
                            errors.append(f"section {key} bullet {bullet_index} cited unknown fact id {token}")
                            continue
                        token = remapped_fact_id
                    normalized_fact_ids.append(token)
                    if token in section_fact_ids:
                        local_fact_ids.append(token)
                        section_cited_fact_ids.add(token)
            cited_fact_texts = [
                str(fact_lookup[fact_id].get("text", "")).strip()
                for fact_id in (local_fact_ids or normalized_fact_ids)
                if fact_id in fact_lookup and str(fact_lookup[fact_id].get("text", "")).strip()
            ]
            errors.extend(
                compass_standup_brief_voice_validation.bullet_shape_errors(
                    section_key=key,
                    bullet_index=bullet_index,
                    text=text,
                    fact_texts=cited_fact_texts,
                )
            )
            if normalized_fact_ids and not local_fact_ids:
                errors.append(f"section {key} bullet {bullet_index} did not cite a section-local fact")
            bullets.append(
                {
                    "text": text,
                    "_fact_ids": local_fact_ids or normalized_fact_ids,
                }
            )
        if key == "current_execution":
            direction_ids = section_kind_ids.get("direction", set())
            if direction_ids and not (section_cited_fact_ids & direction_ids):
                errors.append("Current execution must cite direction evidence")
            window_coverage_ids = section_kind_ids.get("window_coverage", set())
            if (
                scope_mode == "global"
                and window_coverage_ids
                and not (section_cited_fact_ids & window_coverage_ids)
            ):
                coverage_fact_id = next(iter(sorted(window_coverage_ids)))
                coverage_fact_text = str(fact_lookup.get(coverage_fact_id, {}).get("text", "")).strip()
                coverage_text = _global_window_coverage_bullet_text(fact_text=coverage_fact_text)
                if coverage_text:
                    coverage_bullet = {
                        "text": coverage_text,
                        "_fact_ids": [coverage_fact_id],
                    }
                    if len(bullets) >= max_bullets:
                        bullets = bullets[: max_bullets - 1] + [coverage_bullet]
                    else:
                        bullets.append(coverage_bullet)
                    section_cited_fact_ids.add(coverage_fact_id)
                else:
                    errors.append("Current execution must cite whole-window coverage evidence for global scope")
            freshness_ids = section_kind_ids.get("freshness", set())
            if (
                freshness_bucket in {"aging", "stale"}
                and freshness_ids
                and not (section_cited_fact_ids & freshness_ids)
            ):
                errors.append("Current execution must cite freshness evidence when the fact packet is aging or stale")
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
                        "text": str(item.get("text", "")).strip(),
                        "fact_ids": list(item.get("_fact_ids", [])),
                    }
                    for item in bullets
                    if str(item.get("text", "")).strip()
                ],
            }
        )
    errors.extend(compass_standup_brief_voice_validation.brief_shape_errors(sections=normalized_sections))
    return normalized_sections, errors


def _provider_request(
    *,
    fact_packet: Mapping[str, Any],
    compact_retry: bool = False,
    config: odylith_reasoning.ReasoningConfig | None = None,
) -> odylith_reasoning.StructuredReasoningRequest:
    profile = _provider_request_profile(config=config)
    return odylith_reasoning.StructuredReasoningRequest(
        system_prompt=_provider_system_prompt(compact_retry=compact_retry),
        schema_name="compass_standup_brief_compact_retry" if compact_retry else "compass_standup_brief",
        output_schema=_provider_output_schema(),
        prompt_payload=_provider_request_payload(fact_packet=fact_packet, compact_retry=compact_retry),
        model=profile.model,
        reasoning_effort=profile.reasoning_effort,
        timeout_seconds=_COMPASS_PROVIDER_TIMEOUT_SECONDS,
    )


def _repair_provider_request(
    *,
    fact_packet: Mapping[str, Any],
    invalid_response: Mapping[str, Any],
    validation_errors: Sequence[str],
    config: odylith_reasoning.ReasoningConfig | None = None,
) -> odylith_reasoning.StructuredReasoningRequest:
    profile = _provider_request_profile(config=config)
    return odylith_reasoning.StructuredReasoningRequest(
        system_prompt=_repair_provider_system_prompt(),
        schema_name="compass_standup_brief_repair",
        output_schema=_provider_output_schema(),
        prompt_payload=_repair_provider_request_payload(
            fact_packet=fact_packet,
            invalid_response=invalid_response,
            validation_errors=validation_errors,
        ),
        model=profile.model,
        reasoning_effort=profile.reasoning_effort,
        timeout_seconds=_COMPASS_PROVIDER_TIMEOUT_SECONDS,
    )


def _request_provider_with_empty_retry(
    *,
    provider: odylith_reasoning.ReasoningProvider,
    request: odylith_reasoning.StructuredReasoningRequest | None = None,
    requests: Sequence[odylith_reasoning.StructuredReasoningRequest] | None = None,
    max_attempts: int = _EMPTY_PROVIDER_MAX_ATTEMPTS,
) -> Mapping[str, Any] | None:
    """Retry one-shot empty provider replies before failing closed.

    Compass standup already treats invalid structured replies as a separate
    validation/repair path. This helper hardens only the narrower transient case
    where the provider returns no structured payload at all even though the same
    request may succeed on an immediate rerun.
    """

    if requests is not None:
        request_sequence = [item for item in requests if item is not None]
    elif request is not None:
        request_sequence = [request]
    else:
        request_sequence = []
    attempts = max(1, int(max_attempts))
    if not request_sequence:
        return None
    if len(request_sequence) < attempts:
        request_sequence.extend([request_sequence[-1]] * (attempts - len(request_sequence)))
    for retry_request in request_sequence[:attempts]:
        result = provider.generate_structured(request=retry_request)
        if isinstance(result, Mapping):
            return result
    return None


def _provider_requests_for_empty_retry(
    *,
    fact_packet: Mapping[str, Any],
    config: odylith_reasoning.ReasoningConfig | None = None,
) -> list[odylith_reasoning.StructuredReasoningRequest]:
    return [
        _provider_request(fact_packet=fact_packet, compact_retry=False, config=config),
        _provider_request(fact_packet=fact_packet, compact_retry=True, config=config),
    ]


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
    allow_legacy_cache_recovery: bool = True,
    allow_deterministic_fallback: bool = True,
    allow_composed_fallback: bool = False,
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
        (not prefer_provider or not allow_provider)
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
            fact_packet=fact_packet,
            cache_mode="exact",
        )
        if cached_ready is not None:
            return cached_ready
    if not prefer_provider or not allow_provider:
        context_cached_ready = _context_cache_ready_brief_if_reusable(
            repo_root=repo_root,
            cache_entries=cache_entries,
            fingerprint=fingerprint,
            fact_packet=fact_packet,
            generated_utc=generated_utc,
        )
        if context_cached_ready is not None:
            return context_cached_ready
    if allow_legacy_cache_recovery:
        legacy_ready = _legacy_cache_ready_brief_if_reusable(
            repo_root=repo_root,
            cache_entries=cache_entries,
            fingerprint=fingerprint,
            fact_packet=fact_packet,
            generated_utc=generated_utc,
        )
        if legacy_ready is not None:
            return legacy_ready

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
        if allow_composed_fallback:
            return _composed_ready_brief(
                fact_packet=fact_packet,
                fingerprint=fingerprint,
                generated_utc=generated_utc,
            )
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
        if allow_composed_fallback:
            return _composed_ready_brief(
                fact_packet=fact_packet,
                fingerprint=fingerprint,
                generated_utc=generated_utc,
            )
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
        requests=_provider_requests_for_empty_retry(
            fact_packet=fact_packet,
            config=resolved_config,
        ),
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
        if allow_composed_fallback:
            return _composed_ready_brief(
                fact_packet=fact_packet,
                fingerprint=fingerprint,
                generated_utc=generated_utc,
            )
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
                config=resolved_config,
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
            if allow_composed_fallback:
                return _composed_ready_brief(
                    fact_packet=fact_packet,
                    fingerprint=fingerprint,
                    generated_utc=generated_utc,
                )
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
                text = " ".join(str(item.get("text", "")).split()).strip()
                if not text:
                    continue
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
