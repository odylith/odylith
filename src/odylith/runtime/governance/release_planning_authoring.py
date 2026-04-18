"""Release Planning Authoring helpers for the Odylith governance layer."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.governance import authoring_execution_policy
from odylith.runtime.governance import release_planning_contract
from odylith.runtime.governance import release_planning_view_model
from odylith.runtime.governance import validate_backlog_contract as backlog_contract


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith release",
        description="Create, inspect, and maintain repo-local release planning truth.",
    )
    parser.add_argument("--repo-root", default=".")
    subparsers = parser.add_subparsers(dest="release_command", required=True)

    create = subparsers.add_parser("create", help="Create one release definition in the release registry.")
    create.add_argument("release_id")
    create.add_argument("--status", default="planning", choices=("planning", "active", "shipped", "closed"))
    create.add_argument("--version", default="")
    create.add_argument("--tag", default="")
    create.add_argument("--name", default="")
    create.add_argument("--notes", default="")
    create.add_argument("--alias", action="append", default=[])
    create.add_argument("--dry-run", action="store_true")
    create.add_argument("--json", action="store_true", dest="as_json")

    update = subparsers.add_parser("update", help="Update one release definition or alias ownership.")
    update.add_argument("selector")
    update.add_argument("--status", choices=("planning", "active", "shipped", "closed"))
    update.add_argument("--version")
    update.add_argument("--tag")
    update.add_argument("--name")
    update.add_argument("--notes")
    update.add_argument("--alias", action="append", default=[])
    update.add_argument("--drop-alias", action="append", default=[])
    update.add_argument("--clear-aliases", action="store_true")
    update.add_argument("--dry-run", action="store_true")
    update.add_argument("--json", action="store_true", dest="as_json")

    listing = subparsers.add_parser("list", help="List known releases and alias ownership.")
    listing.add_argument("--json", action="store_true", dest="as_json")

    show = subparsers.add_parser("show", help="Show one release and its active assignments.")
    show.add_argument("selector")
    show.add_argument("--json", action="store_true", dest="as_json")

    add = subparsers.add_parser("add", help="Assign one backlog workstream to a release.")
    add.add_argument("workstream_id")
    add.add_argument("selector")
    add.add_argument("--note", default="")
    add.add_argument("--dry-run", action="store_true")
    add.add_argument("--json", action="store_true", dest="as_json")

    remove = subparsers.add_parser("remove", help="Remove one backlog workstream from its active release.")
    remove.add_argument("workstream_id")
    remove.add_argument("selector", nargs="?", default="")
    remove.add_argument("--note", default="")
    remove.add_argument("--dry-run", action="store_true")
    remove.add_argument("--json", action="store_true", dest="as_json")

    move = subparsers.add_parser("move", help="Move one backlog workstream from its active release to another release.")
    move.add_argument("workstream_id")
    move.add_argument("selector")
    move.add_argument("--from-release", default="")
    move.add_argument("--note", default="")
    move.add_argument("--dry-run", action="store_true")
    move.add_argument("--json", action="store_true", dest="as_json")

    return parser.parse_args(argv)


def _load_governed_documents(*, repo_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, backlog_contract.IdeaSpec]]:
    registry_path = release_planning_contract.releases_registry_path(repo_root=repo_root)
    event_log_path = release_planning_contract.release_assignment_event_log_path(repo_root=repo_root)
    registry_document, registry_errors = release_planning_contract.load_registry_document(path=registry_path)
    event_documents, event_errors = release_planning_contract.load_assignment_event_documents(path=event_log_path)
    idea_specs, idea_errors = backlog_contract._validate_idea_specs(  # noqa: SLF001
        repo_root.joinpath("odylith/radar/source/ideas")
    )
    all_errors = [*registry_errors, *event_errors, *idea_errors]
    if all_errors:
        raise ValueError("\n".join(all_errors))
    return registry_document, event_documents, idea_specs


def _render_release_payload(*, payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2) + "\n"


def _release_row_by_id(releases: list[dict[str, Any]], release_id: str) -> dict[str, Any] | None:
    token = str(release_id or "").strip()
    for row in releases:
        if str(row.get("release_id", "")).strip() == token:
            return row
    return None


def _registry_release_rows(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in document.get("releases", [])
        if isinstance(row, Mapping) and str(row.get("release_id", "")).strip()
    ]


def _registry_alias_map(document: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(document.get("aliases"), Mapping):
        return {}
    return {
        release_planning_contract.canonical_alias_token(alias): str(release_id or "").strip()
        for alias, release_id in document.get("aliases", {}).items()
        if release_planning_contract.canonical_alias_token(alias) and str(release_id or "").strip()
    }


def _validated_state(
    *,
    repo_root: Path,
    registry_document: Mapping[str, Any],
    event_documents: Sequence[Mapping[str, Any]],
    idea_specs: Mapping[str, backlog_contract.IdeaSpec],
) -> tuple[release_planning_contract.ReleasePlanningState, dict[str, Any]]:
    state, errors = release_planning_contract.validate_release_planning_payload(
        repo_root=repo_root,
        idea_specs=idea_specs,
        registry_document=registry_document,
        event_documents=event_documents,
    )
    if errors:
        raise ValueError("\n".join(errors))
    payload = release_planning_view_model.build_release_view_payload(state=state)
    return state, payload


def _write_registry_document(*, repo_root: Path, document: Mapping[str, Any]) -> Path:
    target = release_planning_contract.releases_registry_path(repo_root=repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    rendered = release_planning_contract.render_registry_document(
        releases=_registry_release_rows(document),
        aliases=_registry_alias_map(document),
        updated_utc=str(document.get("updated_utc", "")).strip(),
    )
    target.write_text(rendered, encoding="utf-8")
    return target


def _append_event_document(*, repo_root: Path, event: Mapping[str, Any]) -> Path:
    target = release_planning_contract.release_assignment_event_log_path(repo_root=repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(release_planning_contract.render_assignment_event(event))
    return target


def _append_event_documents(*, repo_root: Path, events: Sequence[Mapping[str, Any]]) -> Path:
    target = release_planning_contract.release_assignment_event_log_path(repo_root=repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(release_planning_contract.render_assignment_event(event))
    return target


def _ensure_release_mutable(release: release_planning_contract.ReleaseRecord) -> None:
    if release.terminal:
        raise ValueError(
            f"release `{release.release_id}` is `{release.status}` and its definition is immutable; update alias ownership or create a new release instead"
        )


def _release_governance_decision(
    *,
    repo_root: Path,
    action: str,
    target_scope: Sequence[str],
    requested_scope: Sequence[str],
    preferred_alternative: str,
) -> authoring_execution_policy.GovernedAuthoringDecision:
    registry_path = release_planning_contract.releases_registry_path(repo_root=repo_root)
    event_log_path = release_planning_contract.release_assignment_event_log_path(repo_root=repo_root)
    governed_scope = [str(item).strip() for item in target_scope if str(item).strip()]
    return authoring_execution_policy.evaluate_governed_authoring_action(
        action=action,
        objective="Maintain the authoritative release-planning registry and release assignment history.",
        authoritative_lane="governance.release_planning.authoritative",
        target_scope=governed_scope,
        requested_scope=[str(item).strip() for item in requested_scope if str(item).strip()],
        governed_scope=governed_scope,
        resource_set=[
            str(registry_path.relative_to(repo_root)),
            str(event_log_path.relative_to(repo_root)),
        ],
        success_criteria=[
            "release-planning truth stays authoritative",
            "release mutations stay within the governed release scope",
        ],
        validation_plan=[
            "odylith validate backlog-contract --repo-root .",
        ],
        allowed_moves=[action, "re_anchor"],
        critical_path=[action, "validate_backlog_contract"],
        preferred_alternative=preferred_alternative,
    )


def _print_or_json(*, payload: Mapping[str, Any], as_json: bool) -> None:
    if as_json:
        print(_render_release_payload(payload=payload), end="")
        return
    command = str(payload.get("command", "")).strip()
    if command == "list":
        releases = payload.get("releases", [])
        if not isinstance(releases, list) or not releases:
            print("no releases defined")
            return
        print("release catalog")
        for row in releases:
            if not isinstance(row, Mapping):
                continue
            aliases = [str(item).strip() for item in row.get("aliases", []) if str(item).strip()]
            alias_label = f" aliases={','.join(aliases)}" if aliases else ""
            print(
                "- "
                + f"{str(row.get('release_id', '')).strip()} "
                + f"[{str(row.get('status', '')).strip()}] "
                + f"{str(row.get('display_label', '')).strip() or str(row.get('release_id', '')).strip()}"
                + alias_label
                + f" active_workstreams={int(row.get('active_workstream_count', 0) or 0)}"
            )
        return
    release = payload.get("release")
    if isinstance(release, Mapping):
        print(str(release.get("display_label", release.get("release_id", ""))).strip())
        print(f"- release_id: {str(release.get('release_id', '')).strip()}")
        print(f"- status: {str(release.get('status', '')).strip()}")
        aliases = [str(item).strip() for item in release.get("aliases", []) if str(item).strip()]
        print(f"- aliases: {', '.join(aliases) if aliases else '-'}")
        if str(release.get("version", "")).strip():
            print(f"- version: {str(release.get('version', '')).strip()}")
        if str(release.get("tag", "")).strip():
            print(f"- tag: {str(release.get('tag', '')).strip()}")
        workstreams = [str(item).strip() for item in release.get("active_workstreams", []) if str(item).strip()]
        print(f"- active workstreams: {', '.join(workstreams) if workstreams else '-'}")
        return
    print(_render_release_payload(payload=payload), end="")


def _event_payload(
    *,
    action: str,
    workstream_id: str,
    release_id: str = "",
    from_release_id: str = "",
    to_release_id: str = "",
    note: str = "",
    recorded_at: str | None = None,
) -> dict[str, Any]:
    return {
        "action": str(action).strip(),
        "workstream_id": str(workstream_id).strip().upper(),
        "release_id": str(release_id).strip(),
        "from_release_id": str(from_release_id).strip(),
        "to_release_id": str(to_release_id).strip(),
        "recorded_at": str(recorded_at or "").strip() or release_planning_contract.utc_now_iso(),
        "note": str(note).strip(),
    }


def _run_create(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    registry_document, event_documents, idea_specs = _load_governed_documents(repo_root=repo_root)
    document = copy.deepcopy(registry_document)
    releases = _registry_release_rows(document)
    aliases = _registry_alias_map(document)
    release_id = str(args.release_id or "").strip()
    if _release_row_by_id(releases, release_id) is not None:
        raise ValueError(f"release `{release_id}` already exists")
    releases.append(
        {
            "release_id": release_id,
            "status": str(args.status or "").strip() or "planning",
            "version": str(args.version or "").strip(),
            "tag": str(args.tag or "").strip(),
            "name": str(args.name or "").strip(),
            "notes": str(args.notes or "").strip(),
            "created_utc": release_planning_contract.utc_now_iso()[:10],
            "shipped_utc": "",
            "closed_utc": "",
        }
    )
    for alias in getattr(args, "alias", []) or []:
        aliases[release_planning_contract.canonical_alias_token(alias)] = release_id
    document["releases"] = releases
    document["aliases"] = aliases
    document["updated_utc"] = release_planning_contract.utc_now_iso()[:10]
    state, payload = _validated_state(
        repo_root=repo_root,
        registry_document=document,
        event_documents=event_documents,
        idea_specs=idea_specs,
    )
    governance = _release_governance_decision(
        repo_root=repo_root,
        action="mutate_release_create",
        target_scope=[release_id],
        requested_scope=[release_id],
        preferred_alternative=f"odylith release show {release_id}",
    )
    authoring_execution_policy.enforce_governed_authoring_action(governance)
    if not bool(args.dry_run):
        _write_registry_document(repo_root=repo_root, document=document)
    release = next(row for row in payload["catalog"] if row["release_id"] == release_id)
    return {
        "command": "create",
        "dry_run": bool(args.dry_run),
        "release": release,
        "registry_path": str(state.registry_path),
        "execution_engine": governance.to_dict(),
    }


def _run_update(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    registry_document, event_documents, idea_specs = _load_governed_documents(repo_root=repo_root)
    state, _payload = _validated_state(
        repo_root=repo_root,
        registry_document=registry_document,
        event_documents=event_documents,
        idea_specs=idea_specs,
    )
    release = state.release_for_selector(args.selector)
    document = copy.deepcopy(registry_document)
    releases = _registry_release_rows(document)
    aliases = _registry_alias_map(document)
    row = _release_row_by_id(releases, release.release_id)
    if row is None:
        raise ValueError(f"missing release `{release.release_id}` in registry document")
    field_updates = {
        key: value
        for key, value in {
            "status": getattr(args, "status", None),
            "version": getattr(args, "version", None),
            "tag": getattr(args, "tag", None),
            "name": getattr(args, "name", None),
            "notes": getattr(args, "notes", None),
        }.items()
        if value is not None
    }
    if field_updates:
        _ensure_release_mutable(release)
    changed = False
    for field_name, value in field_updates.items():
        normalized = str(value or "").strip()
        if str(row.get(field_name, "")).strip() == normalized:
            continue
        row[field_name] = normalized
        changed = True
        if field_name == "status":
            if normalized == "shipped" and not str(row.get("shipped_utc", "")).strip():
                row["shipped_utc"] = release_planning_contract.utc_now_iso()[:10]
            if normalized == "closed" and not str(row.get("closed_utc", "")).strip():
                row["closed_utc"] = release_planning_contract.utc_now_iso()[:10]
    if bool(args.clear_aliases):
        to_drop = [alias for alias, owner in aliases.items() if owner == release.release_id]
        for alias in to_drop:
            aliases.pop(alias, None)
            changed = True
    for alias in getattr(args, "drop_alias", []) or []:
        alias_token = release_planning_contract.canonical_alias_token(alias)
        if aliases.get(alias_token) == release.release_id:
            aliases.pop(alias_token, None)
            changed = True
    for alias in getattr(args, "alias", []) or []:
        alias_token = release_planning_contract.canonical_alias_token(alias)
        if aliases.get(alias_token) != release.release_id:
            aliases[alias_token] = release.release_id
            changed = True
    if not changed:
        raise ValueError(f"release `{release.release_id}` update is a no-op")
    document["releases"] = releases
    document["aliases"] = aliases
    document["updated_utc"] = release_planning_contract.utc_now_iso()[:10]
    state, payload = _validated_state(
        repo_root=repo_root,
        registry_document=document,
        event_documents=event_documents,
        idea_specs=idea_specs,
    )
    governance = _release_governance_decision(
        repo_root=repo_root,
        action="mutate_release_update",
        target_scope=[release.release_id],
        requested_scope=[release.release_id],
        preferred_alternative=f"odylith release show {release.release_id}",
    )
    authoring_execution_policy.enforce_governed_authoring_action(governance)
    if not bool(args.dry_run):
        _write_registry_document(repo_root=repo_root, document=document)
    updated = next(row for row in payload["catalog"] if row["release_id"] == release.release_id)
    return {
        "command": "update",
        "dry_run": bool(args.dry_run),
        "release": updated,
        "registry_path": str(state.registry_path),
        "execution_engine": governance.to_dict(),
    }


def _run_list(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    registry_document, event_documents, idea_specs = _load_governed_documents(repo_root=repo_root)
    state, payload = _validated_state(
        repo_root=repo_root,
        registry_document=registry_document,
        event_documents=event_documents,
        idea_specs=idea_specs,
    )
    return {
        "command": "list",
        "releases": payload.get("catalog", []),
        "aliases": payload.get("aliases", {}),
        "summary": payload.get("summary", {}),
        "registry_path": str(state.registry_path),
        "event_log_path": str(state.event_log_path),
    }


def _run_show(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    registry_document, event_documents, idea_specs = _load_governed_documents(repo_root=repo_root)
    state, payload = _validated_state(
        repo_root=repo_root,
        registry_document=registry_document,
        event_documents=event_documents,
        idea_specs=idea_specs,
    )
    release = state.release_for_selector(args.selector)
    release_row = next(row for row in payload["catalog"] if row["release_id"] == release.release_id)
    matching_history = {
        workstream_id: dict(row)
        for workstream_id, row in payload.get("workstreams", {}).items()
        if isinstance(row, Mapping)
        and str(row.get("active_release_id", "")).strip() == release.release_id
    }
    return {
        "command": "show",
        "release": release_row,
        "active_workstreams": sorted(matching_history),
    }


def _event_mutation(
    *,
    repo_root: Path,
    args: argparse.Namespace,
    builder,
) -> dict[str, Any]:
    registry_document, event_documents, idea_specs = _load_governed_documents(repo_root=repo_root)
    state, payload = _validated_state(
        repo_root=repo_root,
        registry_document=registry_document,
        event_documents=event_documents,
        idea_specs=idea_specs,
    )
    builder_output = builder(state=state, payload=payload)
    next_events = [dict(builder_output)] if isinstance(builder_output, Mapping) else [dict(row) for row in builder_output]
    if not next_events:
        raise ValueError("release mutation produced no events")
    candidate_events = [*event_documents, *next_events]
    next_state, next_payload = _validated_state(
        repo_root=repo_root,
        registry_document=registry_document,
        event_documents=candidate_events,
        idea_specs=idea_specs,
    )
    if not bool(args.dry_run):
        _append_event_documents(repo_root=repo_root, events=next_events)
    workstream_id = str(next_events[-1].get("workstream_id", "")).strip().upper()
    scope_tokens = [
        workstream_id,
        str(next_events[-1].get("release_id", "")).strip(),
        str(next_events[-1].get("from_release_id", "")).strip(),
        str(next_events[-1].get("to_release_id", "")).strip(),
    ]
    scope_tokens = [token for token in scope_tokens if token]
    show_selector = str(next_events[-1].get("to_release_id", "")).strip() or str(next_events[-1].get("release_id", "")).strip()
    governance = _release_governance_decision(
        repo_root=repo_root,
        action=f"mutate_release_{str(args.release_command).strip()}",
        target_scope=scope_tokens,
        requested_scope=scope_tokens,
        preferred_alternative=f"odylith release show {show_selector}" if show_selector else "odylith release list",
    )
    authoring_execution_policy.enforce_governed_authoring_action(governance)
    return {
        "command": str(args.release_command).strip(),
        "dry_run": bool(args.dry_run),
        "event": next_events[-1],
        "events": next_events,
        "workstream_id": workstream_id,
        "workstream_release": dict(next_payload.get("workstreams", {}).get(workstream_id, {})),
        "event_log_path": str(next_state.event_log_path),
        "execution_engine": governance.to_dict(),
    }


def _run_add(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()

    def _builder(*, state, payload):  # noqa: ANN001
        workstream_id = str(args.workstream_id or "").strip().upper()
        if workstream_id in state.active_release_by_workstream:
            current_release = state.active_release_by_workstream[workstream_id]
            raise ValueError(
                f"`{workstream_id}` already targets `{current_release}`; use `odylith release move` instead"
            )
        release = state.release_for_selector(args.selector)
        if release.terminal:
            raise ValueError(f"cannot add `{workstream_id}` to terminal release `{release.release_id}`")
        workstream_status = state.workstream_status_by_id.get(workstream_id, "")
        history = tuple(state.history_by_workstream.get(workstream_id, ()))
        if workstream_status == "finished":
            if history:
                latest = history[-1]
                if str(latest.action).strip().lower() == "remove" and str(latest.release_id).strip() == release.release_id:
                    raise ValueError(f"`{workstream_id}` is already recorded as completed in `{release.release_id}`")
            recorded_at = release_planning_contract.utc_now_iso()
            return [
                _event_payload(
                    action="add",
                    workstream_id=workstream_id,
                    release_id=release.release_id,
                    note=args.note,
                    recorded_at=recorded_at,
                ),
                _event_payload(
                    action="remove",
                    workstream_id=workstream_id,
                    release_id=release.release_id,
                    note=args.note,
                    recorded_at=recorded_at,
                ),
            ]
        return _event_payload(
            action="add",
            workstream_id=workstream_id,
            release_id=release.release_id,
            note=args.note,
        )

    return _event_mutation(repo_root=repo_root, args=args, builder=_builder)


def add_workstreams_to_release(
    *,
    repo_root: Path,
    workstream_ids: Sequence[str],
    selector: str,
    note: str = "",
    idea_specs: Mapping[str, backlog_contract.IdeaSpec] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Assign one or more known workstreams to a release after full preflight."""
    root = Path(repo_root).resolve()
    registry_document, event_documents, loaded_idea_specs = _load_governed_documents(repo_root=root)
    effective_idea_specs = dict(idea_specs if idea_specs is not None else loaded_idea_specs)
    state, _payload = _validated_state(
        repo_root=root,
        registry_document=registry_document,
        event_documents=event_documents,
        idea_specs=effective_idea_specs,
    )
    release = state.release_for_selector(selector)
    if release.terminal:
        raise ValueError(f"cannot add workstreams to terminal release `{release.release_id}`")
    normalized_ids: list[str] = []
    for raw_id in workstream_ids:
        workstream_id = str(raw_id or "").strip().upper()
        if not workstream_id:
            continue
        if workstream_id in normalized_ids:
            raise ValueError(f"duplicate workstream id `{workstream_id}` in release assignment request")
        if workstream_id not in effective_idea_specs:
            raise ValueError(f"unknown workstream `{workstream_id}`")
        if workstream_id in state.active_release_by_workstream:
            current_release = state.active_release_by_workstream[workstream_id]
            raise ValueError(
                f"`{workstream_id}` already targets `{current_release}`; use `odylith release move` instead"
            )
        normalized_ids.append(workstream_id)
    if not normalized_ids:
        raise ValueError("release assignment requires at least one workstream id")

    recorded_at = release_planning_contract.utc_now_iso()
    events = [
        _event_payload(
            action="add",
            workstream_id=workstream_id,
            release_id=release.release_id,
            note=note,
            recorded_at=recorded_at,
        )
        for workstream_id in normalized_ids
    ]
    candidate_events = [*event_documents, *events]
    next_state, next_payload = _validated_state(
        repo_root=root,
        registry_document=registry_document,
        event_documents=candidate_events,
        idea_specs=effective_idea_specs,
    )
    governance = _release_governance_decision(
        repo_root=root,
        action="mutate_release_add",
        target_scope=[*normalized_ids, release.release_id],
        requested_scope=[*normalized_ids, release.release_id],
        preferred_alternative=f"odylith release show {release.release_id}",
    )
    authoring_execution_policy.enforce_governed_authoring_action(governance)
    if not bool(dry_run):
        _append_event_documents(repo_root=root, events=events)
    return {
        "command": "add",
        "dry_run": bool(dry_run),
        "events": events,
        "workstream_ids": normalized_ids,
        "release": next(row for row in next_payload["catalog"] if row["release_id"] == release.release_id),
        "event_log_path": str(next_state.event_log_path),
        "execution_engine": governance.to_dict(),
    }


