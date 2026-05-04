"""Patch Compass runtime standup brief slots from maintenance outcomes."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.common.json_objects import load_json_object as _load_json
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.surfaces import compass_standup_brief_narrator

_RUNTIME_CURRENT_JSON = "odylith/compass/runtime/current.v1.json"
_RUNTIME_CURRENT_JS = "odylith/compass/runtime/current.v1.js"


def _now_utc_iso() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def apply_terminal_state_to_runtime_payload(
    *,
    payload: Mapping[str, Any],
    state_entries: Mapping[str, Any],
    runtime_input_fingerprint: str = "",
) -> dict[str, Any]:
    runtime_payload = dict(payload)
    expected_fingerprint = str(runtime_input_fingerprint).strip()
    runtime_contract = runtime_payload.get("runtime_contract")
    if not isinstance(runtime_contract, Mapping):
        return runtime_payload
    actual_fingerprint = str(runtime_contract.get("input_fingerprint", "")).strip()
    if not expected_fingerprint:
        expected_fingerprint = actual_fingerprint
    if not expected_fingerprint or actual_fingerprint != expected_fingerprint:
        return runtime_payload
    global_failures = _terminal_global_failures_from_runtime_payload(
        payload=runtime_payload,
        state_entries=state_entries,
    )
    scoped_failures = _terminal_scoped_failures_from_runtime_payload(
        payload=runtime_payload,
        state_entries=state_entries,
    )
    if not global_failures and not scoped_failures:
        return runtime_payload
    patched_payload, _changed = runtime_payload_with_brief_results(
        payload=runtime_payload,
        global_results={},
        scoped_results={},
        global_failures=global_failures,
        scoped_failures=scoped_failures,
    )
    return patched_payload


def patch_current_runtime_from_terminal_state(
    *,
    repo_root: Path,
    runtime_input_fingerprint: str,
    state_entries: Mapping[str, Any],
) -> bool:
    current_path = repo_root / _RUNTIME_CURRENT_JSON
    current_payload = _load_json(current_path)
    if not isinstance(current_payload, Mapping) or not current_payload:
        return False
    global_failures = _terminal_global_failures_from_runtime_payload(
        payload=current_payload,
        state_entries=state_entries,
    )
    scoped_failures = _terminal_scoped_failures_from_runtime_payload(
        payload=current_payload,
        state_entries=state_entries,
    )
    if not global_failures and not scoped_failures:
        return False
    return patch_current_runtime_payload(
        repo_root=repo_root,
        runtime_input_fingerprint=runtime_input_fingerprint,
        runtime_generated_utc=str(current_payload.get("generated_utc", "")).strip() or _now_utc_iso(),
        global_results={},
        scoped_results={},
        global_failures=global_failures,
        scoped_failures=scoped_failures,
    )


def patch_current_runtime_payload(
    *,
    repo_root: Path,
    runtime_input_fingerprint: str,
    runtime_generated_utc: str,
    global_results: Mapping[str, Mapping[str, Any]],
    scoped_results: Mapping[str, Mapping[str, Mapping[str, Any]]],
    global_failures: Mapping[str, Mapping[str, Any]] | None = None,
    scoped_failures: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
) -> bool:
    current_json_path = (repo_root / _RUNTIME_CURRENT_JSON).resolve()
    current_js_path = (repo_root / _RUNTIME_CURRENT_JS).resolve()
    current_json_signature = odylith_context_cache.path_signature(current_json_path)
    payload = _load_json(current_json_path)
    runtime_contract = payload.get("runtime_contract")
    if not isinstance(runtime_contract, Mapping):
        return False
    if str(runtime_contract.get("input_fingerprint", "")).strip() != str(runtime_input_fingerprint).strip():
        return False
    current_generated_utc = str(payload.get("generated_utc", "")).strip()
    expected_generated_utc = str(runtime_generated_utc).strip()
    if current_generated_utc and expected_generated_utc and current_generated_utc != expected_generated_utc:
        return False
    patched_payload, changed = runtime_payload_with_brief_results(
        payload=payload,
        global_results=global_results,
        scoped_results=scoped_results,
        global_failures=global_failures,
        scoped_failures=scoped_failures,
    )
    if not changed:
        return False
    if odylith_context_cache.path_signature(current_json_path) != current_json_signature:
        return False
    _write_json(repo_root=repo_root, path=current_json_path, payload=patched_payload)
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=current_js_path,
        content="window.__ODYLITH_COMPASS_RUNTIME__ = "
        + json.dumps(patched_payload, separators=(",", ":"))
        + ";\n",
        lock_key=str(current_js_path),
    )
    return True


def runtime_payload_with_brief_results(
    *,
    payload: Mapping[str, Any],
    global_results: Mapping[str, Mapping[str, Any]],
    scoped_results: Mapping[str, Mapping[str, Mapping[str, Any]]],
    global_failures: Mapping[str, Mapping[str, Any]] | None = None,
    scoped_failures: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
) -> tuple[dict[str, Any], bool]:
    patched_payload = dict(payload)
    changed = False
    standup_brief = patched_payload.get("standup_brief")
    digest = patched_payload.get("digest")
    standup_brief_scoped = patched_payload.get("standup_brief_scoped")
    digest_scoped = patched_payload.get("digest_scoped")
    if not isinstance(standup_brief, Mapping):
        standup_brief = {}
    if not isinstance(digest, Mapping):
        digest = {}
    if not isinstance(standup_brief_scoped, Mapping):
        standup_brief_scoped = {}
    if not isinstance(digest_scoped, Mapping):
        digest_scoped = {}
    mutable_standup_brief = {str(key): value for key, value in standup_brief.items()}
    mutable_digest = {str(key): value for key, value in digest.items()}
    mutable_standup_brief_scoped = {
        str(key): dict(value) if isinstance(value, Mapping) else {}
        for key, value in standup_brief_scoped.items()
    }
    mutable_digest_scoped = {
        str(key): dict(value) if isinstance(value, Mapping) else {}
        for key, value in digest_scoped.items()
    }
    for window_key, brief in global_results.items():
        if not isinstance(brief, Mapping):
            continue
        mutable_standup_brief[str(window_key).strip()] = dict(brief)
        mutable_digest[str(window_key).strip()] = compass_standup_brief_narrator.brief_to_digest_lines(brief)
        changed = True
    for window_key, brief in (global_failures or {}).items():
        if not isinstance(brief, Mapping):
            continue
        window_token = str(window_key).strip()
        patched_brief = _brief_preserving_ready_narrative(
            existing=mutable_standup_brief.get(window_token),
            failure=brief,
            scope_kind="global",
        )
        mutable_standup_brief[window_token] = patched_brief
        mutable_digest[window_token] = compass_standup_brief_narrator.brief_to_digest_lines(patched_brief)
        changed = True
    for window_key, window_results in scoped_results.items():
        if not isinstance(window_results, Mapping):
            continue
        scoped_window = dict(mutable_standup_brief_scoped.get(str(window_key).strip(), {}))
        digest_window = dict(mutable_digest_scoped.get(str(window_key).strip(), {}))
        for scope_id, brief in window_results.items():
            if not isinstance(brief, Mapping):
                continue
            scope_token = str(scope_id).strip()
            if not scope_token:
                continue
            scoped_window[scope_token] = dict(brief)
            digest_window[scope_token] = compass_standup_brief_narrator.brief_to_digest_lines(brief)
            changed = True
        mutable_standup_brief_scoped[str(window_key).strip()] = scoped_window
        mutable_digest_scoped[str(window_key).strip()] = digest_window
    for window_key, window_failures in (scoped_failures or {}).items():
        if not isinstance(window_failures, Mapping):
            continue
        window_token = str(window_key).strip()
        scoped_window = dict(mutable_standup_brief_scoped.get(window_token, {}))
        digest_window = dict(mutable_digest_scoped.get(window_token, {}))
        for scope_id, brief in window_failures.items():
            if not isinstance(brief, Mapping):
                continue
            scope_token = str(scope_id).strip()
            if not scope_token:
                continue
            patched_brief = _brief_preserving_ready_narrative(
                existing=scoped_window.get(scope_token),
                failure=brief,
                scope_kind="scoped",
            )
            scoped_window[scope_token] = patched_brief
            digest_window[scope_token] = compass_standup_brief_narrator.brief_to_digest_lines(patched_brief)
            changed = True
        mutable_standup_brief_scoped[window_token] = scoped_window
        mutable_digest_scoped[window_token] = digest_window
    if not changed:
        return patched_payload, False
    patched_payload["standup_brief"] = mutable_standup_brief
    patched_payload["digest"] = mutable_digest
    patched_payload["standup_brief_scoped"] = mutable_standup_brief_scoped
    patched_payload["digest_scoped"] = mutable_digest_scoped
    return patched_payload, True


def _brief_preserving_ready_narrative(
    *,
    existing: Any,
    failure: Mapping[str, Any],
    scope_kind: str,
) -> dict[str, Any]:
    if not isinstance(existing, Mapping):
        return dict(failure)
    if str(existing.get("status", "")).strip().lower() != "ready":
        return dict(failure)
    preserved = dict(existing)
    preserved["notice"] = _failure_notice_for_ready_brief(
        failure=failure,
        scope_kind=scope_kind,
    )
    return preserved


def _failure_notice_for_ready_brief(
    *,
    failure: Mapping[str, Any],
    scope_kind: str,
) -> dict[str, str]:
    diagnostics = (
        dict(failure.get("diagnostics"))
        if isinstance(failure.get("diagnostics"), Mapping)
        else {}
    )
    title = str(diagnostics.get("title", "")).strip() or "Brief unavailable right now"
    message = str(diagnostics.get("message", "")).strip() or (
        "The latest narration pass did not produce a usable standup brief."
    )
    if "last" not in message.lower() or "brief" not in message.lower():
        message = f"{message} Showing the last known standup brief while Compass retries."
    reason = _notice_reason_token(
        str(diagnostics.get("reason", "")).strip()
        or str(failure.get("source", "")).strip()
        or "brief_unavailable"
    )
    prefix = "scoped" if str(scope_kind).strip().lower() == "scoped" else "global"
    notice = {
        "title": title,
        "message": message,
        "reason": f"{prefix}_{reason}_showing_previous",
    }
    next_retry_utc = str(diagnostics.get("next_retry_utc", "")).strip()
    if next_retry_utc:
        notice["next_retry_utc"] = next_retry_utc
    return notice


def _notice_reason_token(value: str) -> str:
    token_chars: list[str] = []
    previous_underscore = False
    for char in str(value).strip().lower():
        if char.isalnum():
            token_chars.append(char)
            previous_underscore = False
        elif not previous_underscore:
            token_chars.append("_")
            previous_underscore = True
    token = "".join(token_chars).strip("_")
    return token or "brief_unavailable"


def _terminal_global_failures_from_runtime_payload(
    *,
    payload: Mapping[str, Any],
    state_entries: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    generated_utc = str(payload.get("generated_utc", "")).strip() or _now_utc_iso()
    standup_briefs = payload.get("standup_brief") if isinstance(payload.get("standup_brief"), Mapping) else {}
    global_failures: dict[str, dict[str, Any]] = {}
    for window_key, brief in standup_briefs.items():
        if not isinstance(brief, Mapping):
            continue
        window_token = str(window_key).strip()
        fingerprint = str(brief.get("fingerprint", "")).strip()
        state_entry = state_entries.get(_candidate_key(window_key=window_token))
        if not window_token or not fingerprint or not isinstance(state_entry, Mapping):
            continue
        if str(state_entry.get("fingerprint", "")).strip() != fingerprint:
            continue
        if str(state_entry.get("status", "")).strip().lower() != "skipped":
            continue
        diagnostics = _diagnostics_from_state_entry(state_entry)
        global_failures[window_token] = compass_standup_brief_narrator._unavailable_ready_brief(  # noqa: SLF001
            fingerprint=fingerprint,
            generated_utc=generated_utc,
            reason=str(diagnostics.get("reason", "")).strip().lower()
            or "skipped_not_worth_calling",
            diagnostics=diagnostics,
        )
    return global_failures


def _terminal_scoped_failures_from_runtime_payload(
    *,
    payload: Mapping[str, Any],
    state_entries: Mapping[str, Any],
) -> dict[str, dict[str, dict[str, Any]]]:
    generated_utc = str(payload.get("generated_utc", "")).strip() or _now_utc_iso()
    scoped_briefs = (
        payload.get("standup_brief_scoped")
        if isinstance(payload.get("standup_brief_scoped"), Mapping)
        else {}
    )
    scoped_failures: dict[str, dict[str, dict[str, Any]]] = {}
    for window_key, scope_map in scoped_briefs.items():
        if not isinstance(scope_map, Mapping):
            continue
        window_token = str(window_key).strip()
        if not window_token:
            continue
        for scope_id, brief in scope_map.items():
            if not isinstance(brief, Mapping):
                continue
            scope_token = str(scope_id).strip()
            fingerprint = str(brief.get("fingerprint", "")).strip()
            state_entry = state_entries.get(_candidate_key(window_key=window_token, scope_id=scope_token))
            if not scope_token or not fingerprint or not isinstance(state_entry, Mapping):
                continue
            if str(state_entry.get("fingerprint", "")).strip() != fingerprint:
                continue
            if str(state_entry.get("status", "")).strip().lower() != "skipped":
                continue
            diagnostics = _diagnostics_from_state_entry(state_entry)
            scoped_failures.setdefault(window_token, {})[
                scope_token
            ] = compass_standup_brief_narrator._unavailable_ready_brief(  # noqa: SLF001
                fingerprint=fingerprint,
                generated_utc=generated_utc,
                reason=str(diagnostics.get("reason", "")).strip().lower()
                or "skipped_not_worth_calling",
                diagnostics=diagnostics,
            )
    return scoped_failures


def _candidate_key(*, window_key: str, scope_id: str = "") -> str:
    return f"global:{window_key}" if not str(scope_id).strip() else f"scoped:{window_key}:{str(scope_id).strip()}"


def _diagnostics_from_state_entry(state_entry: Mapping[str, Any]) -> dict[str, Any]:
    diagnostics = (
        dict(state_entry.get("diagnostics"))
        if isinstance(state_entry.get("diagnostics"), Mapping)
        else {}
    )
    next_retry_utc = str(state_entry.get("next_retry_utc", "")).strip()
    if next_retry_utc:
        diagnostics["next_retry_utc"] = next_retry_utc
    return diagnostics


def _write_json(*, repo_root: Path, path: Path, payload: Mapping[str, Any]) -> None:
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=path,
        content=json.dumps(payload, indent=2) + "\n",
        lock_key=str(path),
    )
