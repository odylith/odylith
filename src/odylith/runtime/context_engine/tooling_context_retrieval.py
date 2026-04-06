"""Retrieval-plane helpers for Odylith Context Engine context packets."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.common.consumer_profile import (
    canonical_truth_token,
    truth_path_kind,
    truth_root_tokens,
)

_ACTIONABLE_NOTE_KINDS = {"guardrail", "runbook", "testing", "tooling_policy", "workflow"}


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for item in values:
        token = str(item or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _compact_mapping_list(
    values: Sequence[Mapping[str, Any]],
    *,
    key: str,
    extra_fields: Sequence[str] = (),
    limit: int = 6,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in values:
        if not isinstance(item, Mapping):
            continue
        token = str(item.get(key, "")).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        row = {key: token}
        for field in extra_fields:
            value = item.get(field)
            if value in (None, "", [], {}):
                continue
            row[field] = value
        rows.append(row)
        if len(rows) >= max(1, int(limit)):
            break
    return rows


def _coalesced_string(*values: Any) -> str:
    for value in values:
        token = str(value or "").strip()
        if token:
            return token
    return ""


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return _dedupe_strings([str(item) for item in value])


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _path_prefix_match(path_ref: str, prefix: str) -> bool:
    path_token = str(path_ref or "").strip().strip("/")
    prefix_token = str(prefix or "").strip().strip("/")
    if not path_token or not prefix_token:
        return False
    return path_token == prefix_token or path_token.startswith(prefix_token + "/")


def _path_ref_match(path_ref: str, target_ref: str) -> str:
    path_token = str(path_ref or "").strip().strip("/")
    target_token = str(target_ref or "").strip().strip("/")
    if not path_token or not target_token:
        return ""
    if path_token == target_token:
        return "exact"
    if path_token.startswith(target_token + "/") or target_token.startswith(path_token + "/"):
        return "watch"
    return ""


def _infer_task_families(
    *,
    packet_kind: str,
    changed_paths: Sequence[str],
    explicit_paths: Sequence[str],
    component_ids: Sequence[str],
    family_hint: str = "",
) -> list[str]:
    families: list[str] = []
    normalized_family = str(family_hint or "").strip().lower().replace("-", "_")
    if normalized_family:
        families.append(normalized_family)
    seed_paths = _dedupe_strings([*map(str, changed_paths), *map(str, explicit_paths)])
    for path_ref in seed_paths:
        if path_ref == "AGENTS.md" or path_ref.startswith("agents-guidelines/"):
            families.extend(["workflow", "prompt-hygiene", "grounding"])
        if path_ref.startswith("src/odylith/"):
            families.extend(["implementation", "tooling"])
        if path_ref.startswith("src/odylith/runtime/context_engine/"):
            families.extend(["tooling", "retrieval", "maintainer-loop"])
        if path_ref.startswith("tests/"):
            families.extend(["testing", "verification"])
        if path_ref.startswith("docs/runbooks/"):
            families.extend(["operations"])
        if path_ref.startswith("odylith/radar/") or path_ref.startswith("odylith/technical-plans/") or path_ref.startswith("odylith/casebook/bugs/"):
            families.extend(["workflow", "grounding", "governance"])
        if path_ref.startswith("infra/") or path_ref.startswith("mk/"):
            families.extend(["deployment", "ops-safety"])
        if path_ref.startswith(("contracts/", "odylith/runtime/contracts/")):
            families.extend(["contracts"])
    if str(packet_kind or "").strip() in {"impact", "session_brief", "bootstrap_session"}:
        families.append("tooling")
    if "odylith-context-engine" in {str(token).strip() for token in component_ids if str(token).strip()}:
        families.extend(["tooling", "retrieval", "maintainer-loop"])
    return _dedupe_strings(families)


def _infer_chunk_task_families(chunk: Mapping[str, Any]) -> list[str]:
    families = _string_list(chunk.get("task_families"))
    note_kind = str(chunk.get("note_kind", "")).strip().lower().replace("-", "_")
    canonical_source = str(chunk.get("canonical_source", "")).strip().lower()
    if note_kind == "workflow":
        families.extend(["workflow", "grounding"])
    elif note_kind == "tooling_policy":
        families.extend(["tooling", "retrieval"])
    elif note_kind == "runbook":
        families.extend(["operations"])
    elif note_kind == "architecture":
        families.extend(["architecture", "boundary-review"])
    elif note_kind == "engineering_standard":
        families.extend(["implementation", "tooling"])
    elif note_kind == "testing":
        families.extend(["testing", "verification"])
    elif note_kind == "pitfall":
        families.extend(["workflow", "prompt-hygiene"])
    elif note_kind == "guardrail":
        families.extend(["ops-safety", "workflow"])
    if canonical_source.endswith("/workflow.md"):
        families.extend(["workflow", "grounding"])
    elif canonical_source.endswith("/tooling.md"):
        families.extend(["tooling", "retrieval"])
    elif canonical_source.endswith("/runbook_index.md"):
        families.extend(["operations"])
    elif canonical_source.endswith("/architecture.md"):
        families.extend(["architecture", "boundary-review"])
    elif canonical_source.endswith("/testing.md") or canonical_source.endswith("/testing_playbook.md"):
        families.extend(["testing", "verification"])
    elif canonical_source.endswith("/pitfalls.md"):
        families.extend(["workflow", "prompt-hygiene"])
    return _dedupe_strings(families)


def _compact_guidance_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    relevance = row.get("relevance", {})
    if not isinstance(relevance, Mapping):
        relevance = {}
    return {
        "score": _int_value(relevance.get("score")),
        "match_tier": str(relevance.get("match_tier", "")).strip(),
        "matched_by": _string_list(relevance.get("matched_by", []))[:3],
        "matched_paths": _string_list(relevance.get("matched_paths", []))[:2],
        "matched_components": _string_list(relevance.get("matched_components", []))[:2],
        "matched_workstreams": _string_list(relevance.get("matched_workstreams", []))[:2],
    }


def _guidance_actionability(row: Mapping[str, Any]) -> dict[str, Any]:
    evidence_summary = _compact_guidance_evidence(row)
    note_kind = str(row.get("note_kind", "")).strip().lower().replace("-", "_")
    canonical_source = str(row.get("canonical_source", "")).strip()
    chunk_path = str(row.get("chunk_path", "")).strip()
    signals: list[str] = []
    if canonical_source or chunk_path:
        signals.append("read_source")
    if evidence_summary["matched_paths"]:
        signals.append("follow_matched_path")
    if note_kind in _ACTIONABLE_NOTE_KINDS:
        signals.append(note_kind)
    risk_class = str(row.get("risk_class", "")).strip()
    if risk_class:
        signals.append("risk_guardrail")
    return {
        "actionable": bool(signals),
        "direct": evidence_summary["match_tier"] in {"direct_path", "anchored_context"},
        "read_path": canonical_source or chunk_path,
        "signals": _dedupe_strings(signals),
    }


def _decorate_guidance_row(row: Mapping[str, Any]) -> dict[str, Any]:
    decorated = dict(row)
    decorated["evidence_summary"] = _compact_guidance_evidence(decorated)
    decorated["actionability"] = _guidance_actionability(decorated)
    return decorated


def _guidance_signal_surface_count(row: Mapping[str, Any]) -> int:
    evidence_summary = row.get("evidence_summary", {})
    if not isinstance(evidence_summary, Mapping):
        evidence_summary = _compact_guidance_evidence(row)
    actionability = row.get("actionability", {})
    if not isinstance(actionability, Mapping):
        actionability = _guidance_actionability(row)
    return (
        min(len(_string_list(evidence_summary.get("matched_by", []))), 4)
        + min(len(_string_list(evidence_summary.get("matched_paths", []))), 2)
        + min(len(_string_list(evidence_summary.get("matched_components", []))), 2)
        + min(len(_string_list(evidence_summary.get("matched_workstreams", []))), 2)
        + min(len(_string_list(evidence_summary.get("matched_task_families", []))), 2)
        + min(len(_string_list(actionability.get("signals", []))), 3)
        + (1 if str(row.get("risk_class", "")).strip() else 0)
        + (1 if str(row.get("canonical_source", "")).strip() or str(actionability.get("read_path", "")).strip() else 0)
    )


def _guidance_actionability_rank(row: Mapping[str, Any]) -> int:
    actionability = row.get("actionability", {})
    if not isinstance(actionability, Mapping):
        actionability = _guidance_actionability(row)
    score = 0
    if bool(actionability.get("actionable")):
        score += 2
    if bool(actionability.get("direct")):
        score += 2
    if str(actionability.get("read_path", "")).strip():
        score += 1
    score += min(len(_string_list(actionability.get("signals", []))), 3)
    return score


def _guidance_rank_key(row: Mapping[str, Any]) -> tuple[int, int, int, int, int, str]:
    evidence_summary = row.get("evidence_summary", {})
    if not isinstance(evidence_summary, Mapping):
        evidence_summary = _compact_guidance_evidence(row)
    match_tier = str(evidence_summary.get("match_tier", row.get("match_tier", ""))).strip()
    match_tier_order = {
        "direct_path": 4,
        "anchored_context": 3,
        "canonical_source": 2,
        "note_match": 1,
        "task_family": 0,
    }
    return (
        -_int_value(evidence_summary.get("score", row.get("score"))),
        -_guidance_actionability_rank(row),
        -_guidance_signal_surface_count(row),
        -(1 if str(row.get("risk_class", "")).strip() else 0),
        -match_tier_order.get(match_tier, 0),
        str(row.get("chunk_id", "")),
    )


def _score_note_chunk(note: Mapping[str, Any]) -> tuple[int, dict[str, Any]]:
    relevance = note.get("relevance", {})
    matched_by = _string_list(note.get("matched_by"))
    matched_paths = _string_list(note.get("matched_paths"))
    matched_components = _string_list(note.get("components"))
    matched_workstreams = _string_list(note.get("workstreams"))
    exact_hits = _int_value(relevance.get("exact_path_hits")) if isinstance(relevance, Mapping) else 0
    watch_hits = _int_value(relevance.get("watch_path_hits")) if isinstance(relevance, Mapping) else 0
    component_hits = _int_value(relevance.get("component_hits")) if isinstance(relevance, Mapping) else len(matched_components)
    workstream_hits = _int_value(relevance.get("workstream_hits")) if isinstance(relevance, Mapping) else len(matched_workstreams)
    score = (
        exact_hits * 55
        + watch_hits * 28
        + component_hits * 22
        + workstream_hits * 26
        + (12 if "path" in matched_by else 0)
        + (8 if "component" in matched_by else 0)
        + (10 if "workstream" in matched_by else 0)
    )
    match_tier = "note_match"
    if exact_hits or watch_hits:
        match_tier = "direct_path"
    elif component_hits or workstream_hits:
        match_tier = "anchored_context"
    return score, {
        "score": score,
        "matched_by": matched_by,
        "matched_paths": matched_paths[:3],
        "matched_components": matched_components[:3],
        "matched_workstreams": matched_workstreams[:3],
        "matched_task_families": [],
        "match_tier": match_tier,
    }


def _chunk_id_from_note(note: Mapping[str, Any], metadata: Mapping[str, Any]) -> str:
    chunk_id = _coalesced_string(note.get("chunk_id"), metadata.get("chunk_id"))
    if chunk_id:
        return chunk_id
    note_id = str(note.get("note_id", "")).strip()
    marker = ":chunk:"
    if marker in note_id:
        return note_id.split(marker, 1)[1].strip()
    return ""


def _note_selected_guidance_chunks(
    engineering_notes: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for note_kind in sorted(engineering_notes):
        notes = engineering_notes.get(note_kind, [])
        if not isinstance(notes, list):
            continue
        for note in notes:
            if not isinstance(note, Mapping):
                continue
            metadata = note.get("metadata", {})
            if not isinstance(metadata, Mapping):
                metadata = {}
            source_mode = _coalesced_string(note.get("source_mode"), metadata.get("source_mode"))
            if source_mode != "guidance_chunk":
                continue
            chunk_id = _chunk_id_from_note(note, metadata)
            if not chunk_id or chunk_id in seen:
                continue
            seen.add(chunk_id)
            score, relevance = _score_note_chunk(note)
            rows.append(
                {
                    "chunk_id": chunk_id,
                    "note_kind": _coalesced_string(note.get("kind"), note.get("note_kind"), note_kind),
                    "title": str(note.get("title", "")).strip(),
                    "summary": str(note.get("summary", "")).strip(),
                    "canonical_source": _coalesced_string(note.get("canonical_source"), metadata.get("canonical_source"), note.get("source_path")),
                    "chunk_path": _coalesced_string(note.get("chunk_path"), metadata.get("chunk_path")),
                    "risk_class": _coalesced_string(note.get("risk_class"), metadata.get("risk_class")),
                    "task_families": _string_list(note.get("task_families"))
                    or _string_list(metadata.get("task_families")),
                    "source_modes": ["note"],
                    "relevance": relevance,
                }
            )
    return rows


def _score_catalog_chunk(
    chunk: Mapping[str, Any],
    *,
    changed_paths: Sequence[str],
    explicit_paths: Sequence[str],
    component_ids: Sequence[str],
    workstream_ids: Sequence[str],
    task_families: Sequence[str],
    docs: Sequence[str],
) -> dict[str, Any] | None:
    path_refs = _string_list(chunk.get("path_refs"))
    path_prefixes = _string_list(chunk.get("path_prefixes"))
    component_affinity = _string_list(chunk.get("component_affinity"))
    chunk_workstreams = _string_list(chunk.get("workstreams"))
    chunk_task_families = _infer_chunk_task_families(chunk)
    matched_paths: list[str] = []
    direct_hits = 0
    prefix_hits = 0
    canonical_source_hits = 0
    for path_ref in _dedupe_strings([*map(str, changed_paths), *map(str, explicit_paths)]):
        if any(_path_ref_match(path_ref, target) == "exact" for target in path_refs):
            direct_hits += 1
            matched_paths.append(path_ref)
            continue
        if any(_path_prefix_match(path_ref, prefix) for prefix in path_prefixes):
            prefix_hits += 1
            matched_paths.append(path_ref)
            continue
        canonical_source = str(chunk.get("canonical_source", "")).strip()
        if canonical_source and _path_ref_match(path_ref, canonical_source) == "exact":
            canonical_source_hits += 1
            matched_paths.append(path_ref)
    matched_components = sorted(set(component_affinity).intersection(component_ids))
    matched_workstreams = sorted(set(chunk_workstreams).intersection(workstream_ids))
    matched_task_families = sorted(set(chunk_task_families).intersection(task_families))
    docs_hits = 0
    canonical_source = str(chunk.get("canonical_source", "")).strip()
    if canonical_source and canonical_source in {str(token).strip() for token in docs if str(token).strip()}:
        docs_hits = 1
    score = (
        direct_hits * 120
        + prefix_hits * 95
        + canonical_source_hits * 70
        + len(matched_components) * 48
        + len(matched_workstreams) * 54
        + len(matched_task_families) * 16
        + docs_hits * 18
    )
    if score <= 0:
        return None
    matched_by: list[str] = []
    if direct_hits or prefix_hits or canonical_source_hits:
        matched_by.append("path")
    if matched_components:
        matched_by.append("component")
    if matched_workstreams:
        matched_by.append("workstream")
    if matched_task_families:
        matched_by.append("task_family")
    match_tier = "task_family"
    if direct_hits or prefix_hits:
        match_tier = "direct_path"
    elif matched_components or matched_workstreams:
        match_tier = "anchored_context"
    elif canonical_source_hits or docs_hits:
        match_tier = "canonical_source"
    return {
        "chunk_id": str(chunk.get("chunk_id", "")).strip(),
        "note_kind": str(chunk.get("note_kind", "")).strip(),
        "title": str(chunk.get("title", "")).strip(),
        "summary": str(chunk.get("summary", "")).strip(),
        "canonical_source": canonical_source,
        "chunk_path": str(chunk.get("chunk_path", "")).strip(),
        "risk_class": str(chunk.get("risk_class", "")).strip(),
        "task_families": chunk_task_families,
        "source_modes": ["catalog"],
        "relevance": {
            "score": score,
            "matched_by": matched_by,
            "matched_paths": matched_paths[:3],
            "matched_components": matched_components[:3],
            "matched_workstreams": matched_workstreams[:3],
            "matched_task_families": matched_task_families[:3],
            "match_tier": match_tier,
        },
    }


def _merge_guidance_rows(base: dict[str, Any], incoming: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for field in ("note_kind", "title", "summary", "canonical_source", "chunk_path", "risk_class"):
        merged[field] = _coalesced_string(merged.get(field), incoming.get(field))
    merged["task_families"] = _dedupe_strings(
        [*map(str, merged.get("task_families", [])), *map(str, incoming.get("task_families", []))]
    )
    merged["source_modes"] = _dedupe_strings(
        [*map(str, merged.get("source_modes", [])), *map(str, incoming.get("source_modes", []))]
    )
    base_relevance = dict(merged.get("relevance", {})) if isinstance(merged.get("relevance"), Mapping) else {}
    incoming_relevance = dict(incoming.get("relevance", {})) if isinstance(incoming.get("relevance"), Mapping) else {}
    base_relevance["score"] = max(_int_value(base_relevance.get("score")), _int_value(incoming_relevance.get("score")))
    match_tier_order = {
        "direct_path": 3,
        "anchored_context": 2,
        "canonical_source": 1,
        "task_family": 0,
        "note_match": 1,
    }
    current_tier = str(base_relevance.get("match_tier", "")).strip()
    incoming_tier = str(incoming_relevance.get("match_tier", "")).strip()
    if match_tier_order.get(incoming_tier, -1) > match_tier_order.get(current_tier, -1):
        base_relevance["match_tier"] = incoming_tier
    elif current_tier:
        base_relevance["match_tier"] = current_tier
    base_relevance["matched_by"] = _dedupe_strings(
        [*map(str, base_relevance.get("matched_by", [])), *map(str, incoming_relevance.get("matched_by", []))]
    )[:4]
    for key in ("matched_paths", "matched_components", "matched_workstreams", "matched_task_families"):
        base_relevance[key] = _dedupe_strings(
            [*map(str, base_relevance.get(key, [])), *map(str, incoming_relevance.get(key, []))]
        )[:4]
    merged["relevance"] = base_relevance
    return _decorate_guidance_row(merged)


def selected_guidance_chunks(
    engineering_notes: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    guidance_catalog: Mapping[str, Any] | None = None,
    packet_kind: str = "",
    family_hint: str = "",
    changed_paths: Sequence[str] = (),
    explicit_paths: Sequence[str] = (),
    docs: Sequence[str] = (),
    components: Sequence[Mapping[str, Any]] = (),
    selected_workstreams: Sequence[Mapping[str, Any]] = (),
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Return compact guidance-chunk rows selected into the packet."""

    component_ids = [
        str(row.get("entity_id", "")).strip()
        for row in components
        if isinstance(row, Mapping) and str(row.get("entity_id", "")).strip()
    ]
    workstream_ids = [
        str(row.get("entity_id", "")).strip().upper()
        for row in selected_workstreams
        if isinstance(row, Mapping) and str(row.get("entity_id", "")).strip()
    ]
    task_families = _infer_task_families(
        packet_kind=packet_kind,
        family_hint=family_hint,
        changed_paths=changed_paths,
        explicit_paths=explicit_paths,
        component_ids=component_ids,
    )
    rows_by_id: dict[str, dict[str, Any]] = {}
    catalog_chunks = guidance_catalog.get("chunks", []) if isinstance(guidance_catalog, Mapping) else []
    if isinstance(catalog_chunks, list):
        for item in catalog_chunks:
            if not isinstance(item, Mapping):
                continue
            scored = _score_catalog_chunk(
                item,
                changed_paths=changed_paths,
                explicit_paths=explicit_paths,
                component_ids=component_ids,
                workstream_ids=workstream_ids,
                task_families=task_families,
                docs=docs,
            )
            if scored is None:
                continue
            chunk_id = str(scored.get("chunk_id", "")).strip()
            if not chunk_id:
                continue
            if chunk_id in rows_by_id:
                rows_by_id[chunk_id] = _merge_guidance_rows(rows_by_id.get(chunk_id, {}), scored)
            else:
                rows_by_id[chunk_id] = _decorate_guidance_row(scored)
    for note_row in _note_selected_guidance_chunks(engineering_notes):
        chunk_id = str(note_row.get("chunk_id", "")).strip()
        if not chunk_id:
            continue
        if chunk_id in rows_by_id:
            rows_by_id[chunk_id] = _merge_guidance_rows(rows_by_id.get(chunk_id, {}), note_row)
        else:
            rows_by_id[chunk_id] = _decorate_guidance_row(note_row)
    ranked = list(rows_by_id.values())
    ranked.sort(key=_guidance_rank_key)
    return ranked[: max(1, int(limit))]


