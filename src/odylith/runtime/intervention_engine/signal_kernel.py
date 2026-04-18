from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.intervention_engine.contract import ObservationEnvelope
from odylith.runtime.intervention_engine import alignment_evidence
from odylith.runtime.intervention_engine import visibility_contract


_WORKSTREAM_RE = re.compile(r"\bB-\d{3,}\b")
_BUG_RE = re.compile(r"\bCB-\d{3,}\b")
_DIAGRAM_RE = re.compile(r"\bD-\d{3,}\b")
_MEANINGFUL_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}")
_STOPWORDS: frozenset[str] = frozenset(
    {
        "about",
        "across",
        "after",
        "agent",
        "all",
        "also",
        "and",
        "around",
        "because",
        "before",
        "bring",
        "capture",
        "clear",
        "conversation",
        "conversations",
        "design",
        "during",
        "engine",
        "facts",
        "flow",
        "from",
        "governance",
        "helpful",
        "human",
        "inside",
        "intervene",
        "intervention",
        "interventions",
        "lane",
        "lanes",
        "make",
        "need",
        "observation",
        "observe",
        "ongoing",
        "proposal",
        "records",
        "session",
        "should",
        "signal",
        "signals",
        "suggest",
        "surface",
        "that",
        "the",
        "their",
        "this",
        "timely",
        "truth",
        "update",
        "voice",
        "with",
    }
)
_GOVERNANCE_HINTS: tuple[str, ...] = (
    "governance",
    "workstream",
    "radar",
    "registry",
    "atlas",
    "casebook",
    "capture",
    "record",
    "proposal",
)
_TOPOLOGY_HINTS: tuple[str, ...] = (
    "topology",
    "diagram",
    "architecture",
    "boundary",
    "ownership",
    "relationship",
    "atlas",
    "map",
)
_INVARIANT_HINTS: tuple[str, ...] = (
    "invariant",
    "must",
    "never",
    "always",
    "guardrail",
    "non-negotiable",
    "rule",
)
_HISTORY_HINTS: tuple[str, ...] = (
    "history",
    "previous",
    "prior",
    "regression",
    "again",
    "already",
    "remember",
    "memory",
    "casebook",
)
_BUG_HINTS: tuple[str, ...] = (
    "bug",
    "failure",
    "regression",
    "incident",
    "broken",
    "crash",
)
_EXECUTION_HINTS: tuple[str, ...] = (
    "implement",
    "wire",
    "build",
    "fix",
    "ship",
    "harden",
    "design",
    "refactor",
)
_GOVERNED_PATH_HINTS: tuple[str, ...] = (
    ".claude/",
    ".codex/",
    "odylith/agents-guidelines/",
    "odylith/registry/",
    "odylith/radar/",
    "odylith/atlas/",
    "odylith/casebook/",
    "src/odylith/runtime/intervention_engine/",
    "src/odylith/runtime/surfaces/",
)


_normalize_string = visibility_contract.normalize_string
_normalize_token = visibility_contract.normalize_token
_normalize_string_list = visibility_contract.normalize_string_list
_mapping = visibility_contract.mapping_copy


