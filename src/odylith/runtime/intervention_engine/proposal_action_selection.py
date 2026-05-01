"""Select governed capture proposal actions for intervention bundles."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.governance import bug_authoring
from odylith.runtime.intervention_engine import fact_producer_runtime
from odylith.runtime.intervention_engine import signal_kernel
from odylith.runtime.intervention_engine import visibility_contract
from odylith.runtime.intervention_engine.contract import CaptureAction
from odylith.runtime.intervention_engine.contract import GovernanceFact
from odylith.runtime.intervention_engine.contract import ObservationEnvelope


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
        "always",
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
        "from",
        "governance",
        "helpful",
        "inside",
        "intervene",
        "intervention",
        "interventions",
        "make",
        "need",
        "observation",
        "observe",
        "ongoing",
        "proposal",
        "records",
        "session",
        "should",
        "suggest",
        "surface",
        "that",
        "the",
        "their",
        "this",
        "timely",
        "truth",
        "update",
        "with",
    }
)
_TITLE_STOPWORDS: frozenset[str] = _STOPWORDS.union(
    {
        "clarity",
        "conversation",
        "governed",
        "harden",
        "ownership",
        "topology",
    }
)


_normalize_string = visibility_contract.normalize_string
_normalize_token = visibility_contract.normalize_token
_normalize_string_list = visibility_contract.normalize_string_list


def slugify(text: str, *, fallback: str) -> str:
    tokens = [
        token.lower()
        for token in _MEANINGFUL_TOKEN_RE.findall(text)
        if token.lower() not in _STOPWORDS
    ]
    slug = "-".join(tokens[:6]).strip("-")
    return slug or fallback


def derive_title(*, observation: ObservationEnvelope, fallback: str) -> str:
    text = observation.prompt_excerpt or observation.assistant_summary or fallback
    all_tokens = [
        token
        for token in _MEANINGFUL_TOKEN_RE.findall(text)
        if token.lower() not in _STOPWORDS
    ]
    tokens = [token for token in all_tokens if token.lower() not in _TITLE_STOPWORDS]
    if not tokens:
        tokens = all_tokens
    if not tokens:
        return fallback
    return " ".join(token.capitalize() if token.islower() else token for token in tokens[:8])


def _title_key(value: Any) -> str:
    return _normalize_token(_normalize_string(value).replace("`", ""))


def _title_signature(value: Any) -> set[str]:
    return set(signal_kernel.semantic_signature(_normalize_string(value)))


def _titles_match(left: Any, right: Any) -> bool:
    left_key = _title_key(left)
    right_key = _title_key(right)
    if left_key and left_key == right_key:
        return True
    left_signature = _title_signature(left)
    right_signature = _title_signature(right)
    if not left_signature or not right_signature:
        return False
    smaller = min(len(left_signature), len(right_signature))
    return smaller >= 3 and len(left_signature & right_signature) >= smaller


def _matching_workstream_by_title(*, lookup: Mapping[str, Any], title: str) -> str:
    if not _normalize_string(title):
        return ""
    for workstream_id, row in lookup.get("workstream_rows", {}).items():
        if _titles_match(row.get("title"), title):
            return _normalize_string(workstream_id)
    return ""


def _matching_bug_by_title(*, lookup: Mapping[str, Any], title: str) -> str:
    if not _normalize_string(title):
        return ""
    for bug_id, row in lookup.get("bug_rows", {}).items():
        path_stem = Path(str(row.get("path", bug_id))).stem
        if _titles_match(row.get("title"), title) or _titles_match(path_stem, title):
            return _normalize_string(bug_id)
    return ""


def _matching_diagram_by_title_or_slug(*, lookup: Mapping[str, Any], title: str, slug: str) -> dict[str, str]:
    wanted_slug = _normalize_string(slug).lower()
    diagrams = lookup.get("mermaid_catalog", {}).get("diagrams", [])
    if not isinstance(diagrams, list):
        return {}
    for row in diagrams:
        if not isinstance(row, Mapping):
            continue
        row_slug = _normalize_string(row.get("slug")).lower()
        if not _titles_match(row.get("title"), title) and row_slug != wanted_slug:
            continue
        return {
            "kind": "diagram",
            "id": _normalize_string(row.get("diagram_id")),
            "label": _normalize_string(row.get("title")),
            "path": _normalize_string(row.get("source_mmd")),
        }
    return {}


def _entry_field(entry: Any, field: str) -> Any:
    if isinstance(entry, Mapping):
        return entry.get(field)
    return getattr(entry, field, None)


def _radar_create_payload(*, observation: ObservationEnvelope, title: str) -> dict[str, str]:
    prompt_surface = fact_producer_runtime.joined_prompt_surface(observation)
    prompt_excerpt = _normalize_string(observation.prompt_excerpt)
    changed_paths = [path for path in _normalize_string_list(observation.changed_paths)[:3] if path]
    path_clause = f" Touched paths include {', '.join(changed_paths)}." if changed_paths else ""
    problem_seed = prompt_excerpt or prompt_surface or title
    return {
        "title": title,
        "problem": (
            f"The active conversation is asking Odylith to govern {title}, but no existing Radar "
            f"workstream anchors that slice yet. Prompt evidence: {problem_seed}.{path_clause}"
        ),
        "customer": (
            "Maintainers and coding agents who need the live decision, touched paths, "
            "and follow-on validation to survive beyond this one chat turn."
        ),
        "opportunity": (
            f"Capture {title} as explicit Radar truth while the prompt and file evidence are still warm, "
            "so implementation can bind to one governed record instead of reconstructing intent later."
        ),
        "product_view": (
            "A proposal-applied Radar workstream must be useful immediately: it should explain why "
            "the work exists, who needs it, and how a later maintainer can prove it."
        ),
        "success_metrics": (
            f"- Radar creates a non-placeholder workstream for {title}.\n"
            "- The record includes grounded problem, customer, opportunity, product view, and success metrics.\n"
            "- A follow-on technical plan can bind to the workstream without rewriting its core detail."
        ),
    }


def _matching_component_by_title_or_id(*, lookup: Mapping[str, Any], title: str, target_id: str) -> str:
    normalized_target = _normalize_string(target_id)
    if normalized_target in lookup.get("components", {}):
        return normalized_target
    alias_lookup = lookup.get("alias_lookup", {})
    if normalized_target in alias_lookup:
        return _normalize_string(alias_lookup.get(normalized_target))
    for component_id, entry in lookup.get("components", {}).items():
        if _titles_match(_entry_field(entry, "name") or component_id, title):
            return _normalize_string(component_id)
    return ""


def proposal_actions(
    *,
    observation: ObservationEnvelope,
    lookup: Mapping[str, Any],
    facts: Sequence[GovernanceFact],
    signal_profile: Mapping[str, Any],
) -> list[CaptureAction]:
    actions: list[CaptureAction] = []
    if not bool(signal_profile.get("proposal_signal")):
        return actions
    if any(_normalize_token(row.kind) == "write_blocker" for row in facts):
        return actions
    prompt_surface = (
        _normalize_string(signal_profile.get("prompt_surface"))
        or fact_producer_runtime.joined_prompt_surface(observation)
    )
    phase = _normalize_token(observation.turn_phase)
    workstream_ids = list(lookup.get("workstream_ids", []))
    component_ids = list(lookup.get("component_ids", []))
    diagram_refs = list(lookup.get("diagram_refs", []))
    bug_ids = list(lookup.get("bug_ids", []))

    title = derive_title(observation=observation, fallback="Governed Observation")
    slug = slugify(title, fallback="governed-observation")
    matched_workstream_id = (
        workstream_ids[0]
        if workstream_ids
        else _matching_workstream_by_title(lookup=lookup, title=title)
    )
    derived_component_id = slugify(title, fallback="intervention-engine")
    if derived_component_id == "intervention-engine" and "governance" in _normalize_token(prompt_surface):
        derived_component_id = "governance-intervention-engine"
    matched_component_id = component_ids[0] if component_ids else _matching_component_by_title_or_id(
        lookup=lookup,
        title=title,
        target_id=derived_component_id,
    )
    matched_diagram = diagram_refs[0] if diagram_refs else _matching_diagram_by_title_or_slug(
        lookup=lookup,
        title=f"{title} Topology",
        slug=slug,
    )
    matched_bug_id = bug_ids[0] if bug_ids else _matching_bug_by_title(lookup=lookup, title=title)

    if matched_workstream_id:
        actions.append(
            CaptureAction(
                surface="radar",
                action="update",
                target_kind="workstream",
                target_id=matched_workstream_id,
                title=title,
                rationale=(
                    f"Local Radar candidate: {matched_workstream_id}. Update it only if it still owns this work."
                ),
                apply_supported=False,
                cli_command="odylith governance capture-apply",
                payload={"idea_id": matched_workstream_id},
            )
        )
    elif bool(signal_profile.get("has_governance_hints")) or phase in {"post_edit_checkpoint", "post_bash_checkpoint"}:
        actions.append(
            CaptureAction(
                surface="radar",
                action="create",
                target_kind="workstream",
                target_id="",
                title=title,
                rationale="No workstream tracks this yet, and the conversation has enough signal to create one now.",
                apply_supported=True,
                cli_command="odylith backlog create",
                payload=_radar_create_payload(observation=observation, title=title),
            )
        )

    if matched_component_id:
        actions.append(
            CaptureAction(
                surface="registry",
                action="update",
                target_kind="component",
                target_id=matched_component_id,
                title=title,
                rationale=(
                    f"Local Registry candidate: `{matched_component_id}`. Update it only if it owns this boundary."
                ),
                apply_supported=False,
                cli_command="odylith governance capture-apply",
                payload={"component_id": matched_component_id},
            )
        )
    else:
        actions.append(
            CaptureAction(
                surface="registry",
                action="create",
                target_kind="component",
                target_id=derived_component_id,
                title=title,
                rationale="This conversation is defining a runtime boundary that Registry does not track yet.",
                apply_supported=True,
                cli_command="odylith component register",
                payload={
                    "component_id": derived_component_id,
                    "label": title,
                    "path": (observation.changed_paths[0] if observation.changed_paths else "src/odylith/runtime"),
                    "kind": "runtime",
                },
            )
        )

    if matched_diagram:
        actions.append(
            CaptureAction(
                surface="atlas",
                action="review_refresh",
                target_kind="diagram",
                target_id=_normalize_string(matched_diagram.get("id")),
                title=_normalize_string(matched_diagram.get("label")) or title,
                rationale="Atlas has a local related diagram. Review it before creating another one.",
                apply_supported=False,
                cli_command="odylith governance capture-apply",
                payload={"diagram_id": _normalize_string(matched_diagram.get("id"))},
            )
        )
    elif bool(signal_profile.get("has_topology_hints")) or any(row.kind == "topology" for row in facts):
        actions.append(
            CaptureAction(
                surface="atlas",
                action="create",
                target_kind="diagram",
                target_id=f"proposed:{slug}",
                title=f"{title} Topology",
                rationale="This conversation is making topology claims without a diagram anchor yet.",
                apply_supported=False,
                cli_command="odylith atlas scaffold",
                payload={
                    "slug": slug,
                    "title": f"{title} Topology",
                    "kind": "flowchart",
                },
            )
        )

    if matched_bug_id:
        actions.append(
            CaptureAction(
                surface="casebook",
                action="reopen",
                target_kind="bug",
                target_id=matched_bug_id,
                title=lookup.get("bug_rows", {}).get(matched_bug_id, {}).get("title", title),
                rationale=(
                    f"Local Casebook candidate: {matched_bug_id}. Add evidence only if this is the same failure."
                ),
                apply_supported=False,
                cli_command="odylith governance capture-apply",
                payload={"bug_id": matched_bug_id},
            )
        )
    elif bool(signal_profile.get("has_bug_hints")):
        casebook_payload = {"title": title, "component": matched_component_id}
        missing_capture_fields = bug_authoring.missing_capture_requirements(
            title=title,
            component=matched_component_id,
            payload=casebook_payload,
        )
        capture_rationale = (
            "This conversation describes a failure or regression risk that Casebook does not track yet."
        )
        if missing_capture_fields:
            capture_rationale = (
                "This conversation describes a failure or regression risk, but Odylith still needs grounded "
                "bug-capture evidence before it can create the Casebook record automatically."
            )
            casebook_payload["missing_capture_fields"] = missing_capture_fields
        actions.append(
            CaptureAction(
                surface="casebook",
                action="create",
                target_kind="bug",
                target_id="",
                title=title,
                rationale=capture_rationale,
                apply_supported=not missing_capture_fields,
                cli_command="odylith bug capture",
                payload=casebook_payload,
            )
        )
    return actions
