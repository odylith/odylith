from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.governance import backlog_authoring
from odylith.runtime.governance import bug_authoring
from odylith.runtime.governance import component_authoring
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.surfaces import scaffold_mermaid_diagram


def _normalize_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _required_text_payload(payload: Mapping[str, Any], *, keys: Sequence[str], surface: str) -> dict[str, str]:
    values: dict[str, str] = {}
    missing: list[str] = []
    for key in keys:
        token = _normalize_string(payload.get(key))
        if not token:
            missing.append(key)
            continue
        values[key] = token
    if missing:
        missing_flags = ", ".join(f"`{item}`" for item in missing)
        raise ValueError(
            f"{surface} create requires grounded workstream detail before apply; "
            f"missing fields: {missing_flags}"
        )
    return values


def _payload_text(args_payload: str) -> str:
    if _normalize_string(args_payload):
        return str(args_payload)
    import sys

    return sys.stdin.read()


def _load_payload(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _proposal_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("proposal"), Mapping):
        return dict(payload.get("proposal"))
    if isinstance(payload.get("capture_bundle"), Mapping):
        return dict(payload.get("capture_bundle"))
    return dict(payload)


def _latest_proposal_event(*, repo_root: Path, proposal_key: str, session_id: str) -> dict[str, Any]:
    latest: dict[str, Any] = {}
    wanted_session = _normalize_string(session_id)
    for row in stream_state.load_recent_intervention_events(
        repo_root=repo_root,
        limit=400,
        session_id=wanted_session,
    ):
        if _normalize_string(row.get("intervention_key")) != proposal_key:
            continue
        latest = dict(row)
    if latest or wanted_session:
        return latest
    for row in stream_state.load_recent_intervention_events(
        repo_root=repo_root,
        limit=400,
    ):
        if _normalize_string(row.get("intervention_key")) != proposal_key:
            continue
        latest = dict(row)
    return latest


def _next_diagram_id(catalog_path: Path) -> str:
    payload = _load_payload(catalog_path.read_text(encoding="utf-8")) if catalog_path.is_file() else {}
    max_id = 0
    for row in payload.get("diagrams", []) if isinstance(payload.get("diagrams"), list) else []:
        token = _normalize_string(row.get("diagram_id"))
        if token.startswith("D-") and token[2:].isdigit():
            max_id = max(max_id, int(token[2:]))
    return f"D-{max_id + 1:03d}"


def _apply_radar_create(*, repo_root: Path, action: Mapping[str, Any]) -> dict[str, Any]:
    payload = _mapping(action.get("payload"))
    title = _normalize_string(payload.get("title")) or _normalize_string(action.get("title")) or "Governed Observation"
    detail = _required_text_payload(
        payload,
        keys=("problem", "customer", "opportunity", "product_view", "success_metrics"),
        surface="Radar",
    )
    args = SimpleNamespace(
        repo_root=str(repo_root),
        backlog_index="odylith/radar/source/INDEX.md",
        ideas_root="odylith/radar/source/ideas",
        problem=detail["problem"],
        customer=detail["customer"],
        opportunity=detail["opportunity"],
        product_view=detail["product_view"],
        success_metrics=detail["success_metrics"],
        priority="P1",
        commercial_value=3,
        product_impact=4,
        market_value=4,
        impacted_parts="odylith",
        sizing="M",
        complexity="Medium",
        ordering_score=78,
        ordering_rationale="Queued through `odylith governance capture-apply` from an Odylith Proposal.",
        confidence="high",
        founder_override=False,
        override_note="",
        override_review_date="",
        dry_run=False,
        as_json=False,
    )
    result = backlog_authoring.create_queued_backlog_items(
        repo_root=repo_root,
        backlog_index_path=repo_root / "odylith" / "radar" / "source" / "INDEX.md",
        ideas_root=repo_root / "odylith" / "radar" / "source" / "ideas",
        titles=(title,),
        args=args,
    )
    for raw_path, text in result["idea_files"].items():
        Path(raw_path).write_text(str(text), encoding="utf-8")
    (repo_root / "odylith" / "radar" / "source" / "INDEX.md").write_text(
        str(result["backlog_index_text"]),
        encoding="utf-8",
    )
    backlog_authoring.owned_surface_refresh.raise_for_failed_refresh(
        repo_root=repo_root,
        surface="radar",
        operation_label="Odylith Proposal apply",
    )
    created = result.get("created", [])
    return dict(created[0]) if isinstance(created, list) and created else {"title": title}