def _run_remove(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()

    def _builder(*, state, payload):  # noqa: ANN001
        workstream_id = str(args.workstream_id or "").strip().upper()
        active_release_id = state.active_release_by_workstream.get(workstream_id, "")
        if not active_release_id:
            raise ValueError(f"`{workstream_id}` has no active release target")
        if str(args.selector or "").strip():
            selected = state.release_for_selector(args.selector)
            if selected.release_id != active_release_id:
                raise ValueError(
                    f"`{workstream_id}` targets `{active_release_id}`, not `{selected.release_id}`"
                )
        return _event_payload(
            action="remove",
            workstream_id=workstream_id,
            release_id=active_release_id,
            note=args.note,
        )

    return _event_mutation(repo_root=repo_root, args=args, builder=_builder)


def _run_move(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()

    def _builder(*, state, payload):  # noqa: ANN001
        workstream_id = str(args.workstream_id or "").strip().upper()
        active_release_id = state.active_release_by_workstream.get(workstream_id, "")
        if not active_release_id:
            raise ValueError(f"`{workstream_id}` has no active release target to move")
        from_release_id = active_release_id
        if str(args.from_release or "").strip():
            from_release = state.release_for_selector(args.from_release)
            from_release_id = from_release.release_id
        target = state.release_for_selector(args.selector)
        if target.release_id == active_release_id:
            raise ValueError(f"`{workstream_id}` already targets `{target.release_id}`")
        if target.terminal:
            raise ValueError(f"cannot move `{workstream_id}` into terminal release `{target.release_id}`")
        return _event_payload(
            action="move",
            workstream_id=workstream_id,
            from_release_id=from_release_id,
            to_release_id=target.release_id,
            note=args.note,
        )

    return _event_mutation(repo_root=repo_root, args=args, builder=_builder)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        payload = {
            "create": _run_create,
            "update": _run_update,
            "list": _run_list,
            "show": _run_show,
            "add": _run_add,
            "remove": _run_remove,
            "move": _run_move,
        }[str(args.release_command).strip()](args)
    except ValueError as exc:
        print(str(exc))
        return 2
    _print_or_json(payload=payload, as_json=bool(getattr(args, "as_json", False)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
