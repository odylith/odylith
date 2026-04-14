"""Compass standup brief narrator and exact-substrate cache.

Compass runtime remains authoritative for fact selection, evidence ranking, and
fingerprinting. This module owns the bounded narration layer:

- reuse the shared Odylith reasoning provider configuration and adapters;
- request a fixed four-section standup brief with schema-constrained output;
- validate the reply against the deterministic fact packet and UI contract;
- cache validated results by exact narration-substrate fingerprint; and
- replay only exact same-packet narration when live AI narration is not
  available.
"""

from __future__ import annotations

import datetime as dt
import difflib
from dataclasses import replace
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.surfaces import compass_standup_brief_substrate
from odylith.runtime.surfaces import compass_standup_brief_voice_validation


STANDUP_BRIEF_SCHEMA_VERSION = "v25"
STANDUP_BRIEF_CACHE_PATH = ".odylith/compass/standup-brief-cache.v25.json"
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
    r"^\s*(?:[A-Z][A-Za-z0-9`'’(),/\- ]{4,90}\s+comes\s+next\s+because|"
    r"(?:`?B-\d+`?|[A-Z][A-Za-z0-9`'’(),/\- ]{4,90})\s+is\s+next\s*:|"
    r"the\s+next\s+move\s+is\b|next\s+up\s+is\b|then\b)",
    re.IGNORECASE,
)
_GENERIC_RISK_WRAPPER_RE = re.compile(
    r"^\s*(?:a\s+p\d+\s+blocker\s+is\s+still\s+open\s*:|primary\s+blocker\s+is\s+still\s+open\s*:)",
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
_GENERIC_COVERAGE_ROLLCALL_RE = re.compile(
    r"^\s*(?:most\s+of\s+the\s+work\s+here\s+was\s+in|"
    r"most\s+of\s+the\s+movement\s+this\s+window\s+sat\s+in|"
    r"a\s+lot\s+happened,\s+but\s+most\s+of\s+it\s+came\s+through)\b",
    re.IGNORECASE,
)
_GENERIC_LINKAGE_WRAPPER_RE = re.compile(
    r"\bare\s+still\s+moving\s+together\b",
    re.IGNORECASE,
)
_GENERIC_EXISTENCE_BECAUSE_RE = re.compile(
    r"^\s*(?:`?B-\d+`?|[A-Za-z][A-Za-z0-9`'’(),/\- ]{0,90})\s+is\s+there\s+because\b",
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
_WORKSTREAM_TOKEN_RE = re.compile(r"\bB-\d{3,}\b")
_VOLATILE_FRESHNESS_TEXT_RE = re.compile(r"^Freshness signal is (?:aging|stale):", re.IGNORECASE)
_MAX_BULLET_WORDS = 48
_EMPTY_PROVIDER_MAX_ATTEMPTS = 2
_COMPASS_PROVIDER_TIMEOUT_SECONDS = 60.0
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
_VALID_FRESHNESS_BUCKETS = {"live", "recent", "aging", "stale", "unknown"}
_CLAUDE_COMPASS_NARRATION_MODEL = "claude-haiku-4-5"


def _default_compass_reasoning_config() -> odylith_reasoning.ReasoningConfig:
    return odylith_reasoning.ReasoningConfig(
        mode="auto",
        provider="auto-local",
        model=_CLAUDE_COMPASS_NARRATION_MODEL,
        base_url="",
        api_key="",
        scope_cap=5,
        timeout_seconds=_COMPASS_PROVIDER_TIMEOUT_SECONDS,
        codex_bin="codex",
        codex_reasoning_effort="medium",
        claude_bin="claude",
        claude_reasoning_effort="low",
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
    """Return the stable fingerprint for the exact deterministic narration substrate."""

    substrate = compass_standup_brief_substrate.build_narration_substrate(
        fact_packet=fact_packet,
        schema_version=STANDUP_BRIEF_SCHEMA_VERSION,
    )
    return str(substrate.get("fingerprint", "")).strip()


def _narration_substrate(
    *,
    fact_packet: Mapping[str, Any],
    previous_substrate: Mapping[str, Any] | None = None,
    previous_brief: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return compass_standup_brief_substrate.build_narration_substrate(
        fact_packet=fact_packet,
        previous_substrate=previous_substrate,
        previous_brief=previous_brief,
        schema_version=STANDUP_BRIEF_SCHEMA_VERSION,
    )


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


def _fact_packet_freshness_bucket(*, fact_packet: Mapping[str, Any]) -> str:
    summary = fact_packet.get("summary")
    if not isinstance(summary, Mapping):
        return "unknown"
    freshness = summary.get("freshness")
    if not isinstance(freshness, Mapping):
        return "unknown"
    bucket = str(freshness.get("bucket", "")).strip().lower()
    if bucket in _VALID_FRESHNESS_BUCKETS:
        return bucket
    return "unknown"


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


def _provider_system_prompt(*, compact_retry: bool = False) -> str:
    prompt = (
        "You are Compass, the governed standup narrator. "
        "Write a concise four-section standup brief from the supplied fact packet only. "
        "Sound like a thoughtful maintainer talking to a teammate: friendly, calm, direct, simple, factual, precise, and human. "
        "Use short plain sentences first. Carry judgment without sounding grand. "
        "Celebrate real wins with restraint. When things are shaky, be steady and reassuring without softening the truth. "
        "Name what changed, why it matters, what is next, and what could still break. "
        "Keep the 24h and 48h views in the same live spoken voice; 48h widens the evidence, not the personality. "
        "Do not sound like a dashboard, status bot, executive memo, or polished management summary. "
        "Do not force workstream roll calls just to prove coverage. Name only the lanes that help the reader understand the window, and let the evidence carry the rest. "
        "Do not use stock framing, repeated house phrases, stagey metaphor, or canned wrappers such as "
        "'Most of the work here was in', 'X and Y are still moving together', 'X is there because', "
        "'The next move is', 'Next up is', or repeated 'Over the last 48 hours' leads. "
        "Use only the supplied fact packet and cited fact ids. "
        "Do not print raw fact ids in prose; cite only supplied fact ids in fact_ids. "
        "Keep section order and labels exactly as provided."
    )
    if compact_retry:
        return prompt + " Keep the bullets especially tight, but preserve the same human voice."
    return prompt


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
    provider_view = compass_standup_brief_substrate.provider_substrate_view(
        substrate=_narration_substrate(fact_packet=fact_packet)
    )
    if not compact_retry:
        return provider_view
    fact_limits = _COMPACT_RETRY_PROVIDER_FACT_LIMITS_BY_SECTION
    compact_sections: list[dict[str, Any]] = []
    for row in provider_view.get("sections", []):
        if not isinstance(row, Mapping):
            continue
        section_key = str(row.get("key", "")).strip()
        limit = int(fact_limits.get(section_key, 1) or 1)
        compact_sections.append(
            {
                **dict(row),
                "facts": [
                    dict(item)
                    for item in (row.get("facts", []) if isinstance(row.get("facts"), Sequence) else [])[:limit]
                    if isinstance(item, Mapping)
                ],
            }
        )
    return {
        **provider_view,
        "sections": compact_sections,
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
                "Say what is actively being worked and why it deserves attention now. Keep it concrete, simple, and tied to the cited proof."
            )
        elif key == "risks_to_watch":
            contract["max_bullets"] = 3
            contract["objective"] = "Name the seam to watch, what could drift, or what still feels fragile. Stay calm, clear, and factual."
        elif key == "completed":
            contract["objective"] = (
                "Say what actually landed. Quietly celebrate real wins when they matter, and explain why the landing changed the room only if it helps orientation."
            )
        elif key == "next_planned":
            contract["objective"] = "Say what is next and why it is next in plain language."
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
                "celebration": [
                    "Good one to get over the line: the first-turn bootstrap work closed cleanly, and that takes one old loose end off the board.",
                ],
                "reassurance": [
                    "Small but real reassurance: the repo is still on the pinned dogfood path maintainers are meant to trust.",
                ],
                "steady_risk": [
                    "This is the seam to watch. If the browser checks still miss drift, Compass will keep sounding more certain than it should.",
                ],
                "slow_window": [
                    "Not a big movement window. The same fragile edge is still the one asking for care.",
                ],
            },
            "writing_contract": {
                "target_style": "friendly grounded maintainer narration",
                "max_words_per_bullet": _MAX_BULLET_WORDS,
                "rules": [
                    "sound like a thoughtful maintainer talking to a teammate",
                    "use short plain sentences first",
                    "be friendly, calm, direct, factual, and precise",
                    "say what changed, why it matters, what is next, or what could still break",
                    "celebrate real wins with restraint",
                    "when things are shaky, be steady and reassuring without hiding the truth",
                    "keep 24h and 48h in the same live spoken maintainer register; only the evidence window widens",
                    "do not write in first-person singular",
                    "use ordinary words another maintainer can understand on first read",
                    "show humane judgment without sounding grand, polished, or performed",
                    "name only the lanes that help the reader understand the window instead of forcing a workstream roll call",
                    "carry consequence inside the relevant bullet instead of splitting it into a dedicated explanation section",
                    "prefer observed movement, friction, proof, or risk over portfolio umbrella language",
                    "keep each bullet visibly tethered to the cited fact language",
                    "if the cited facts disappear and the bullet still sounds plausible, it is too generic for Compass",
                    "if a tired maintainer would have to reread the sentence, rewrite it more simply",
                    "treat plan closure as proof that a change landed; do not write the bullet as an administrative plan-status update",
                    "do not lead bullets by restating long workstream titles or queue labels",
                    "do not use absence-plus-compensation leads like 'no milestone closed ..., but ...' when movement facts exist",
                    "do not write next-step bullets as 'X comes next because', 'The next move is', or start follow-ons with 'Then'",
                    "do not write bullets as 'Next up is', 'What matters here is', 'Most of the work here was in', 'X and Y are still moving together', or 'X is there because'",
                    "do not keep reopening bullets with repeated 'Over the last 48 hours' or similar window labels",
                    "do not paraphrase packet bookkeeping such as plan closeouts, repo pins, product claims, tracked corpus coverage, or governance seams as if they were the story itself",
                    "do not turn plan posture, checklist counts, timeline signals, or closure-discipline warnings into the headline unless the fact packet gives no more concrete movement",
                    "do not use stock timing wrappers, rhetorical tests, stagey metaphors, or dashboard-wise abstractions",
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
                    "Most of the work here was in",
                    "X and Y are still moving together",
                    "X is there because",
                    "the next move is",
                    "Next up is",
                    "Over the last 48 hours",
                    "pressure point",
                    "center of gravity",
                    "slippery",
                ],
                "overused_stock_leads": [
                    "Most of the work here was in",
                    "X and Y are still moving together",
                    "X is there because",
                    "The next move is",
                    "Next up is",
                    "What matters here is",
                    "Over the last 48 hours,",
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
            "substrate_fingerprint": str(brief.get("substrate_fingerprint", "")).strip() or fingerprint,
            "bundle_fingerprint": str(brief.get("bundle_fingerprint", "")).strip(),
            "last_successful_narration_fingerprint": (
                str(brief.get("last_successful_narration_fingerprint", "")).strip() or fingerprint
            ),
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


def latest_cached_entry_for_context(
    *,
    repo_root: Path,
    fact_packet: Mapping[str, Any],
) -> dict[str, Any] | None:
    entries = _load_cache(repo_root=repo_root).get("entries", {})
    if not isinstance(entries, Mapping):
        return None
    target_context = _cache_context(fact_packet=fact_packet)
    winner: dict[str, Any] | None = None
    winner_generated_utc = ""
    for fingerprint, entry in entries.items():
        if not str(fingerprint).strip() or not isinstance(entry, Mapping):
            continue
        context = entry.get("context")
        if not isinstance(context, Mapping):
            continue
        if (
            str(context.get("window", "")).strip() != str(target_context.get("window", "")).strip()
            or str(context.get("scope_mode", "")).strip() != str(target_context.get("scope_mode", "")).strip()
            or str(context.get("scope_id", "")).strip() != str(target_context.get("scope_id", "")).strip()
        ):
            continue
        generated_utc = str(entry.get("generated_utc", "")).strip()
        if generated_utc >= winner_generated_utc:
            winner_generated_utc = generated_utc
            winner = {"fingerprint": str(fingerprint).strip(), **dict(entry)}
    return winner


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
            "Install or expose a supported local reasoning host in this environment before refreshing Compass."
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
    substrate_fingerprint: str = "",
    bundle_fingerprint: str = "",
    provider_decision: str = "",
    last_successful_narration_fingerprint: str = "",
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
        "substrate_fingerprint": str(substrate_fingerprint or fingerprint).strip() or str(fingerprint).strip(),
        "bundle_fingerprint": str(bundle_fingerprint).strip(),
        "provider_decision": str(provider_decision).strip().lower()
        or ("cache_reuse" if _brief_source_label(source=source) == "cache" else "provider_called"),
        "last_successful_narration_fingerprint": (
            str(last_successful_narration_fingerprint or substrate_fingerprint or fingerprint).strip()
        ),
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
        substrate_fingerprint=str(cached_entry.get("substrate_fingerprint", "")).strip() or fingerprint,
        bundle_fingerprint=str(cached_entry.get("bundle_fingerprint", "")).strip(),
        provider_decision="cache_reuse",
        last_successful_narration_fingerprint=(
            str(cached_entry.get("last_successful_narration_fingerprint", "")).strip() or fingerprint
        ),
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
        "substrate_fingerprint": fingerprint,
        "last_successful_narration_fingerprint": fingerprint,
        "substrate": _narration_substrate(fact_packet=fact_packet),
    }
    _write_cache(
        repo_root=repo_root,
        payload={
            "version": STANDUP_BRIEF_SCHEMA_VERSION,
            "entries": cache_entries,
        },
    )


def _unavailable_brief(
    *,
    fingerprint: str,
    attempted_utc: str,
    diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": STANDUP_BRIEF_SCHEMA_VERSION,
        "status": "unavailable",
        "source": "unavailable",
        "fingerprint": fingerprint,
        "substrate_fingerprint": str(fingerprint).strip(),
        "bundle_fingerprint": "",
        "provider_decision": str(dict(diagnostics).get("provider_decision", "")).strip().lower() or "unavailable",
        "last_successful_narration_fingerprint": "",
        "generated_utc": "",
        "diagnostics": {
            **dict(diagnostics),
            "attempted_utc": str(attempted_utc or "").strip(),
        },
        "sections": [],
    }


def _exact_cache_replay_notice(*, reason: str) -> dict[str, str]:
    reason_token = str(reason or "").strip().lower() or "provider_unavailable"
    if reason_token == "provider_deferred":
        title = "Showing exact replayed brief"
        message = (
            "Compass stayed on the cheap refresh path for this view, so it replayed the last "
            "validated brief for the exact same fact packet."
        )
    elif reason_token == "provider_empty":
        title = "Showing last validated exact brief"
        message = (
            "Compass did not receive a usable live brief, so it replayed the last validated "
            "brief for the exact same fact packet."
        )
    elif reason_token == "validation_failed":
        title = "Showing last validated exact brief"
        message = (
            "Compass rejected the live brief for this packet, so it replayed the last validated "
            "brief for the exact same fact packet."
        )
    else:
        title = "Showing last validated exact brief"
        message = (
            "Compass could not reach a live narrator, so it replayed the last validated brief "
            "for the exact same fact packet."
        )
    return {
        "title": title,
        "message": message,
        "reason": reason_token,
    }


def _exact_cache_ready_brief_if_available(
    *,
    fingerprint: str,
    cached_entry: Mapping[str, Any] | None,
    fact_packet: Mapping[str, Any],
    notice_reason: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(cached_entry, Mapping):
        return None
    return _cache_ready_brief(
        fingerprint=fingerprint,
        cached_entry=cached_entry,
        fact_packet=fact_packet,
        cache_mode="exact",
        notice=_exact_cache_replay_notice(reason=notice_reason or "")
        if notice_reason
        else None,
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


def _provider_display_name(provider: str) -> str:
    token = str(provider or "").strip().lower()
    if token == "codex-cli":
        return "Codex CLI"
    if token == "claude-cli":
        return "Claude Code"
    if token == "openai-compatible":
        return "OpenAI-compatible endpoint"
    if token == "auto-local":
        return "local provider"
    return str(provider or "").strip()


def _provider_attempt_label(*, diagnostics: Mapping[str, Any] | None = None) -> str:
    if not isinstance(diagnostics, Mapping):
        return ""
    provider_label = _provider_display_name(str(diagnostics.get("provider", "")).strip())
    model_label = str(diagnostics.get("provider_model", "") or diagnostics.get("model", "")).strip()
    if provider_label and model_label:
        return f"{provider_label} using {model_label}"
    return provider_label or model_label


def _unavailable_brief_message(
    reason: str,
    *,
    diagnostics: Mapping[str, Any] | None = None,
) -> str:
    token = str(reason or "").strip().lower()
    if token == "skipped_not_worth_calling":
        return "Compass kept provider spend at zero here because the winning narrative facts did not change enough to justify a fresh live rewrite."
    if token == "provider_deferred":
        return "Compass is still warming a fresh brief for this exact packet. There was no exact replay ready yet."
    if token == "rate_limited":
        return "Compass hit narration provider capacity while warming this brief. It will retry on backoff."
    if token == "credits_exhausted":
        attempt_label = _provider_attempt_label(diagnostics=diagnostics)
        if attempt_label:
            return (
                "Compass could not warm this brief because the last narration attempt through "
                f"{attempt_label} may have hit a credit or budget limit. It will retry on backoff."
            )
        return "Compass could not warm this brief because the narration provider may have hit a credit or budget limit. It will retry on backoff."
    if token == "timeout":
        return "Compass asked the narration provider for this brief, but the reply took too long. It will retry on backoff."
    if token == "provider_unavailable":
        return "Compass could not reach the narration provider, and there was no exact current-packet brief to replay."
    if token == "transport_error":
        return "Compass could not reach the narration provider for this brief. It will retry on backoff."
    if token == "auth_error":
        return "Compass could not warm this brief because the narration provider rejected the request. Check provider access before trusting another retry."
    if token == "provider_empty":
        return "Compass did not receive a usable narration reply, and there was no exact current-packet brief to replay."
    if token == "provider_error":
        return "The narration provider failed on the last attempt. Compass will retry on backoff."
    if token == "invalid_batch":
        return "Compass received a narration reply for this brief, but the result was not usable yet. It will retry on backoff."
    if token == "validation_failed":
        return "Compass received an invalid brief, and there was no exact current-packet brief to replay."
    return "Compass could not build a current standup brief for this packet."


def _unavailable_brief_title(
    reason: str,
    *,
    diagnostics: Mapping[str, Any] | None = None,
) -> str:
    token = str(reason or "").strip().lower()
    if token == "skipped_not_worth_calling":
        return "Brief stayed on wallet-safe local truth"
    if token == "provider_deferred":
        return "Fresh brief still warming"
    if token == "rate_limited":
        return "Brief is waiting on provider capacity"
    if token == "credits_exhausted":
        provider_label = ""
        if isinstance(diagnostics, Mapping):
            provider_label = _provider_display_name(str(diagnostics.get("provider", "")).strip())
        if provider_label:
            return f"Brief is waiting on {provider_label} budget"
        return "Brief is waiting on provider budget"
    if token == "timeout":
        return "Brief timed out"
    if token == "provider_unavailable":
        return "Brief provider unavailable"
    if token == "transport_error":
        return "Brief provider could not be reached"
    if token == "auth_error":
        return "Brief provider access failed"
    if token == "provider_empty":
        return "Brief provider returned nothing usable"
    if token == "provider_error":
        return "Brief unavailable right now"
    if token == "invalid_batch":
        return "Brief needs another provider pass"
    if token == "validation_failed":
        return "Brief failed validation"
    return "Standup brief unavailable"


def _failure_reason_from_provider_code(code: str) -> str:
    token = str(code or "").strip().lower()
    mapping = {
        "rate_limited": "rate_limited",
        "credits_exhausted": "credits_exhausted",
        "timeout": "timeout",
        "unavailable": "provider_unavailable",
        "transport_error": "transport_error",
        "auth_error": "auth_error",
        "provider_error": "provider_error",
        "invalid_response": "invalid_batch",
    }
    return mapping.get(token, "")


_FAILOVER_PROVIDER_FAILURE_REASONS: frozenset[str] = frozenset(
    {"credits_exhausted", "rate_limited", "provider_error"}
)


def _alternate_local_provider_name(provider_name: str) -> str:
    token = str(provider_name or "").strip().lower()
    if token == "codex-cli":
        return "claude-cli"
    if token == "claude-cli":
        return "codex-cli"
    return ""


def _retryable_provider_failure(provider: Any) -> tuple[str, dict[str, Any]]:
    failure = odylith_reasoning.provider_failure_metadata(provider)
    reason = _failure_reason_from_provider_code(failure.get("code", ""))
    if reason in _FAILOVER_PROVIDER_FAILURE_REASONS:
        return reason, failure
    return "", failure


def _alternate_local_provider(
    *,
    repo_root: Path,
    config: odylith_reasoning.ReasoningConfig,
    failed_provider: Any,
) -> tuple[odylith_reasoning.ReasoningProvider | None, odylith_reasoning.ReasoningConfig | None, dict[str, Any]]:
    reason, failure = _retryable_provider_failure(failed_provider)
    failed_provider_name = str(failure.get("provider", "")).strip().lower()
    alternate_name = _alternate_local_provider_name(failed_provider_name)
    if not reason or not alternate_name:
        return None, None, failure
    alternate_config = replace(config, provider=alternate_name, model="")
    alternate_provider = odylith_reasoning.provider_from_config(
        alternate_config,
        repo_root=repo_root,
        require_auto_mode=False,
        allow_implicit_local_provider=True,
    )
    return alternate_provider, alternate_config, failure


def _unavailable_ready_brief(
    *,
    fingerprint: str,
    generated_utc: str,
    reason: str,
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    token = str(reason or "").strip().lower() or "brief_unavailable"
    diagnostic_payload = {
        "reason": token,
        "title": _unavailable_brief_title(token, diagnostics=diagnostics),
        "message": _unavailable_brief_message(token, diagnostics=diagnostics),
    }
    if isinstance(diagnostics, Mapping):
        for key, value in diagnostics.items():
            if value in (None, "", []):
                continue
            diagnostic_payload[str(key)] = value
    return {
        "schema_version": STANDUP_BRIEF_SCHEMA_VERSION,
        "status": "unavailable",
        "source": "unavailable",
        "fingerprint": fingerprint,
        "substrate_fingerprint": str(fingerprint).strip(),
        "bundle_fingerprint": "",
        "provider_decision": str(diagnostic_payload.get("provider_decision", "")).strip().lower() or token,
        "last_successful_narration_fingerprint": "",
        "generated_utc": generated_utc,
        "sections": [],
        "diagnostics": diagnostic_payload,
        "evidence_lookup": {},
    }


def unavailable_brief_for_provider_failure(
    *,
    fingerprint: str,
    generated_utc: str,
    provider: Any,
    fallback_reason: str = "provider_empty",
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    failure = odylith_reasoning.provider_failure_metadata(provider)
    reason = _failure_reason_from_provider_code(failure.get("code", "")) or str(fallback_reason or "").strip().lower()
    payload = dict(diagnostics) if isinstance(diagnostics, Mapping) else {}
    if failure.get("provider"):
        payload.setdefault("provider", failure["provider"])
    if failure.get("code"):
        payload.setdefault("provider_failure_code", failure["code"])
    if failure.get("detail"):
        payload.setdefault("provider_failure_detail", failure["detail"])
    if failure.get("model"):
        payload.setdefault("provider_model", failure["model"])
    if failure.get("reasoning_effort"):
        payload.setdefault("provider_reasoning_effort", failure["reasoning_effort"])
    return _unavailable_ready_brief(
        fingerprint=fingerprint,
        generated_utc=generated_utc,
        reason=reason,
        diagnostics=payload,
    )


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


def _workstream_ids_from_text(text: str) -> set[str]:
    return {match.group(0) for match in _WORKSTREAM_TOKEN_RE.finditer(str(text or ""))}


def _fact_workstream_ids(fact: Mapping[str, Any]) -> set[str]:
    ids = {
        str(token).strip()
        for token in fact.get("workstreams", [])
        if str(token).strip()
    }
    ids |= _workstream_ids_from_text(str(fact.get("text", "")).strip())
    return ids


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
    response = {"sections": [dict(item) for item in raw_sections if isinstance(item, Mapping)]}
    sections, errors = _validate_brief_response(
        response=response,
        fact_packet=fact_packet,
        cached_evidence_lookup=cached_evidence_lookup,
    )
    if not errors and sections:
        return sections
    return None


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
            if _GENERIC_RISK_WRAPPER_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} reuses a generic risk wrapper")
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
            if _GENERIC_COVERAGE_ROLLCALL_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} falls back to a stock workstream roll-call")
            if _GENERIC_LINKAGE_WRAPPER_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} falls back to a stock linkage wrapper")
            if _GENERIC_EXISTENCE_BECAUSE_RE.search(text):
                errors.append(f"section {key} bullet {bullet_index} falls back to a stock existence wrapper")
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
            cited_facts = [
                fact_lookup[fact_id]
                for fact_id in (local_fact_ids or normalized_fact_ids)
                if fact_id in fact_lookup
            ]
            bullet_workstream_ids = _workstream_ids_from_text(text)
            cited_workstream_ids: set[str] = set()
            for cited_fact in cited_facts:
                cited_workstream_ids |= _fact_workstream_ids(cited_fact)
            errors.extend(
                compass_standup_brief_voice_validation.bullet_shape_errors(
                    section_key=key,
                    bullet_index=bullet_index,
                    text=text,
                    fact_texts=cited_fact_texts,
                )
            )
            if bullet_workstream_ids and cited_workstream_ids and not (bullet_workstream_ids & cited_workstream_ids):
                errors.append(
                    f"section {key} bullet {bullet_index} names workstreams that do not appear in the cited fact"
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
) -> dict[str, Any]:
    """Build a validated standup brief with exact-fingerprint replay only."""

    repo_root = Path(repo_root).resolve()
    previous_entry = latest_cached_entry_for_context(repo_root=repo_root, fact_packet=fact_packet)
    previous_substrate = (
        previous_entry.get("substrate")
        if isinstance(previous_entry, Mapping) and isinstance(previous_entry.get("substrate"), Mapping)
        else None
    )
    previous_brief = None
    if isinstance(previous_entry, Mapping):
        previous_brief = _cache_ready_brief(
            fingerprint=str(previous_entry.get("fingerprint", "")).strip(),
            cached_entry=previous_entry,
            fact_packet=fact_packet,
            cache_mode="exact",
        )
    substrate = _narration_substrate(
        fact_packet=fact_packet,
        previous_substrate=previous_substrate,
        previous_brief=previous_brief,
    )
    fingerprint = str(substrate.get("fingerprint", "")).strip()
    cache_payload = _load_cache(repo_root=repo_root)
    entries = cache_payload.get("entries")
    cache_entries = dict(entries) if isinstance(entries, Mapping) else {}
    cache_context = _cache_context(fact_packet=fact_packet)
    cached_entry = cache_entries.get(fingerprint)
    if not prefer_provider and isinstance(cached_entry, Mapping):
        cached_ready = _exact_cache_ready_brief_if_available(
            fingerprint=fingerprint,
            cached_entry=cached_entry,
            fact_packet=fact_packet,
        )
        if cached_ready is not None:
            return cached_ready
    resolved_config = config or odylith_reasoning.reasoning_config_from_env(repo_root=repo_root)
    if not allow_provider:
        cached_ready = _exact_cache_ready_brief_if_available(
            fingerprint=fingerprint,
            cached_entry=cached_entry,
            fact_packet=fact_packet,
        )
        if cached_ready is not None:
            return cached_ready
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
        exact_ready = _exact_cache_ready_brief_if_available(
            fingerprint=fingerprint,
            cached_entry=cached_entry,
            fact_packet=fact_packet,
            notice_reason="provider_unavailable",
        )
        if exact_ready is not None:
            return exact_ready
        return _unavailable_ready_brief(
            fingerprint=fingerprint,
            generated_utc=generated_utc,
            reason="provider_unavailable",
        )

    failover_diagnostics: dict[str, Any] = {}
    raw_result = _request_provider_with_empty_retry(
        provider=resolved_provider,
        requests=_provider_requests_for_empty_retry(
            fact_packet=fact_packet,
            config=resolved_config,
        ),
    )
    if not isinstance(raw_result, Mapping) and provider is None:
        alternate_provider, alternate_config, primary_failure = _alternate_local_provider(
            repo_root=repo_root,
            config=resolved_config,
            failed_provider=resolved_provider,
        )
        if alternate_provider is not None and alternate_config is not None:
            failover_diagnostics = {
                "primary_provider": primary_failure.get("provider", ""),
                "primary_provider_failure_code": primary_failure.get("code", ""),
            }
            raw_result = _request_provider_with_empty_retry(
                provider=alternate_provider,
                requests=_provider_requests_for_empty_retry(
                    fact_packet=fact_packet,
                    config=alternate_config,
                ),
            )
            if isinstance(raw_result, Mapping):
                resolved_provider = alternate_provider
                resolved_config = alternate_config
                failover_diagnostics["fallback_provider"] = odylith_reasoning.provider_failure_metadata(
                    alternate_provider
                ).get("provider", "") or alternate_config.provider
            else:
                alternate_failure = odylith_reasoning.provider_failure_metadata(alternate_provider)
                failover_diagnostics["fallback_provider"] = alternate_failure.get("provider", "") or alternate_config.provider
                failover_diagnostics["fallback_provider_failure_code"] = alternate_failure.get("code", "")
    if not isinstance(raw_result, Mapping):
        exact_ready = _exact_cache_ready_brief_if_available(
            fingerprint=fingerprint,
            cached_entry=cached_entry,
            fact_packet=fact_packet,
            notice_reason="provider_empty",
        )
        if exact_ready is not None:
            return exact_ready
        return unavailable_brief_for_provider_failure(
            fingerprint=fingerprint,
            generated_utc=generated_utc,
            provider=resolved_provider,
            fallback_reason="provider_empty",
            diagnostics=failover_diagnostics,
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
            exact_ready = _exact_cache_ready_brief_if_available(
                fingerprint=fingerprint,
                cached_entry=cached_entry,
                fact_packet=fact_packet,
                notice_reason="validation_failed",
            )
            if exact_ready is not None:
                return exact_ready
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
        substrate_fingerprint=fingerprint,
        provider_decision=(
            "provider_failover"
            if failover_diagnostics.get("primary_provider") and failover_diagnostics.get("fallback_provider")
            else "provider_called"
        ),
        last_successful_narration_fingerprint=fingerprint,
    )
    cache_entries[fingerprint] = {
        "generated_utc": ready["generated_utc"],
        "sections": ready["sections"],
        "evidence_lookup": ready["evidence_lookup"],
        "context": cache_context,
        "substrate_fingerprint": fingerprint,
        "last_successful_narration_fingerprint": fingerprint,
        "substrate": substrate,
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
    "latest_cached_entry_for_context",
    "standup_brief_cache_path",
    "standup_brief_fingerprint",
]