def compact_guidance_brief(
    selected_guidance_chunks: Sequence[Mapping[str, Any]],
    *,
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Return small, prompt-useful guidance highlights for the final packet."""

    rows: list[dict[str, Any]] = []
    for item in selected_guidance_chunks[: max(1, int(limit))]:
        if not isinstance(item, Mapping):
            continue
        evidence_summary = item.get("evidence_summary", {})
        if not isinstance(evidence_summary, Mapping):
            evidence_summary = _compact_guidance_evidence(item)
        actionability = item.get("actionability", {})
        if not isinstance(actionability, Mapping):
            actionability = _guidance_actionability(item)
        rows.append(
            {
                "chunk_id": str(item.get("chunk_id", "")).strip(),
                "title": str(item.get("title", "")).strip(),
                "summary": str(item.get("summary", "")).strip(),
                "canonical_source": str(item.get("canonical_source", "")).strip(),
                "risk_class": str(item.get("risk_class", "")).strip(),
                "match_tier": str(evidence_summary.get("match_tier", "")).strip(),
                "matched_by": _string_list(evidence_summary.get("matched_by", []))[:3],
                "matched_paths": _string_list(evidence_summary.get("matched_paths", []))[:2],
                "evidence_summary": {
                    "score": _int_value(evidence_summary.get("score")),
                    "match_tier": str(evidence_summary.get("match_tier", "")).strip(),
                    "matched_paths": _string_list(evidence_summary.get("matched_paths", []))[:2],
                },
                "actionability": {
                    "actionable": bool(actionability.get("actionable")),
                    "direct": bool(actionability.get("direct")),
                    "read_path": str(actionability.get("read_path", "")).strip(),
                    "signals": _string_list(actionability.get("signals", []))[:3],
                },
            }
        )
    return [row for row in rows if any(value not in ("", [], {}, None) for value in row.values())]


def prioritize_docs(
    docs: Sequence[str],
    *,
    repo_root: Path | None = None,
    selected_guidance_chunks: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    changed_paths: Sequence[str],
) -> list[str]:
    """Prefer high-signal docs without widening the packet."""

    root = repo_root or Path.cwd()
    truth_roots = truth_root_tokens(repo_root=root)
    component_ids = {
        str(row.get("entity_id", "")).strip()
        for row in components
        if isinstance(row, Mapping) and str(row.get("entity_id", "")).strip()
    }
    guidance_sources = {
        canonical_truth_token(str(item.get("canonical_source", "")).strip(), repo_root=root)
        for item in selected_guidance_chunks
        if isinstance(item, Mapping) and str(item.get("canonical_source", "")).strip()
    }
    guidance_paths = {
        canonical_truth_token(str(item.get("chunk_path", "")).strip(), repo_root=root)
        for item in selected_guidance_chunks
        if isinstance(item, Mapping) and str(item.get("chunk_path", "")).strip()
    }
    changed = {canonical_truth_token(str(token).strip(), repo_root=root) for token in changed_paths if str(token).strip()}
    scored: list[tuple[tuple[int, int], str]] = []
    for index, raw_doc in enumerate(docs):
        doc = canonical_truth_token(str(raw_doc).strip(), repo_root=root)
        if not doc:
            continue
        doc_kind = truth_path_kind(doc, repo_root=root, truth_roots=truth_roots)
        score = 0
        if doc in changed:
            score += 110
        if doc in guidance_sources:
            score += 95
        if doc in guidance_paths:
            score += 70
        if doc_kind in {"component_spec", "component_forensics"}:
            score += 50
        if doc_kind == "runbook":
            score += 35
        if doc.startswith("agents-guidelines/"):
            score += 24
        if any(component_id and component_id in doc for component_id in component_ids):
            score += 40
        scored.append(((-score, index), doc))
    scored.sort(key=lambda item: item[0])
    return _dedupe_strings([doc for _score, doc in scored])


def prioritize_bootstrap_docs(
    docs: Sequence[str],
    *,
    repo_root: Path | None = None,
    selected_guidance_chunks: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    changed_paths: Sequence[str],
) -> list[str]:
    """Preserve spec/runbook evidence before duplicate guidance-backed docs in bootstrap packets."""

    root = repo_root or Path.cwd()
    truth_roots = truth_root_tokens(repo_root=root)
    prioritized = prioritize_docs(
        docs,
        repo_root=root,
        selected_guidance_chunks=selected_guidance_chunks,
        components=components,
        changed_paths=changed_paths,
    )
    guidance_refs: set[str] = set()
    for row in selected_guidance_chunks:
        if not isinstance(row, Mapping):
            continue
        for key in ("canonical_source", "chunk_path"):
            token = canonical_truth_token(str(row.get(key, "")).strip(), repo_root=root)
            if token:
                guidance_refs.add(token)
        actionability = dict(row.get("actionability", {})) if isinstance(row.get("actionability"), Mapping) else {}
        read_path = canonical_truth_token(str(actionability.get("read_path", "")).strip(), repo_root=root)
        if read_path:
            guidance_refs.add(read_path)
    scored: list[tuple[tuple[int, int], str]] = []
    for index, raw_doc in enumerate(prioritized):
        doc = str(raw_doc).strip()
        if not doc:
            continue
        doc_kind = truth_path_kind(doc, repo_root=root, truth_roots=truth_roots)
        score = 0
        if doc_kind in {"component_spec", "component_forensics"}:
            score += 120
        if doc_kind == "runbook":
            score += 95
        if doc.startswith("agents-guidelines/") and not doc.startswith("agents-guidelines/indexable/"):
            score += 28
        if doc not in guidance_refs:
            score += 42
        if doc in guidance_refs:
            score -= 36
        if doc.startswith("agents-guidelines/indexable/"):
            score -= 24
        scored.append(((-score, index), doc))
    scored.sort(key=lambda item: item[0])
    return _dedupe_strings([doc for _score, doc in scored])


def build_working_memory_tiers(
    *,
    packet_kind: str,
    repo_root: Path | None = None,
    changed_paths: Sequence[str],
    explicit_paths: Sequence[str],
    docs: Sequence[str],
    recommended_commands: Sequence[str],
    recommended_tests: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    selected_workstreams: Sequence[Mapping[str, Any]],
    selected_guidance_chunks: Sequence[Mapping[str, Any]],
    session_id: str = "",
    selection_state: str = "",
) -> dict[str, Any]:
    """Describe the cold/warm/hot/scratch memory tiers for one packet."""

    guidance_limit = 4
    if str(packet_kind or "").strip() == "session_brief":
        guidance_limit = 3
    elif str(packet_kind or "").strip() == "bootstrap_session":
        guidance_limit = 2
    cold_sources = [
        "AGENTS.md",
        "agents-guidelines/indexable-guidance-chunks.v1.json",
        "odylith/registry/source/component_registry.v1.json",
        "odylith/radar/source/INDEX.md",
        "odylith/technical-plans/INDEX.md",
        "odylith/casebook/bugs/INDEX.md",
    ]
    warm_docs = [canonical_truth_token(str(token).strip(), repo_root=repo_root) for token in docs[:6] if str(token).strip()]
    warm_components = _compact_mapping_list(components, key="entity_id", extra_fields=("title",), limit=4)
    warm_workstreams = _compact_mapping_list(selected_workstreams, key="entity_id", extra_fields=("title",), limit=4)
    hot_tests = _compact_mapping_list(recommended_tests, key="path", extra_fields=("nodeid", "reason"), limit=4)
    return {
        "cold": {
            "description": "Authoritative repo contracts and routing inputs.",
            "sources": cold_sources,
        },
        "warm": {
            "description": "Retrieved guidance and context selected for this slice.",
            "guidance_chunks": compact_guidance_brief(selected_guidance_chunks, limit=guidance_limit),
            "docs": warm_docs,
            "components": warm_components,
            "workstreams": warm_workstreams,
        },
        "hot": {
            "description": "Immediate execution context carried into the current packet.",
            "packet_kind": str(packet_kind or "").strip(),
            "changed_paths": _dedupe_strings([canonical_truth_token(str(token), repo_root=repo_root) for token in changed_paths]),
            "explicit_paths": _dedupe_strings([canonical_truth_token(str(token), repo_root=repo_root) for token in explicit_paths]),
            "recommended_commands": [str(token).strip() for token in recommended_commands[:4] if str(token).strip()],
            "recommended_tests": hot_tests,
        },
        "scratch": {
            "description": "Ephemeral session-local state that should not become canonical truth.",
            "session_id": str(session_id or "").strip(),
            "selection_state": str(selection_state or "").strip(),
        },
    }


def compact_retrieval_bundle(
    *,
    packet_kind: str,
    family_hint: str = "",
    repo_root: Path | None = None,
    changed_paths: Sequence[str],
    explicit_paths: Sequence[str],
    docs: Sequence[str],
    recommended_commands: Sequence[str],
    recommended_tests: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    selected_workstreams: Sequence[Mapping[str, Any]],
    engineering_notes: Mapping[str, Sequence[Mapping[str, Any]]],
    guidance_catalog: Mapping[str, Any] | None = None,
    session_id: str = "",
    selection_state: str = "",
    build_working_memory: bool = True,
) -> dict[str, Any]:
    """Build a compact retrieval bundle for routing and packet assembly."""

    guidance_brief_limit = 4
    if str(packet_kind or "").strip() == "session_brief":
        guidance_brief_limit = 3
    elif str(packet_kind or "").strip() == "bootstrap_session":
        guidance_brief_limit = 2
    guidance_chunks = selected_guidance_chunks(
        engineering_notes,
        guidance_catalog=guidance_catalog,
        packet_kind=packet_kind,
        family_hint=family_hint,
        changed_paths=changed_paths,
        explicit_paths=explicit_paths,
        docs=docs,
        components=components,
        selected_workstreams=selected_workstreams,
    )
    return {
        "selected_guidance_chunks": guidance_chunks,
        "guidance_brief": compact_guidance_brief(guidance_chunks, limit=guidance_brief_limit),
        "prioritized_docs": prioritize_docs(
            docs,
            repo_root=repo_root,
            selected_guidance_chunks=guidance_chunks,
            components=components,
            changed_paths=changed_paths,
        ),
        "working_memory_tiers": build_working_memory_tiers(
            packet_kind=packet_kind,
            repo_root=repo_root,
            changed_paths=changed_paths,
            explicit_paths=explicit_paths,
            docs=docs,
            recommended_commands=recommended_commands,
            recommended_tests=recommended_tests,
            components=components,
            selected_workstreams=selected_workstreams,
            selected_guidance_chunks=guidance_chunks,
            session_id=session_id,
            selection_state=selection_state,
        )
        if build_working_memory
        else {},
    }


__all__ = [
    "build_working_memory_tiers",
    "compact_guidance_brief",
    "compact_retrieval_bundle",
    "prioritize_bootstrap_docs",
    "prioritize_docs",
    "selected_guidance_chunks",
]