def _explicit_ids(text: str, pattern: re.Pattern[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for token in pattern.findall(_normalize_string(text)):
        value = _normalize_string(token).upper()
        if not value or value in seen:
            continue
        seen.add(value)
        rows.append(value)
    return rows


def _contains_any(text: str, hints: Sequence[str]) -> bool:
    haystack = _normalize_token(text)
    return any(_normalize_token(hint) in haystack for hint in hints)


def _joined_prompt_surface(observation: ObservationEnvelope) -> str:
    return " ".join(
        token
        for token in (observation.prompt_excerpt, observation.assistant_summary)
        if _normalize_string(token)
    ).strip()


def semantic_signature(*values: str) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        for token in _MEANINGFUL_TOKEN_RE.findall(_normalize_string(value)):
            normalized = token.lower()
            if normalized in _STOPWORDS or normalized in seen:
                continue
            seen.add(normalized)
            rows.append(normalized)
            if len(rows) >= 10:
                return rows
    return rows


def _ref_ids(target_refs: Sequence[Mapping[str, str]], *, kind: str) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    wanted = _normalize_token(kind)
    for row in target_refs:
        if not isinstance(row, Mapping):
            continue
        if _normalize_token(row.get("kind")) != wanted:
            continue
        token = _normalize_string(row.get("id"))
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _governed_path_pressure(changed_paths: Sequence[str]) -> int:
    score = 0
    for raw_path in changed_paths:
        path = _normalize_string(raw_path)
        if not path:
            continue
        normalized = Path(path).as_posix()
        if any(normalized.startswith(prefix) for prefix in _GOVERNED_PATH_HINTS):
            score += 18
        elif normalized.startswith("src/odylith/runtime/"):
            score += 8
    return min(score, 40)


def _dimension_score(
    *,
    prompt_surface: str,
    changed_paths: Sequence[str],
    target_refs: Sequence[Mapping[str, str]],
    hints: Sequence[str],
    direct_ref_bonus: int = 0,
) -> int:
    score = 0
    if _contains_any(prompt_surface, hints):
        score += 32
    if _contains_any(" ".join(changed_paths), hints):
        score += 12
    if direct_ref_bonus and target_refs:
        score += direct_ref_bonus
    return min(score, 100)


def build_signal_profile(
    *,
    observation: ObservationEnvelope,
    session_memory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    memory = _mapping(session_memory)
    prompt_surface = _joined_prompt_surface(observation)
    changed_paths = _normalize_string_list(observation.changed_paths)
    packet_summary = alignment_evidence.merged_packet_summary(observation)
    target_refs = alignment_evidence.active_target_refs(observation)
    for key, kind in (("workstreams", "workstream"), ("bugs", "bug"), ("diagrams", "diagram"), ("components", "component")):
        for token in _normalize_string_list(packet_summary.get(key)):
            target_refs.append({"kind": kind, "id": token, "path": "", "label": token})
    deduped_target_refs: list[dict[str, str]] = []
    seen_target_refs: set[tuple[str, str]] = set()
    for row in target_refs:
        if not isinstance(row, Mapping):
            continue
        kind = _normalize_token(row.get("kind"))
        item_id = _normalize_string(row.get("id"))
        key = (kind, item_id)
        if not kind or not item_id or key in seen_target_refs:
            continue
        seen_target_refs.add(key)
        deduped_target_refs.append(
            {
                "kind": kind,
                "id": item_id,
                "path": _normalize_string(row.get("path")),
                "label": _normalize_string(row.get("label")) or item_id,
            }
        )
    alignment_text = alignment_evidence.alignment_signal_text(observation)
    prompt_with_paths = " ".join([prompt_surface, *changed_paths, alignment_text]).strip()
    workstream_ids = _ref_ids(deduped_target_refs, kind="workstream")
    bug_ids = _ref_ids(deduped_target_refs, kind="bug")
    component_ids = _ref_ids(deduped_target_refs, kind="component")
    diagram_refs = [
        dict(row)
        for row in deduped_target_refs
        if _normalize_token(row.get("kind")) == "diagram"
    ]
    if not workstream_ids:
        workstream_ids = _explicit_ids(prompt_surface, _WORKSTREAM_RE)
    if not bug_ids:
        bug_ids = _explicit_ids(prompt_surface, _BUG_RE)
    if not diagram_refs:
        diagram_refs = [
            {"kind": "diagram", "id": token, "path": "", "label": token}
            for token in _explicit_ids(prompt_surface, _DIAGRAM_RE)
        ]
    semantic_rows = semantic_signature(
        prompt_surface,
        alignment_text,
        " ".join(changed_paths),
        " ".join(f"{row['kind']} {row['id']}" for row in deduped_target_refs),
    )
    identity_rows = semantic_signature(
        observation.prompt_excerpt or prompt_surface,
        " ".join(f"{row['kind']} {row['id']}" for row in deduped_target_refs),
        " ".join(workstream_ids + bug_ids + component_ids + [row.get("id", "") for row in diagram_refs]),
    )
    signature_token = "|".join(semantic_rows)
    same_signature_recent = signature_token and signature_token in {
        str(token)
        for token in memory.get("recent_signatures", [])
        if _normalize_string(token)
    }
    had_recent_teaser = signature_token and signature_token in {
        str(token)
        for token in memory.get("recent_teaser_signatures", [])
        if _normalize_string(token)
    }
    had_recent_card = signature_token and signature_token in {
        str(token)
        for token in memory.get("recent_card_signatures", [])
        if _normalize_string(token)
    }
    governed_path_pressure = _governed_path_pressure(changed_paths)
    anchor_pressure = min(
        100,
        (24 if workstream_ids else 0)
        + (16 if component_ids else 0)
        + (14 if bug_ids else 0)
        + (12 if diagram_refs else 0)
        + governed_path_pressure,
    )
    dimensions = {
        "governance": _dimension_score(
            prompt_surface=prompt_surface,
            changed_paths=changed_paths,
            target_refs=deduped_target_refs,
            hints=_GOVERNANCE_HINTS,
            direct_ref_bonus=18 if workstream_ids or component_ids else 0,
        ),
        "topology": _dimension_score(
            prompt_surface=prompt_surface,
            changed_paths=changed_paths,
            target_refs=deduped_target_refs,
            hints=_TOPOLOGY_HINTS,
            direct_ref_bonus=14 if diagram_refs else 0,
        ),
        "invariant": _dimension_score(
            prompt_surface=prompt_surface,
            changed_paths=changed_paths,
            target_refs=(),
            hints=_INVARIANT_HINTS,
        ),
        "history": _dimension_score(
            prompt_surface=prompt_surface,
            changed_paths=changed_paths,
            target_refs=deduped_target_refs,
            hints=_HISTORY_HINTS,
            direct_ref_bonus=16 if bug_ids else 0,
        ),
        "bug": _dimension_score(
            prompt_surface=prompt_surface,
            changed_paths=changed_paths,
            target_refs=deduped_target_refs,
            hints=_BUG_HINTS,
            direct_ref_bonus=12 if bug_ids else 0,
        ),
        "execution": _dimension_score(
            prompt_surface=prompt_with_paths,
            changed_paths=changed_paths,
            target_refs=(),
            hints=_EXECUTION_HINTS,
        ),
        "continuity": min(100, anchor_pressure + (18 if same_signature_recent else 0)),
    }
    governed_dimension_max = max(
        dimensions["governance"],
        dimensions["topology"],
        dimensions["invariant"],
        dimensions["history"],
        dimensions["bug"],
        dimensions["continuity"],
    )
    evidence_classes: list[str] = []
    if observation.prompt_excerpt:
        evidence_classes.append("prompt")
    if observation.assistant_summary:
        evidence_classes.append("assistant")
    if changed_paths:
        evidence_classes.append("changed_paths")
    if deduped_target_refs:
        evidence_classes.append("packet")
    for evidence_class in alignment_evidence.runtime_evidence_classes(observation):
        if evidence_class not in evidence_classes:
            evidence_classes.append(evidence_class)
    novelty_score = max(0, 76 - dimensions["continuity"] + (8 if governed_path_pressure <= 0 else 0))
    session_repeat_penalty = 20 if had_recent_card else 10 if same_signature_recent else 0
    session_escalation_bonus = 14 if had_recent_teaser and changed_paths else 0
    max_dimension = max(dimensions.values()) if dimensions else 0
    repo_truth_eligible = bool(
        anchor_pressure >= 18
        or governed_dimension_max >= 32
        or (session_escalation_bonus and governed_dimension_max >= 24)
    )
    proposal_signal = bool(
        anchor_pressure >= 22
        or (dimensions["governance"] + dimensions["topology"] + dimensions["history"] + dimensions["invariant"]) >= 54
        or (governed_path_pressure >= 18 and governed_dimension_max >= 28)
    )
    return {
        "prompt_surface": prompt_surface,
        "target_refs": deduped_target_refs,
        "workstream_ids": workstream_ids,
        "bug_ids": bug_ids,
        "component_ids": component_ids,
        "diagram_refs": diagram_refs,
        "semantic_signature": semantic_rows,
        "identity_signature": identity_rows,
        "anchor_pressure": anchor_pressure,
        "governed_path_pressure": governed_path_pressure,
        "dimensions": dimensions,
        "evidence_classes": evidence_classes,
        "novelty_score": novelty_score,
        "session_repeat_penalty": session_repeat_penalty,
        "session_escalation_bonus": session_escalation_bonus,
        "same_signature_recent": bool(same_signature_recent),
        "had_recent_teaser": bool(had_recent_teaser),
        "had_recent_card": bool(had_recent_card),
        "has_direct_refs": bool(workstream_ids or bug_ids or component_ids or diagram_refs),
        "has_governance_hints": dimensions["governance"] >= 32,
        "has_topology_hints": dimensions["topology"] >= 32,
        "has_invariant_hints": dimensions["invariant"] >= 32,
        "has_bug_hints": max(dimensions["bug"], dimensions["history"]) >= 32,
        "has_execution_hints": dimensions["execution"] >= 32,
        "has_fact_signal": bool(anchor_pressure >= 18 or max_dimension >= 32),
        "repo_truth_eligible": repo_truth_eligible,
        "proposal_signal": proposal_signal,
        "governed_dimension_max": governed_dimension_max,
    }
