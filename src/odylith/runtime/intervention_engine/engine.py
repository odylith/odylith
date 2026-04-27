"""Engine helpers for the Odylith intervention engine layer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.common.json_objects import load_json_object as _load_json
from odylith.runtime.governance import component_registry_intelligence as component_registry
from odylith.runtime.governance import workstream_inference
from odylith.runtime.intervention_engine.contract import CaptureBundle
from odylith.runtime.intervention_engine.contract import GovernanceFact
from odylith.runtime.intervention_engine.contract import InterventionBundle
from odylith.runtime.intervention_engine.contract import InterventionCandidate
from odylith.runtime.intervention_engine.contract import ObservationEnvelope
from odylith.runtime.intervention_engine import alignment_evidence
from odylith.runtime.intervention_engine import continuity_runtime
from odylith.runtime.intervention_engine import fact_producer_runtime
from odylith.runtime.intervention_engine import moment_runtime
from odylith.runtime.intervention_engine import proposal_action_selection
from odylith.runtime.intervention_engine import signal_kernel
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.intervention_engine import visibility_contract
from odylith.runtime.intervention_engine import voice
from odylith.runtime.intervention_engine import voice_contract


_normalize_string = visibility_contract.normalize_string
_normalize_token = visibility_contract.normalize_token
_normalize_string_list = visibility_contract.normalize_string_list


_REPO_TRUTH_CACHE: dict[tuple[str, tuple[Any, ...]], dict[str, Any]] = {}


def _path_signature(path: Path) -> tuple[str, int, int]:
    try:
        stat = path.stat()
    except OSError:
        return (path.as_posix(), -1, -1)
    size = int(stat.st_size) if path.is_file() else 0
    return (path.as_posix(), int(stat.st_mtime_ns), size)


def _bug_catalog_signature(bugs_root: Path) -> tuple[tuple[str, int, int], ...]:
    rows: list[tuple[str, int, int]] = []
    if not bugs_root.is_dir():
        return tuple(rows)
    for path in sorted(bugs_root.glob("*.md")):
        rows.append(_path_signature(path))
    return tuple(rows)


def _component_index(repo_root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    manifest_path = repo_root / component_registry.DEFAULT_MANIFEST_PATH
    catalog_path = repo_root / component_registry.DEFAULT_CATALOG_PATH
    ideas_root = repo_root / component_registry.DEFAULT_IDEAS_ROOT
    components, alias_lookup, _diagnostics = component_registry.build_component_index(
        repo_root=repo_root,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
        ideas_root=ideas_root,
    )
    return components, alias_lookup


def _traceability_state(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, set[str]]]:
    traceability = _load_json(repo_root / "odylith" / "radar" / "traceability-graph.v1.json")
    mermaid_catalog = _load_json(repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json")
    ws_index = workstream_inference.collect_workstream_path_index_from_traceability(
        repo_root=repo_root,
        traceability_graph=traceability,
        mermaid_catalog=mermaid_catalog,
    )
    return traceability, mermaid_catalog, ws_index


def _bug_index(repo_root: Path) -> dict[str, dict[str, str]]:
    bugs_root = repo_root / "odylith" / "casebook" / "bugs"
    rows: dict[str, dict[str, str]] = {}
    if not bugs_root.is_dir():
        return rows
    for path in sorted(bugs_root.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        bug_id = ""
        title = ""
        for line in text.splitlines():
            stripped = str(line or "").strip().lstrip("- ").strip()
            if stripped.startswith("Bug ID:"):
                bug_id = _normalize_string(stripped.split(":", 1)[1]).upper()
            if stripped.startswith("Description:"):
                title = _normalize_string(stripped.split(":", 1)[1])
            if bug_id and title:
                break
        if bug_id:
            rows[bug_id] = {
                "bug_id": bug_id,
                "title": title or path.stem,
                "path": path.relative_to(repo_root).as_posix(),
            }
    return rows


def _repo_truth(repo_root: Path) -> dict[str, Any]:
    manifest_path = repo_root / component_registry.DEFAULT_MANIFEST_PATH
    component_catalog_path = repo_root / component_registry.DEFAULT_CATALOG_PATH
    ideas_root = repo_root / component_registry.DEFAULT_IDEAS_ROOT
    traceability_path = repo_root / "odylith" / "radar" / "traceability-graph.v1.json"
    diagram_catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    bugs_root = repo_root / "odylith" / "casebook" / "bugs"
    cache_key = (
        repo_root.as_posix(),
        (
            _path_signature(manifest_path),
            _path_signature(component_catalog_path),
            _path_signature(ideas_root),
            _path_signature(traceability_path),
            _path_signature(diagram_catalog_path),
            *_bug_catalog_signature(bugs_root),
        ),
    )
    cached = _REPO_TRUTH_CACHE.get(cache_key)
    if cached is not None:
        return cached
    components, alias_lookup = _component_index(repo_root)
    traceability, mermaid_catalog, ws_index = _traceability_state(repo_root)
    bug_rows = _bug_index(repo_root)
    workstream_rows = {
        _normalize_string(row.get("idea_id")): dict(row)
        for row in traceability.get("workstreams", [])
        if isinstance(row, Mapping) and _normalize_string(row.get("idea_id"))
    }
    payload = {
        "components": components,
        "alias_lookup": alias_lookup,
        "traceability": traceability,
        "mermaid_catalog": mermaid_catalog,
        "ws_index": ws_index,
        "bug_rows": bug_rows,
        "workstream_rows": workstream_rows,
    }
    _REPO_TRUTH_CACHE.clear()
    _REPO_TRUTH_CACHE[cache_key] = payload
    return payload


def _path_components(*, changed_paths: Sequence[str], components: Mapping[str, Any]) -> list[str]:
    matched: set[str] = set()
    trie = component_registry._build_component_path_prefix_trie(  # noqa: SLF001
        {
            component_id: component_registry._entry_to_mutable(entry)  # noqa: SLF001
            for component_id, entry in components.items()
        },
        include_spec_ref=True,
    )
    for path in changed_paths:
        for token in component_registry.equivalent_component_artifact_tokens(path):
            matched.update(component_registry._lookup_component_ids_for_path_token(token, trie=trie))  # noqa: SLF001
    return sorted(matched)


def _path_diagrams(*, changed_paths: Sequence[str], mermaid_catalog: Mapping[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    diagrams = mermaid_catalog.get("diagrams", [])
    if not isinstance(diagrams, list):
        return rows
    for row in diagrams:
        if not isinstance(row, Mapping):
            continue
        refs = _normalize_string_list(row.get("change_watch_paths"))
        refs.extend(_normalize_string_list([row.get("source_mmd"), row.get("source_svg"), row.get("source_png")]))
        matched = False
        for changed in changed_paths:
            normalized = workstream_inference.normalize_repo_token(changed)
            if not normalized:
                continue
            for ref in refs:
                token = workstream_inference.normalize_repo_token(ref)
                if token and (normalized == token or normalized.startswith(f"{token}/") or token.startswith(f"{normalized}/")):
                    matched = True
                    break
            if matched:
                break
        if matched:
            rows.append(
                {
                    "kind": "diagram",
                    "id": _normalize_string(row.get("diagram_id")),
                    "label": _normalize_string(row.get("title")),
                    "path": _normalize_string(row.get("source_mmd")),
                }
            )
    return rows


def _workstreams_for_paths(*, changed_paths: Sequence[str], ws_index: Mapping[str, set[str]]) -> list[str]:
    return workstream_inference.map_paths_to_workstreams(changed_paths, ws_index)


def _component_workstreams(*, component_ids: Sequence[str], components: Mapping[str, Any]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for component_id in component_ids:
        entry = components.get(component_id)
        raw_workstreams = entry.get("workstreams") if isinstance(entry, Mapping) else getattr(entry, "workstreams", ())
        for token in _normalize_string_list(raw_workstreams):
            if token in seen:
                continue
            seen.add(token)
            rows.append(token)
    return rows


def _repo_lookup(
    *,
    repo_root: Path,
    observation: ObservationEnvelope,
) -> dict[str, Any]:
    repo_truth = _repo_truth(repo_root)
    components = dict(repo_truth.get("components", {}))
    alias_lookup = dict(repo_truth.get("alias_lookup", {}))
    traceability = dict(repo_truth.get("traceability", {}))
    mermaid_catalog = dict(repo_truth.get("mermaid_catalog", {}))
    ws_index = dict(repo_truth.get("ws_index", {}))
    bug_rows = dict(repo_truth.get("bug_rows", {}))
    workstream_rows = dict(repo_truth.get("workstream_rows", {}))
    target_refs = alignment_evidence.active_target_refs(observation)
    workstream_ids = {
        ref["id"]
        for ref in target_refs
        if ref.get("kind") == "workstream" and _normalize_string(ref.get("id"))
    }
    workstream_ids.update(_workstreams_for_paths(changed_paths=observation.changed_paths, ws_index=ws_index))
    bug_ids = {
        ref["id"]
        for ref in target_refs
        if ref.get("kind") == "bug" and _normalize_string(ref.get("id"))
    }
    diagram_refs = [
        ref
        for ref in target_refs
        if ref.get("kind") == "diagram" and _normalize_string(ref.get("id"))
    ]
    diagram_refs.extend(_path_diagrams(changed_paths=observation.changed_paths, mermaid_catalog=mermaid_catalog))
    component_ids = {
        ref["id"]
        for ref in target_refs
        if ref.get("kind") == "component" and _normalize_string(ref.get("id"))
    }
    component_ids.update(_path_components(changed_paths=observation.changed_paths, components=components))
    workstream_ids.update(_component_workstreams(component_ids=sorted(component_ids), components=components))
    return {
        "components": components,
        "alias_lookup": alias_lookup,
        "traceability": traceability,
        "mermaid_catalog": mermaid_catalog,
        "bug_rows": bug_rows,
        "workstream_rows": workstream_rows,
        "workstream_ids": sorted(token for token in workstream_ids if token),
        "bug_ids": sorted(token for token in bug_ids if token in bug_rows or token),
        "diagram_refs": diagram_refs,
        "component_ids": sorted(token for token in component_ids if token),
        "target_refs": target_refs,
    }


def _quick_lookup(*, signal_profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "components": {},
        "alias_lookup": {},
        "traceability": {},
        "mermaid_catalog": {},
        "bug_rows": {},
        "workstream_rows": {},
        "workstream_ids": list(signal_profile.get("workstream_ids", [])),
        "bug_ids": list(signal_profile.get("bug_ids", [])),
        "diagram_refs": [dict(row) for row in signal_profile.get("diagram_refs", []) if isinstance(row, Mapping)],
        "component_ids": list(signal_profile.get("component_ids", [])),
        "target_refs": [dict(row) for row in signal_profile.get("target_refs", []) if isinstance(row, Mapping)],
    }


def _dedupe_ref_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        normalized = {
            "kind": _normalize_token(row.get("kind")),
            "id": _normalize_string(row.get("id")),
            "path": _normalize_string(row.get("path")),
            "label": _normalize_string(row.get("label")) or _normalize_string(row.get("id")),
        }
        key = (normalized["kind"], normalized["id"], normalized["path"])
        if not normalized["id"] or key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def _merge_lookup(base: Mapping[str, Any], repo_rows: Mapping[str, Any]) -> dict[str, Any]:
    base_diagram_refs = list(base.get("diagram_refs", [])) if isinstance(base.get("diagram_refs"), list) else []
    repo_diagram_refs = list(repo_rows.get("diagram_refs", [])) if isinstance(repo_rows.get("diagram_refs"), list) else []
    base_target_refs = list(base.get("target_refs", [])) if isinstance(base.get("target_refs"), list) else []
    repo_target_refs = list(repo_rows.get("target_refs", [])) if isinstance(repo_rows.get("target_refs"), list) else []
    return {
        "components": dict(repo_rows.get("components", {})),
        "alias_lookup": dict(repo_rows.get("alias_lookup", {})),
        "traceability": dict(repo_rows.get("traceability", {})),
        "mermaid_catalog": dict(repo_rows.get("mermaid_catalog", {})),
        "bug_rows": dict(repo_rows.get("bug_rows", {})),
        "workstream_rows": dict(repo_rows.get("workstream_rows", {})),
        "workstream_ids": sorted(
            {
                *(_normalize_string_list(base.get("workstream_ids"))),
                *(_normalize_string_list(repo_rows.get("workstream_ids"))),
            }
        ),
        "bug_ids": sorted(
            {
                *(_normalize_string_list(base.get("bug_ids"))),
                *(_normalize_string_list(repo_rows.get("bug_ids"))),
            }
        ),
        "diagram_refs": _dedupe_ref_rows(
            [*base_diagram_refs, *repo_diagram_refs]
        ),
        "component_ids": sorted(
            {
                *(_normalize_string_list(base.get("component_ids"))),
                *(_normalize_string_list(repo_rows.get("component_ids"))),
            }
        ),
        "target_refs": _dedupe_ref_rows(
            [*base_target_refs, *repo_target_refs]
        ),
    }


def _candidate_stage_without_dedupe(
    *,
    observation: ObservationEnvelope,
    evidence_classes: Sequence[str],
    facts: Sequence[GovernanceFact],
    moment: Mapping[str, Any],
) -> str:
    return moment_runtime.candidate_stage_without_dedupe(
        observation=observation,
        evidence_classes=evidence_classes,
        facts=facts,
        moment=moment,
    )


def _candidate_stage(
    *,
    stage_guess: str,
    continuity: Mapping[str, Any],
) -> str:
    return continuity_runtime.evolve_candidate_stage(
        stage=stage_guess,
        continuity=continuity,
    )


def _candidate_duplicate_reason(*, stage: str, continuity: Mapping[str, Any]) -> str:
    if bool(continuity.get("declined")):
        return "declined_in_session"
    normalized_stage = _normalize_token(stage)
    if normalized_stage == "teaser" and bool(continuity.get("seen_teaser")):
        return "duplicate_teaser"
    if normalized_stage == "card" and bool(continuity.get("seen_card")):
        return "duplicate_card"
    return ""


def _proposal_duplicate_reason(*, continuity: Mapping[str, Any]) -> str:
    if bool(continuity.get("declined")):
        return "declined_in_session"
    if bool(continuity.get("proposal_pending")):
        return "proposal_already_pending"
    if bool(continuity.get("proposal_applied")):
        return "proposal_already_applied"
    return ""


def _intervention_key(
    *,
    observation: ObservationEnvelope,
    lookup: Mapping[str, Any],
    moment: Mapping[str, Any],
    signal_profile: Mapping[str, Any],
) -> str:
    prompt_surface = fact_producer_runtime.joined_prompt_surface(observation)
    title = proposal_action_selection.slugify(
        proposal_action_selection.derive_title(observation=observation, fallback="governed-observation"),
        fallback="governed-observation",
    )
    payload = {
        "session_id": observation.session_id,
        "workstreams": list(lookup.get("workstream_ids", [])),
        "bugs": list(lookup.get("bug_ids", [])),
        "components": list(lookup.get("component_ids", [])),
        "diagrams": [row.get("id", "") for row in lookup.get("diagram_refs", []) if isinstance(row, Mapping)],
        "semantic_signature": list(signal_profile.get("identity_signature", []))
        or list(signal_profile.get("semantic_signature", []))
        or signal_kernel.semantic_signature(prompt_surface),
        "subject": title,
    }
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"iv-{digest[:16]}"


def _enriched_observation_payload(
    *,
    observation: ObservationEnvelope,
    lookup: Mapping[str, Any],
) -> dict[str, Any]:
    payload = observation.as_dict()
    payload["active_target_refs"] = _dedupe_ref_rows(
        [
            *(payload.get("active_target_refs", []) if isinstance(payload.get("active_target_refs"), list) else []),
            *(lookup.get("target_refs", []) if isinstance(lookup.get("target_refs"), list) else []),
            *(lookup.get("diagram_refs", []) if isinstance(lookup.get("diagram_refs"), list) else []),
            *(
                {"kind": "workstream", "id": token, "path": "", "label": token}
                for token in _normalize_string_list(lookup.get("workstream_ids"))
            ),
            *(
                {"kind": "bug", "id": token, "path": "", "label": token}
                for token in _normalize_string_list(lookup.get("bug_ids"))
            ),
            *(
                {"kind": "component", "id": token, "path": "", "label": token}
                for token in _normalize_string_list(lookup.get("component_ids"))
            ),
        ]
    )
    packet_summary = alignment_evidence.merged_packet_summary(observation)
    if _normalize_string_list(lookup.get("workstream_ids")) and not _normalize_string_list(packet_summary.get("workstreams")):
        packet_summary["workstreams"] = _normalize_string_list(lookup.get("workstream_ids"))
    if _normalize_string_list(lookup.get("bug_ids")) and not _normalize_string_list(packet_summary.get("bugs")):
        packet_summary["bugs"] = _normalize_string_list(lookup.get("bug_ids"))
    component_ids = _normalize_string_list(lookup.get("component_ids"))
    if component_ids and not _normalize_string_list(packet_summary.get("components")):
        packet_summary["components"] = component_ids
    diagram_ids = [
        _normalize_string(row.get("id"))
        for row in lookup.get("diagram_refs", [])
        if isinstance(row, Mapping) and _normalize_string(row.get("id"))
    ]
    if diagram_ids and not _normalize_string_list(packet_summary.get("diagrams")):
        packet_summary["diagrams"] = diagram_ids
    payload["packet_summary"] = packet_summary
    return payload


def build_intervention_bundle(*, repo_root: Path, observation: Mapping[str, Any]) -> dict[str, Any]:
    normalized_observation = ObservationEnvelope.from_mapping(observation)
    session_memory = alignment_evidence.merged_session_memory(
        observation=normalized_observation,
        stream_memory=stream_state.session_memory_snapshot(
            repo_root=repo_root,
            session_id=normalized_observation.session_id,
        ),
    )
    signal_profile = signal_kernel.build_signal_profile(
        observation=normalized_observation,
        session_memory=session_memory,
    )
    lookup = _quick_lookup(signal_profile=signal_profile)
    if bool(signal_profile.get("repo_truth_eligible")):
        lookup = _merge_lookup(
            lookup,
            _repo_lookup(repo_root=repo_root, observation=normalized_observation),
        )
    evidence = list(signal_profile.get("evidence_classes", [])) or fact_producer_runtime.evidence_classes(
        observation=normalized_observation,
        lookup=lookup,
    )
    facts = alignment_evidence.merge_governance_facts(
        fact_producer_runtime.collect_facts(
            observation=normalized_observation,
            lookup=lookup,
            evidence_classes=evidence,
            signal_profile=signal_profile,
        ),
        alignment_evidence.governance_facts_from_alignment(
            observation=normalized_observation,
            evidence_classes=evidence,
        ),
    )
    moment = moment_runtime.select_moment(
        observation=normalized_observation,
        facts=facts,
        signal_profile=signal_profile,
        lookup=lookup,
        evidence_classes=evidence,
        session_memory=session_memory,
    )
    moment["semantic_signature"] = list(signal_profile.get("semantic_signature", []))
    key = _intervention_key(
        observation=normalized_observation,
        lookup=lookup,
        moment=moment,
        signal_profile=signal_profile,
    )
    continuity = continuity_runtime.moment_continuity_snapshot(
        repo_root=repo_root,
        session_id=normalized_observation.session_id,
        moment_key=key,
        semantic_signature=signal_profile.get("identity_signature", []) or signal_profile.get("semantic_signature", []),
    )
    moment["continuity"] = dict(continuity)
    stage_guess = moment_runtime.candidate_stage_without_dedupe(
        observation=normalized_observation,
        evidence_classes=evidence,
        facts=facts,
        moment=moment,
    )
    stage = _candidate_stage(
        stage_guess=stage_guess,
        continuity=continuity,
    )
    candidate_duplicate_reason = _candidate_duplicate_reason(
        stage=stage,
        continuity=continuity,
    )
    proposal_duplicate_reason = _proposal_duplicate_reason(continuity=continuity)
    proposal_ready = (
        stage == "card"
        and int(moment.get("proposal_readiness") or 0) >= 62
        and proposal_duplicate_reason == ""
    )
    actions = []
    if proposal_ready:
        actions = proposal_action_selection.proposal_actions(
            observation=normalized_observation,
            lookup=lookup,
            facts=facts,
            signal_profile=signal_profile,
        )
    headline, observation_markdown, observation_plain, teaser_text = voice.render_observation(
        facts=facts,
        proposal_actions=actions,
        moment=moment,
        seed=key,
    )
    candidate = InterventionCandidate(
        key=key,
        stage=stage,
        eligible=stage in {"teaser", "card"} and not candidate_duplicate_reason,
        teaser_text=teaser_text if stage == "teaser" else "",
        markdown_text=observation_markdown if stage == "card" and not candidate_duplicate_reason else "",
        plain_text=observation_plain if stage == "card" and not candidate_duplicate_reason else "",
        evidence_classes=list(evidence),
        facts=[row.as_dict() for row in facts],
        moment=dict(moment),
        suppressed_reason=candidate_duplicate_reason,
        headline=headline,
    )
    proposal_markdown = ""
    proposal_plain = ""
    confirmation_text = ""
    if actions:
        proposal_markdown, proposal_plain, confirmation_text = voice.render_proposal(
            actions=actions,
            moment=moment,
            seed=key,
        )
    proposal = CaptureBundle(
        key=key,
        eligible=bool(actions) and proposal_ready,
        stale=False,
        markdown_text=proposal_markdown,
        plain_text=proposal_plain,
        confirmation_text=confirmation_text,
        actions=[row.as_dict() for row in actions],
        action_surfaces=voice.collect_action_surfaces(actions),
        apply_supported=all(bool(row.apply_supported) for row in actions if actions) if actions else False,
        suppressed_reason=proposal_duplicate_reason,
    )
    proposal_payload = proposal.as_dict()
    proposal_payload["semantic_signature"] = list(signal_profile.get("semantic_signature", []))
    proposal_payload["summary"] = voice.summarize_proposal(
        actions=actions,
        moment=moment,
    ) if actions else ""
    observation_payload = _enriched_observation_payload(
        observation=normalized_observation,
        lookup=lookup,
    )
    payload = InterventionBundle(
        observation=observation_payload,
        facts=[row.as_dict() for row in facts],
        candidate=candidate.as_dict(),
        proposal=proposal_payload,
        render_policy={
            "max_card_per_turn": 1,
            "dedupe_by_intervention_key": True,
            "prompt_submit_teaser_only": True,
            "proposal_requires_confirmation": True,
            "voice_contract": voice_contract.voice_contract_payload(),
        },
        pending_state=stream_state.pending_proposal_state(repo_root=repo_root),
    )
    return payload.as_dict()
