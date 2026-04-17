from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.common import agent_runtime_contract


_INTERVENTION_EVENT_KINDS: frozenset[str] = frozenset(
    {
        "intervention_teaser",
        "ambient_signal",
        "intervention_card",
        "capture_proposed",
        "capture_applied",
        "capture_declined",
        "assist_closeout",
    }
)
_EVENT_STREAM_CACHE: dict[tuple[str, int, int], list[dict[str, Any]]] = {}
_SESSION_MEMORY_CACHE: dict[tuple[tuple[str, int, int], str, int], dict[str, Any]] = {}
_PENDING_PROPOSAL_CACHE: dict[tuple[tuple[str, int, int], int], dict[str, Any]] = {}
_STREAM_PATH_CACHE: dict[tuple[str, str], Path] = {}


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


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        token = _normalize_string(value)
        return [token] if token else []
    rows: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = _normalize_string(item)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _json_safe_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    try:
        encoded = json.dumps(dict(value), sort_keys=True, default=str)
        decoded = json.loads(encoded)
    except (TypeError, ValueError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _agent_stream_path(*, repo_root: Path, value: Any = "") -> Path:
    cache_key = (str(repo_root), _normalize_string(value))
    cached = _STREAM_PATH_CACHE.get(cache_key)
    if cached is not None:
        return cached
    root = Path(repo_root).expanduser()
    if not root.is_absolute():
        root = Path.cwd() / root
    requested = str(value or "").strip()
    if requested:
        explicit = Path(requested).expanduser()
        if explicit.is_absolute():
            path = explicit
            _STREAM_PATH_CACHE[cache_key] = path
            return path
    path = root / agent_runtime_contract.AGENT_STREAM_PATH
    for token in agent_runtime_contract.candidate_stream_tokens(value):
        candidate = root / token
        if candidate.exists():
            path = candidate
            break
    _STREAM_PATH_CACHE[cache_key] = path
    return path


def _stream_cache_signature(*, repo_root: Path) -> tuple[str, int, int]:
    stream_path = _agent_stream_path(repo_root=repo_root)
    if not stream_path.is_file():
        return (stream_path.as_posix(), -1, -1)
    try:
        stat = stream_path.stat()
        return (stream_path.as_posix(), int(stat.st_mtime_ns), int(stat.st_size))
    except OSError:
        return (stream_path.as_posix(), -1, -1)


def event_cache_signature(*, repo_root: Path) -> tuple[str, int, int]:
    return _stream_cache_signature(repo_root=repo_root)


def append_intervention_event(
    *,
    repo_root: Path,
    kind: str,
    summary: str,
    session_id: str = "",
    host_family: str = "",
    intervention_key: str = "",
    turn_phase: str = "",
    workstreams: Sequence[str] = (),
    artifacts: Sequence[str] = (),
    components: Sequence[str] = (),
    action_surfaces: Sequence[str] = (),
    display_markdown: str = "",
    display_plain: str = "",
    confirmation_text: str = "",
    proposal_status: str = "",
    prompt_excerpt: str = "",
    assistant_summary: str = "",
    moment_kind: str = "",
    semantic_signature: Sequence[str] = (),
    delivery_channel: str = "",
    delivery_status: str = "",
    render_surface: str = "",
    delivery_latency_ms: float | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_kind = _normalize_string(kind).lower()
    if normalized_kind not in _INTERVENTION_EVENT_KINDS:
        raise ValueError(f"unsupported intervention event kind: {kind}")
    payload = {
        "version": "v1",
        "kind": normalized_kind,
        "summary": _normalize_string(summary),
        "ts_iso": dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "author": "assistant",
        "source": "assistant",
        "session_id": _normalize_string(session_id) or agent_runtime_contract.default_host_session_id(),
        "host_family": _normalize_string(host_family).lower(),
        "intervention_key": _normalize_string(intervention_key),
        "turn_phase": _normalize_string(turn_phase).lower(),
        "workstreams": _normalize_string_list(workstreams),
        "artifacts": _normalize_string_list(artifacts),
        "components": _normalize_string_list(components),
        "action_surfaces": _normalize_string_list(action_surfaces),
        "display_markdown": _normalize_block_string(display_markdown),
        "display_plain": _normalize_block_string(display_plain),
        "confirmation_text": _normalize_string(confirmation_text),
        "proposal_status": _normalize_string(proposal_status).lower(),
        "prompt_excerpt": _normalize_string(prompt_excerpt),
        "assistant_summary": _normalize_string(assistant_summary),
        "moment_kind": _normalize_string(moment_kind).lower(),
        "semantic_signature": _normalize_string_list(semantic_signature),
        "delivery_channel": _normalize_string(delivery_channel).lower(),
        "delivery_status": _normalize_string(delivery_status).lower(),
        "render_surface": _normalize_string(render_surface).lower(),
        "metadata": _json_safe_mapping(metadata),
    }
    if delivery_latency_ms is not None:
        payload["delivery_latency_ms"] = round(max(0.0, float(delivery_latency_ms)), 3)
    payload = {key: value for key, value in payload.items() if value not in ("", [], {})}
    stream_path = _agent_stream_path(repo_root=repo_root)
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    with stream_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    _EVENT_STREAM_CACHE.clear()
    _SESSION_MEMORY_CACHE.clear()
    _PENDING_PROPOSAL_CACHE.clear()
    return payload


def load_recent_intervention_events(
    *,
    repo_root: Path,
    limit: int = 200,
    session_id: str = "",
) -> list[dict[str, Any]]:
    stream_path = _agent_stream_path(repo_root=repo_root)
    if not stream_path.is_file():
        return []
    cache_key = _stream_cache_signature(repo_root=repo_root)
    cached = _EVENT_STREAM_CACHE.get(cache_key)
    if cached is None:
        rows: list[dict[str, Any]] = []
        try:
            with stream_path.open(encoding="utf-8") as handle:
                for raw_line in handle:
                    line = str(raw_line or "").strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(payload, Mapping):
                        continue
                    kind = _normalize_string(payload.get("kind")).lower()
                    if kind not in _INTERVENTION_EVENT_KINDS:
                        continue
                    rows.append(dict(payload))
        except OSError:
            return []
        _EVENT_STREAM_CACHE.clear()
        _EVENT_STREAM_CACHE[cache_key] = rows
        cached = rows
    wanted_session = _normalize_string(session_id)
    rows = [
        dict(payload)
        for payload in cached
        if not wanted_session or _normalize_string(payload.get("session_id")) == wanted_session
    ]
    return rows[-max(1, int(limit)) :]


def session_memory_snapshot(
    *,
    repo_root: Path,
    session_id: str,
    limit: int = 80,
) -> dict[str, Any]:
    cache_key = (event_cache_signature(repo_root=repo_root), _normalize_string(session_id), max(1, int(limit)))
    cached = _SESSION_MEMORY_CACHE.get(cache_key)
    if cached is not None:
        return dict(cached)
    events = load_recent_intervention_events(
        repo_root=repo_root,
        limit=limit,
        session_id=session_id,
    )
    recent_signatures: list[str] = []
    recent_teaser_signatures: list[str] = []
    recent_card_signatures: list[str] = []
    recent_moment_kinds: list[str] = []
    seen_all: set[str] = set()
    seen_teaser: set[str] = set()
    seen_card: set[str] = set()
    for row in reversed(events):
        signatures = _normalize_string_list(row.get("semantic_signature"))
        signature_token = "|".join(signatures)
        if signature_token and signature_token not in seen_all:
            seen_all.add(signature_token)
            recent_signatures.append(signature_token)
        kind = _normalize_string(row.get("kind")).lower()
        if signature_token and kind == "intervention_teaser" and signature_token not in seen_teaser:
            seen_teaser.add(signature_token)
            recent_teaser_signatures.append(signature_token)
        if signature_token and kind in {"intervention_card", "capture_proposed"} and signature_token not in seen_card:
            seen_card.add(signature_token)
            recent_card_signatures.append(signature_token)
        moment_kind = _normalize_string(row.get("moment_kind")).lower()
        if moment_kind:
            recent_moment_kinds.append(moment_kind)
    payload = {
        "recent_event_count": len(events),
        "recent_signatures": recent_signatures[:12],
        "recent_teaser_signatures": recent_teaser_signatures[:8],
        "recent_card_signatures": recent_card_signatures[:8],
        "recent_moment_kinds": recent_moment_kinds[:12],
    }
    _SESSION_MEMORY_CACHE[cache_key] = payload
    return dict(payload)


def pending_proposal_state(*, repo_root: Path, limit: int = 400) -> dict[str, Any]:
    cache_key = (event_cache_signature(repo_root=repo_root), max(1, int(limit)))
    cached = _PENDING_PROPOSAL_CACHE.get(cache_key)
    if cached is not None:
        return dict(cached)
    events = load_recent_intervention_events(repo_root=repo_root, limit=limit)
    latest_by_key: dict[str, dict[str, Any]] = {}
    for row in events:
        if _normalize_string(row.get("kind")).lower() not in {
            "capture_proposed",
            "capture_applied",
            "capture_declined",
        }:
            continue
        key = _normalize_string(row.get("intervention_key"))
        if not key:
            continue
        latest_by_key[key] = row
    pending: list[dict[str, Any]] = []
    for row in latest_by_key.values():
        if _normalize_string(row.get("kind")).lower() != "capture_proposed":
            continue
        pending.append(
            {
                "intervention_key": _normalize_string(row.get("intervention_key")),
                "summary": _normalize_string(row.get("summary")),
                "session_id": _normalize_string(row.get("session_id")),
                "host_family": _normalize_string(row.get("host_family")).lower(),
                "turn_phase": _normalize_string(row.get("turn_phase")).lower(),
                "action_surfaces": _normalize_string_list(row.get("action_surfaces")),
                "workstreams": _normalize_string_list(row.get("workstreams")),
                "confirmation_text": _normalize_string(row.get("confirmation_text")),
                "proposal_status": _normalize_string(row.get("proposal_status")).lower(),
                "display_markdown": _normalize_block_string(row.get("display_markdown")),
                "display_plain": _normalize_block_string(row.get("display_plain")),
                "prompt_excerpt": _normalize_string(row.get("prompt_excerpt")),
                "moment_kind": _normalize_string(row.get("moment_kind")).lower(),
                "semantic_signature": _normalize_string_list(row.get("semantic_signature")),
                "delivery_channel": _normalize_string(row.get("delivery_channel")).lower(),
                "delivery_status": _normalize_string(row.get("delivery_status")).lower(),
                "render_surface": _normalize_string(row.get("render_surface")).lower(),
                "ts_iso": _normalize_string(row.get("ts_iso")),
            }
        )
    pending.sort(key=lambda row: row.get("ts_iso", ""), reverse=True)
    payload = {
        "pending_count": len(pending),
        "pending": pending[:8],
        "recent_event_count": len(events),
    }
    _PENDING_PROPOSAL_CACHE[cache_key] = payload
    return dict(payload)
