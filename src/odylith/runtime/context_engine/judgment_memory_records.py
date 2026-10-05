"""Bounded source admission and continuity for judgment memory."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.common import derivation_provenance
from odylith.runtime.context_engine import memory_record_policy as policy

_SOURCE_CACHE: dict[str, tuple[dict[str, Any], dict[str, Any], str]] = {}


def projection_provenance(runtime_state: Mapping[str, Any]) -> dict[str, Any]:
    compiler = runtime_state.get("odylith_compiler", {})
    return derivation_provenance.extract_provenance(compiler if isinstance(compiler, Mapping) else {})


def _source_evidence(*, store: Any, root: Path, path: Path) -> tuple[dict[str, Any], str]:
    stat = path.stat()
    signature = store.odylith_context_cache.path_signature(path) | {
        "ctime_ns": stat.st_ctime_ns, "device": stat.st_dev, "inode": stat.st_ino,
    }
    cached = _SOURCE_CACHE.get(str(path))
    if cached is None or cached[0] != signature:
        spec = store.backlog_contract._parse_idea_spec_uncached(
            target=path, repo_root=root, signature=signature,
        )
        fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()
        cached = (signature, dict(spec.metadata), fingerprint)
        if len(_SOURCE_CACHE) >= 128:
            _SOURCE_CACHE.clear()
        _SOURCE_CACHE[str(path)] = cached
    return cached[1], cached[2]


def source_record(
    *, store: Any, root: Path, source_ref: str, role: str,
    observed_utc: str, provenance: Mapping[str, Any],
) -> dict[str, Any]:
    unknown = policy.record(
        role=role, source_ref=source_ref, observed_utc=observed_utc, provenance=provenance
    )
    path = (root / source_ref).resolve() if source_ref else None
    if path is None or not path.is_relative_to(root) or not path.is_file():
        return unknown
    try:
        metadata, fingerprint = _source_evidence(store=store, root=root, path=path)
    except (OSError, UnicodeError):
        return unknown
    evidence_utc = metadata.get("updated", metadata.get("date", metadata.get("created",
        metadata.get("Updated", metadata.get("Date", "")))))
    return policy.record(
        metadata, role=role, validity="current" if role == "current_truth" else "unknown",
        source_ref=source_ref, source_fingerprint=fingerprint,
        evidence_utc=str(evidence_utc),
        observed_utc=observed_utc, provenance=provenance,
    )


def build_starter(
    *, store: Any, root: Path, current: Mapping[str, Any], previous: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]], packets: Sequence[Mapping[str, Any]],
    sessions: Sequence[Mapping[str, Any]],
    observed_utc: str, runtime_state: Mapping[str, Any],
) -> dict[str, Any]:
    path = str(current.get("path", "")).strip() or str(previous.get("path", "")).strip()
    same_path = path == str(previous.get("path", "")).strip()
    evidence = []
    for packet in packets:
        if not policy.independent_selection(
            str(packet.get("selection_state", "")), str(packet.get("selection_ambiguity_class", ""))
        ):
            continue
        paths = packet.get("changed_paths", [])
        if isinstance(paths, list) and any(store._repo_paths_overlap(repo_root=root, left=str(p), right=path) for p in paths):
            workstream = store._payload_workstream_hint(packet)
            if workstream:
                evidence.append((str(packet.get("bootstrapped_at", "")), workstream))
    for session in sessions:
        stamp = str(session.get("evidence_confirmed_utc", ""))
        session_paths = session.get("claimed_paths", [])
        if stamp and isinstance(session_paths, list) and any(store._repo_paths_overlap(repo_root=root, left=str(p), right=path) for p in session_paths):
            workstream = store._workstream_token(str(session.get("workstream", "")))
            if workstream:
                evidence.append((stamp, workstream))
    previous_confirmation = str(previous.get("confirmed_utc", previous.get("last_seen_utc", ""))) if same_path else ""
    evidence = [item for item in evidence if item[0] and item[0] > previous_confirmation]
    evidence.sort(reverse=True)
    workstream = store._workstream_token(str(previous.get("workstream_id", ""))) if same_path else ""
    confirmation = previous_confirmation
    if evidence:
        confirmation, workstream = evidence[0]
    row = next((row for row in rows if store._workstream_token(str(row.get("idea_id", ""))) == workstream), {})
    source_ref = store._parse_link_target(str(row.get("link", "")))
    provenance = projection_provenance(runtime_state)
    previous_record = previous.get("memory_record", {}) if same_path else {}
    if not isinstance(previous_record, Mapping) or previous_record.get("version") != policy.POLICY_VERSION:
        previous_record = {}
    # Carry-forward observation does not reconfirm evidence or its derivation.
    if evidence:
        memory = source_record(
            store=store, root=root, source_ref=source_ref, role="current_truth",
            observed_utc=observed_utc, provenance=provenance,
        )
    else:
        memory = policy.record(previous_record, observed_utc=observed_utc)
    memory["confirmed_utc"] = confirmation
    if row.get("section") in {"finished", "parked"} or row.get("status") in {"Finished", "Done", "Rejected"}:
        memory["role"] = "historical_learning"
    if evidence and len({candidate for stamp, candidate in evidence if stamp == evidence[0][0]}) > 1:
        memory["validity"] = "unknown"
    return {
        "path": path, "seam": str(current.get("seam", previous.get("seam", ""))),
        "component_label": str(current.get("component_label", previous.get("component_label", ""))),
        "workstream_id": workstream,
        "first_seen_utc": (str(previous.get("first_seen_utc", "")) if same_path else "") or confirmation,
        "last_seen_utc": confirmation, "confirmed_utc": confirmation,
        "observed_utc": observed_utc, "status": "current" if current.get("path") else "inferred" if path else "",
        "memory_record": memory,
    }


def load_workstream_hint(
    *, store: Any, root: Path, changed_paths: Sequence[str],
) -> dict[str, Any]:
    paths = store._normalize_changed_path_list(repo_root=root, values=changed_paths)
    if not paths:
        return {}
    snapshot = store._judgment_memory_snapshot_cached(repo_root=root)
    starter = snapshot.get("starter_slice", {})
    if not isinstance(starter, Mapping):
        return {}
    workstream = store._workstream_token(str(starter.get("workstream_id", "")))
    path = store._normalize_repo_token(str(starter.get("path", "")), repo_root=root)
    matched = [p for p in paths if store._repo_paths_overlap(repo_root=root, left=p, right=path)]
    memory = starter.get("memory_record", {})
    if not workstream or not matched or not isinstance(memory, Mapping):
        return {}
    provenance = projection_provenance(store.read_runtime_state(repo_root=root))
    admission = policy.assess(memory, expected_provenance=provenance)
    confirmed = policy.freshness(confirmed_utc=str(memory.get("confirmed_utc", "")))
    if not provenance or not admission["current_authority"] or confirmed["bucket"] not in {"fresh", "recent"}:
        return {}
    source_ref = str(memory.get("source_ref", ""))
    current = source_record(
        store=store, root=root, source_ref=source_ref, role="current_truth",
        observed_utc="", provenance=provenance,
    )
    if current["source_fingerprint"] != memory.get("source_fingerprint") or current["validity"] != "current":
        return {}
    try:
        metadata, fingerprint = _source_evidence(store=store, root=root, path=(root / source_ref).resolve())
    except (OSError, UnicodeError):
        return {}
    source_workstream = store._workstream_token(str(metadata.get("idea_id", "")))
    if fingerprint != memory.get("source_fingerprint") or source_workstream != workstream or str(metadata.get("status", "")).lower() in {
        "finished", "done", "rejected", "parked",
    }:
        return {}
    return {
        "workstream_id": workstream, "slice_path": path, "matched_paths": matched[:4],
        "status": str(starter.get("status", "")), "confidence": "medium",
        "reason": f"Current source and confirmed slice evidence tie `{path}` to `{workstream}`.",
        "memory_record": dict(memory), "memory_admission": "current_source_confirmed",
    }