def _apply_registry_create(*, repo_root: Path, action: Mapping[str, Any]) -> dict[str, Any]:
    payload = _mapping(action.get("payload"))
    return component_authoring.register_component(
        repo_root=repo_root,
        component_id=_normalize_string(payload.get("component_id")) or _normalize_string(action.get("target_id")) or "governance-intervention-engine",
        label=_normalize_string(payload.get("label")) or _normalize_string(action.get("title")) or "Governance Intervention Engine",
        path=_normalize_string(payload.get("path")) or "src/odylith/runtime/intervention_engine",
        kind=_normalize_string(payload.get("kind")) or "runtime",
        dry_run=False,
    ).as_dict()


def _apply_casebook_create(*, repo_root: Path, action: Mapping[str, Any]) -> dict[str, Any]:
    payload = _mapping(action.get("payload"))
    title = _normalize_string(payload.get("title")) or _normalize_string(action.get("title")) or "Governed Observation"
    component = _normalize_string(payload.get("component"))
    missing = bug_authoring.missing_capture_requirements(
        title=title,
        component=component,
        payload=payload,
    )
    if missing:
        missing_flags = ", ".join(f"`{item}`" for item in missing)
        raise ValueError(
            "Casebook create requires grounded bug-capture evidence before apply; "
            f"missing or placeholder fields: {missing_flags}"
        )
    return bug_authoring.capture_bug_from_payload(
        repo_root=repo_root,
        title=title,
        component=component,
        severity="P2",
        payload=payload,
        dry_run=False,
    ).as_dict()


def _apply_atlas_create(*, repo_root: Path, action: Mapping[str, Any]) -> dict[str, Any]:
    payload = _mapping(action.get("payload"))
    backlog_refs = payload.get("related_backlog")
    plan_refs = payload.get("related_plans")
    doc_refs = payload.get("related_docs")
    if not isinstance(backlog_refs, list) or not backlog_refs:
        raise ValueError("Atlas create requires `related_backlog` in the proposal payload")
    if not isinstance(plan_refs, list) or not plan_refs:
        raise ValueError("Atlas create requires `related_plans` in the proposal payload")
    if not isinstance(doc_refs, list) or not doc_refs:
        raise ValueError("Atlas create requires `related_docs` in the proposal payload")
    catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    diagram_id = _next_diagram_id(catalog_path)
    slug = _normalize_string(payload.get("slug")) or _normalize_string(action.get("target_id")).replace("proposed:", "") or "governed-observation"
    title = _normalize_string(payload.get("title")) or _normalize_string(action.get("title")) or "Governed Observation Topology"
    argv = [
        "--repo-root",
        str(repo_root),
        "--diagram-id",
        diagram_id,
        "--slug",
        slug,
        "--title",
        title,
        "--kind",
        _normalize_string(payload.get("kind")) or "flowchart",
        "--owner",
        "product",
        "--summary",
        f"Topology and governance observation for {title}.",
        "--component",
        f"{_normalize_string(payload.get('component_id')) or 'governance-intervention-engine'}::Owned runtime boundary for this proposal.",
        "--create-source-if-missing",
    ]
    for token in backlog_refs:
        argv.extend(["--backlog", str(token)])
    for token in plan_refs:
        argv.extend(["--plan", str(token)])
    for token in doc_refs:
        argv.extend(["--doc", str(token)])
    rc = scaffold_mermaid_diagram.main(argv)
    if rc != 0:
        raise ValueError("Atlas scaffold failed")
    return {"diagram_id": diagram_id, "slug": slug, "title": title}


