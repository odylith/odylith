"""Optional Vespa-backed shared retrieval augmentation for Odylith."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import quote, urljoin

import httpx

from odylith.runtime.memory import odylith_memory_backend
from odylith.runtime.context_engine import odylith_context_cache

STATE_FILENAME = "odylith-vespa-sync.v1.json"
SYNC_MANIFEST_FILENAME = "odylith-vespa-sync-manifest.v1.json"
_ALLOWED_REMOTE_MODES = {"disabled", "augment", "remote_only"}
_DEFAULT_TIMEOUT_SECONDS = 20.0


def remote_state_path(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / ".odylith" / "runtime" / STATE_FILENAME).resolve()


def sync_manifest_path(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / ".odylith" / "runtime" / SYNC_MANIFEST_FILENAME).resolve()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _env_truthy(name: str) -> bool:
    value = str(os.environ.get(name, "")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _coerce_timeout_seconds(raw_value: str, *, issues: list[str]) -> float:
    token = str(raw_value or "").strip()
    if not token:
        return _DEFAULT_TIMEOUT_SECONDS
    try:
        timeout_seconds = float(token)
    except ValueError:
        issues.append("invalid_timeout_seconds")
        return _DEFAULT_TIMEOUT_SECONDS
    if timeout_seconds <= 0.0:
        issues.append("nonpositive_timeout_seconds")
        return _DEFAULT_TIMEOUT_SECONDS
    return timeout_seconds


def _remote_action(*, blocking_issues: Sequence[str], mode: str) -> str:
    blocking = {str(issue).strip() for issue in blocking_issues if str(issue).strip()}
    if "base_url_missing" in blocking:
        return "Set ODYLITH_VESPA_URL before using Vespa-backed retrieval or sync."
    if "incomplete_client_certificate" in blocking:
        return "Set both ODYLITH_VESPA_CLIENT_CERT and ODYLITH_VESPA_CLIENT_KEY, or unset both."
    if "client_cert_missing" in blocking or "client_key_missing" in blocking:
        return "Point ODYLITH_VESPA_CLIENT_CERT and ODYLITH_VESPA_CLIENT_KEY at readable files, or unset them."
    invalid_mode = next((issue for issue in blocking if issue.startswith("invalid_mode:")), "")
    if invalid_mode:
        return "Set ODYLITH_VESPA_MODE to one of disabled, augment, or remote_only."
    if mode == "disabled":
        return "Set ODYLITH_VESPA_MODE=augment or remote_only after configuring a live Vespa endpoint."
    return ""


def remote_config(*, repo_root: Path) -> dict[str, Any]:
    base_url = str(os.environ.get("ODYLITH_VESPA_URL", "")).strip().rstrip("/")
    schema = str(os.environ.get("ODYLITH_VESPA_SCHEMA", "")).strip() or "odylith_memory"
    namespace = str(os.environ.get("ODYLITH_VESPA_NAMESPACE", "")).strip() or "odylith"
    issues: list[str] = []
    blocking_issues: list[str] = []
    mode = str(os.environ.get("ODYLITH_VESPA_MODE", "")).strip().lower() or "disabled"
    if mode not in _ALLOWED_REMOTE_MODES:
        blocking_issues.append(f"invalid_mode:{mode}")
    ranking = str(os.environ.get("ODYLITH_VESPA_RANK_PROFILE", "")).strip()
    timeout_seconds = _coerce_timeout_seconds(os.environ.get("ODYLITH_VESPA_TIMEOUT_SECONDS", ""), issues=issues)
    token = str(os.environ.get("ODYLITH_VESPA_TOKEN", "")).strip()
    cert_path = str(os.environ.get("ODYLITH_VESPA_CLIENT_CERT", "")).strip()
    key_path = str(os.environ.get("ODYLITH_VESPA_CLIENT_KEY", "")).strip()
    if bool(cert_path) != bool(key_path):
        blocking_issues.append("incomplete_client_certificate")
    if cert_path and key_path:
        cert_candidate = Path(cert_path).expanduser()
        key_candidate = Path(key_path).expanduser()
        cert_path = str(cert_candidate)
        key_path = str(key_candidate)
        if not cert_candidate.is_file():
            blocking_issues.append("client_cert_missing")
        if not key_candidate.is_file():
            blocking_issues.append("client_key_missing")
    prune_missing = _env_truthy("ODYLITH_VESPA_PRUNE_MISSING")
    active_mode = mode in {"augment", "remote_only"}
    if active_mode and not base_url:
        blocking_issues.append("base_url_missing")
    blocking_issues = list(dict.fromkeys(blocking_issues))
    issues = list(dict.fromkeys([*issues, *blocking_issues]))
    enabled = bool(base_url and active_mode and not blocking_issues)
    status = "ready" if enabled else "misconfigured" if blocking_issues or active_mode else "disabled"
    return {
        "provider": "vespa_http",
        "enabled": enabled,
        "configured": bool(base_url),
        "status": status,
        "mode": mode,
        "base_url": base_url,
        "schema": schema,
        "namespace": namespace,
        "ranking_profile": ranking,
        "timeout_seconds": timeout_seconds,
        "prune_missing": prune_missing,
        "issues": issues,
        "blocking_issues": blocking_issues,
        "action": _remote_action(blocking_issues=blocking_issues, mode=mode),
        "auth": {
            "bearer_token": bool(token),
            "client_cert": bool(cert_path and key_path),
        },
        "token": token,
        "cert_path": cert_path,
        "key_path": key_path,
        "state": odylith_context_cache.read_json_object(remote_state_path(repo_root=repo_root)),
    }


def _client_kwargs(config: Mapping[str, Any]) -> dict[str, Any]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    token = str(config.get("token", "")).strip()
    cert_path = str(config.get("cert_path", "")).strip()
    key_path = str(config.get("key_path", "")).strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    kwargs: dict[str, Any] = {"headers": headers, "timeout": float(config.get("timeout_seconds", 20.0) or 20.0)}
    if cert_path and key_path:
        kwargs["cert"] = (cert_path, key_path)
    return kwargs


def _vespa_kind_filter_yql(kinds: Sequence[str] | None) -> str:
    allowed = [str(kind).strip().lower() for kind in (kinds or []) if str(kind).strip()]
    if not allowed:
        return ""
    clauses = [f'kind contains "{token.replace(chr(34), r"\\\"")}"' for token in allowed]
    return " and (" + " or ".join(clauses) + ")"


def _document_sync_fingerprint(documents: Sequence[Mapping[str, Any]]) -> str:
    return odylith_context_cache.fingerprint_payload(
        [
            {
                "doc_key": str(row.get("doc_key", "")).strip(),
                "path": str(row.get("path", "")).strip(),
                "content_hash": str(row.get("content_hash", "")).strip() or str(row.get("content", "")).strip(),
            }
            for row in documents
            if isinstance(row, Mapping) and str(row.get("doc_key", "")).strip()
        ]
    )


def _document_fields(row: Mapping[str, Any]) -> dict[str, Any]:
    content = str(row.get("content", "")).strip()
    embedding = row.get("embedding")
    if not isinstance(embedding, list) or not embedding:
        source_text = "\n".join(
            token
            for token in (
                str(row.get("entity_id", "")).strip(),
                str(row.get("title", "")).strip(),
                str(row.get("path", "")).strip(),
                content,
            )
            if token
        ).strip()
        embedding = odylith_memory_backend.derived_embedding(source_text)
    return {
        "doc_key": str(row.get("doc_key", "")).strip(),
        "kind": str(row.get("kind", "")).strip(),
        "entity_id": str(row.get("entity_id", "")).strip(),
        "title": str(row.get("title", "")).strip(),
        "path": str(row.get("path", "")).strip(),
        "content": content,
        "embedding": [float(value) for value in embedding],
    }


def _dedupe_documents(documents: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for row in documents:
        if not isinstance(row, Mapping):
            continue
        doc_key = str(row.get("doc_key", "")).strip()
        if not doc_key:
            continue
        deduped[doc_key] = dict(row)
    return [deduped[key] for key in sorted(deduped)]


def query_remote(
    *,
    repo_root: Path,
    query: str,
    limit: int,
    kinds: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    config = remote_config(repo_root=root)
    if not bool(config.get("enabled")):
        return []
    base_url = str(config.get("base_url", "")).strip()
    schema = str(config.get("schema", "")).strip()
    ranking = str(config.get("ranking_profile", "")).strip()
    kind_filter = _vespa_kind_filter_yql(kinds)
    requested_hits = max(1, int(limit))
    payload: dict[str, Any] = {
        "yql": f"select * from sources {schema} where userQuery(){kind_filter};",
        "query": str(query or "").strip(),
        "hits": requested_hits * (3 if kind_filter else 1),
    }
    if ranking:
        payload["ranking.profile"] = ranking
    response = httpx.post(urljoin(base_url + "/", "search/"), json=payload, **_client_kwargs(config))
    response.raise_for_status()
    body = response.json()
    allowed = {str(kind).strip().lower() for kind in (kinds or []) if str(kind).strip()}
    results: list[dict[str, Any]] = []
    root_payload = body.get("root", {}) if isinstance(body, Mapping) else {}
    hits = root_payload.get("children", []) if isinstance(root_payload, Mapping) else []
    for hit in hits if isinstance(hits, list) else []:
        if not isinstance(hit, Mapping):
            continue
        fields = hit.get("fields", {}) if isinstance(hit.get("fields"), Mapping) else {}
        kind = str(fields.get("kind", "")).strip().lower()
        if allowed and kind not in allowed:
            continue
        results.append(
            {
                "doc_key": str(fields.get("doc_key", "")).strip(),
                "kind": kind,
                "entity_id": str(fields.get("entity_id", "")).strip(),
                "title": str(fields.get("title", "")).strip(),
                "path": str(fields.get("path", "")).strip(),
                "score": float(hit.get("relevance", 0.0) or 0.0),
                "remote": True,
            }
        )
        if len(results) >= max(1, int(limit)):
            break
    return results


def sync_remote(
    *,
    repo_root: Path,
    documents: Sequence[Mapping[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config = remote_config(repo_root=root)
    unique_documents = _dedupe_documents(documents)
    manifest_path = sync_manifest_path(repo_root=root)
    previous_manifest = odylith_context_cache.read_json_object(manifest_path)
    current_doc_keys = [
        str(row.get("doc_key", "")).strip()
        for row in unique_documents
        if isinstance(row, Mapping) and str(row.get("doc_key", "")).strip()
    ]
    current_doc_keys = sorted(dict.fromkeys(current_doc_keys))
    sync_fingerprint = _document_sync_fingerprint(unique_documents)
    previous_keys = (
        [str(token).strip() for token in previous_manifest.get("synced_doc_keys", []) if str(token).strip()]
        if isinstance(previous_manifest.get("synced_doc_keys"), list)
        else []
    )
    stale_doc_keys = sorted(set(previous_keys) - set(current_doc_keys))
    now_state = {
        "provider": "vespa_http",
        "enabled": bool(config.get("enabled")),
        "configured": bool(config.get("configured")),
        "issues": list(config.get("issues", [])) if isinstance(config.get("issues"), list) else [],
        "blocking_issues": list(config.get("blocking_issues", []))
        if isinstance(config.get("blocking_issues"), list)
        else [],
        "action": str(config.get("action", "")).strip(),
        "mode": str(config.get("mode", "")).strip(),
        "dry_run": bool(dry_run),
        "attempted_documents": len(unique_documents),
        "synced_documents": 0,
        "deleted_documents": 0,
        "stale_documents": len(stale_doc_keys),
        "sync_fingerprint": sync_fingerprint,
        "errors": [],
    }
    if str(config.get("status", "")).strip() == "misconfigured":
        now_state["status"] = "misconfigured"
        now_state["errors"] = list(now_state.get("blocking_issues", []))
        odylith_context_cache.write_json_if_changed(
            repo_root=root,
            path=remote_state_path(repo_root=root),
            payload=now_state,
            lock_key=str(remote_state_path(repo_root=root)),
        )
        return now_state
    if not bool(config.get("enabled")):
        now_state["status"] = "disabled"
        odylith_context_cache.write_json_if_changed(
            repo_root=root,
            path=remote_state_path(repo_root=root),
            payload=now_state,
            lock_key=str(remote_state_path(repo_root=root)),
        )
        return now_state
    base_url = str(config.get("base_url", "")).strip()
    namespace = str(config.get("namespace", "")).strip()
    schema = str(config.get("schema", "")).strip()
    if dry_run:
        now_state["status"] = "dry_run"
        odylith_context_cache.write_json_if_changed(
            repo_root=root,
            path=remote_state_path(repo_root=root),
            payload=now_state,
            lock_key=str(remote_state_path(repo_root=root)),
        )
        return now_state
    if (
        sync_fingerprint
        and str(previous_manifest.get("sync_fingerprint", "")).strip() == sync_fingerprint
        and set(previous_keys) == set(current_doc_keys)
    ):
        now_state["status"] = "skipped_unchanged"
        now_state["last_synced_utc"] = str(previous_manifest.get("last_synced_utc", "")).strip()
        odylith_context_cache.write_json_if_changed(
            repo_root=root,
            path=remote_state_path(repo_root=root),
            payload=now_state,
            lock_key=str(remote_state_path(repo_root=root)),
        )
        return now_state
    client = httpx.Client(**_client_kwargs(config))
    try:
        for row in unique_documents:
            if not isinstance(row, Mapping):
                continue
            doc_key = str(row.get("doc_key", "")).strip()
            if not doc_key:
                continue
            body = {
                "fields": _document_fields(row),
            }
            endpoint = urljoin(
                base_url + "/",
                f"document/v1/{quote(namespace, safe='')}/{quote(schema, safe='')}/docid/{quote(doc_key, safe='')}",
            )
            try:
                response = client.post(endpoint, json=body)
                response.raise_for_status()
                now_state["synced_documents"] += 1
            except Exception as exc:  # pragma: no cover - exercised by integration/error handling
                now_state["errors"].append(f"{doc_key}: {type(exc).__name__}: {exc}")
        if bool(config.get("prune_missing")):
            for doc_key in stale_doc_keys:
                endpoint = urljoin(
                    base_url + "/",
                    f"document/v1/{quote(namespace, safe='')}/{quote(schema, safe='')}/docid/{quote(doc_key, safe='')}",
                )
                try:
                    response = client.delete(endpoint)
                    response.raise_for_status()
                    now_state["deleted_documents"] += 1
                except Exception as exc:  # pragma: no cover - exercised by integration/error handling
                    now_state["errors"].append(f"delete {doc_key}: {type(exc).__name__}: {exc}")
        now_state["status"] = "ok" if not now_state["errors"] else "partial_error"
        now_state["last_synced_utc"] = _utc_now()
    finally:
        client.close()
    if now_state["status"] == "ok":
        odylith_context_cache.write_json_if_changed(
            repo_root=root,
            path=manifest_path,
            payload={
                "provider": "vespa_http",
                "schema": schema,
                "namespace": namespace,
                "sync_fingerprint": sync_fingerprint,
                "attempted_documents": len(current_doc_keys),
                "synced_doc_keys": current_doc_keys,
                "last_synced_utc": now_state.get("last_synced_utc", ""),
            },
            lock_key=str(manifest_path),
        )
    odylith_context_cache.write_json_if_changed(
        repo_root=root,
        path=remote_state_path(repo_root=root),
        payload=now_state,
        lock_key=str(remote_state_path(repo_root=root)),
    )
    return now_state


__all__ = [
    "query_remote",
    "remote_config",
    "remote_state_path",
    "sync_manifest_path",
    "sync_remote",
]