def apply_proposal_bundle(
    *,
    repo_root: Path,
    payload: Mapping[str, Any],
    decline: bool = False,
) -> dict[str, Any]:
    proposal = _proposal_payload(payload)
    proposal_key = _normalize_string(proposal.get("key"))
    observation = _mapping(payload.get("observation"))
    session_id = _normalize_string(observation.get("session_id"))
    latest_event = _latest_proposal_event(
        repo_root=repo_root,
        proposal_key=proposal_key,
        session_id=session_id,
    )
    latest_kind = _normalize_string(latest_event.get("kind")).lower()
    host_family = _normalize_string(observation.get("host_family")) or _normalize_string(latest_event.get("host_family"))
    turn_phase = _normalize_string(observation.get("turn_phase"))
    prompt_excerpt = _normalize_string(observation.get("prompt_excerpt")) or _normalize_string(latest_event.get("prompt_excerpt"))
    assistant_summary = _normalize_string(observation.get("assistant_summary")) or _normalize_string(latest_event.get("assistant_summary"))
    candidate = _mapping(payload.get("candidate"))
    moment = _mapping(candidate.get("moment"))
    moment_kind = _normalize_string(moment.get("kind")) or _normalize_string(latest_event.get("moment_kind"))
    semantic_signature = proposal.get("semantic_signature")
    if not isinstance(semantic_signature, list):
        semantic_signature = moment.get("semantic_signature")
    if not isinstance(semantic_signature, list):
        semantic_signature = latest_event.get("semantic_signature")
    if decline:
        if latest_kind in {"capture_applied", "capture_declined"}:
            raise ValueError("proposal payload is stale")
        summary = _normalize_string(proposal.get("plain_text")) or "Odylith Proposal declined."
        stream_state.append_intervention_event(
            repo_root=repo_root,
            kind="capture_declined",
            summary="Odylith Proposal declined.",
            session_id=session_id,
            host_family=host_family,
            intervention_key=proposal_key,
            turn_phase=turn_phase,
            action_surfaces=proposal.get("action_surfaces", []),
            display_plain=str(proposal.get("plain_text") or summary),
            display_markdown=str(proposal.get("markdown_text") or ""),
            confirmation_text=_normalize_string(proposal.get("confirmation_text")),
            proposal_status="declined",
            prompt_excerpt=prompt_excerpt,
            assistant_summary=assistant_summary,
            moment_kind=moment_kind,
            semantic_signature=semantic_signature if isinstance(semantic_signature, list) else (),
        )
        return {"status": "declined", "applied": [], "skipped": []}
    if not bool(proposal.get("eligible")):
        raise ValueError("proposal payload is not eligible for apply")
    if bool(proposal.get("stale")) or latest_kind in {"capture_applied", "capture_declined"}:
        raise ValueError("proposal payload is stale")
    if not bool(proposal.get("apply_supported")):
        raise ValueError("proposal bundle is preview-only until every action has a safe CLI-backed apply path")
    actions = proposal.get("actions")
    if not isinstance(actions, list) or not actions:
        raise ValueError("proposal payload has no actions")
    supported_operations = {
        ("radar", "create"),
        ("registry", "create"),
        ("casebook", "create"),
        ("atlas", "create"),
    }
    normalized_actions: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, Mapping):
            raise ValueError("proposal payload has malformed actions")
        surface = _normalize_string(action.get("surface")).lower()
        operation = _normalize_string(action.get("action")).lower()
        if (surface, operation) not in supported_operations:
            raise ValueError("proposal payload has unsupported apply actions")
        normalized_actions.append(dict(action))

    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for action in normalized_actions:
        surface = _normalize_string(action.get("surface")).lower()
        operation = _normalize_string(action.get("action")).lower()
        if surface == "radar" and operation == "create":
            applied.append({"surface": "radar", "result": _apply_radar_create(repo_root=repo_root, action=action)})
            continue
        if surface == "registry" and operation == "create":
            applied.append({"surface": "registry", "result": _apply_registry_create(repo_root=repo_root, action=action)})
            continue
        if surface == "casebook" and operation == "create":
            applied.append({"surface": "casebook", "result": _apply_casebook_create(repo_root=repo_root, action=action)})
            continue
        if surface == "atlas" and operation == "create":
            applied.append({"surface": "atlas", "result": _apply_atlas_create(repo_root=repo_root, action=action)})
            continue
        skipped.append({"surface": surface, "reason": "unsupported"})

    if not applied:
        raise ValueError("proposal payload has no safe CLI-backed apply actions")
    if skipped:
        raise ValueError("proposal payload is stale or unsupported")

    summary = _normalize_string(proposal.get("plain_text")) or "Odylith Proposal applied."
    stream_state.append_intervention_event(
        repo_root=repo_root,
        kind="capture_applied",
        summary="Odylith Proposal applied.",
        session_id=session_id,
        host_family=host_family,
        intervention_key=proposal_key,
        turn_phase=turn_phase,
        action_surfaces=proposal.get("action_surfaces", []),
        display_plain=str(proposal.get("plain_text") or summary),
        display_markdown=str(proposal.get("markdown_text") or ""),
        confirmation_text=_normalize_string(proposal.get("confirmation_text")),
        proposal_status="applied",
        prompt_excerpt=prompt_excerpt,
        assistant_summary=assistant_summary,
        moment_kind=moment_kind,
        semantic_signature=semantic_signature if isinstance(semantic_signature, list) else (),
    )
    return {"status": "applied", "applied": applied, "skipped": skipped}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith governance capture-apply",
        description="Apply or decline one Odylith Proposal payload.",
    )
    parser.add_argument("--repo-root", default=".", help="Consumer repository root.")
    parser.add_argument("--payload-json", default="", help="Proposal payload JSON. Defaults to stdin.")
    parser.add_argument("--decline", action="store_true", help="Decline the proposal instead of applying it.")
    args = parser.parse_args(list(argv or ()))
    payload = _load_payload(_payload_text(str(args.payload_json)))
    try:
        result = apply_proposal_bundle(
            repo_root=Path(args.repo_root).expanduser().resolve(),
            payload=payload,
            decline=bool(args.decline),
        )
    except ValueError as exc:
        print(str(exc))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
