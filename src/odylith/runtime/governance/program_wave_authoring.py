from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.governance import authoring_execution_policy
from odylith.runtime.governance import execution_wave_contract
from odylith.runtime.governance import program_wave_execution_governance
from odylith.runtime.governance import validate_backlog_contract as backlog_contract

_ROLE_TO_FIELD = {
    "primary": "primary_workstreams",
    "carried": "carried_workstreams",
    "in_band": "in_band_workstreams",
}


def _wave_sort_key(wave_id: str) -> tuple[int, str]:
    token = str(wave_id or "").strip()
    if token.startswith("W") and token[1:].isdigit():
        return (int(token[1:]), token)
    return (10_000, token)


def _parse_program_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith program",
        description="Create, inspect, and maintain umbrella execution-wave programs.",
    )
    parser.add_argument("--repo-root", default=".")
    subparsers = parser.add_subparsers(dest="program_command", required=True)

    create = subparsers.add_parser("create", help="Create one umbrella execution-wave program.")
    create.add_argument("umbrella_id")
    create.add_argument("--dry-run", action="store_true")
    create.add_argument("--json", action="store_true", dest="as_json")

    update = subparsers.add_parser("update", help="Update program-level wave posture.")
    update.add_argument("umbrella_id")
    update.add_argument("--activate-wave")
    update.add_argument("--complete-wave", action="append", default=[])
    update.add_argument("--block-wave", action="append", default=[])
    update.add_argument("--plan-wave", action="append", default=[])
    update.add_argument("--sync-children", action="store_true")
    update.add_argument("--dry-run", action="store_true")
    update.add_argument("--json", action="store_true", dest="as_json")

    listing = subparsers.add_parser("list", help="List known execution-wave programs.")
    listing.add_argument("--json", action="store_true", dest="as_json")

    show = subparsers.add_parser("show", help="Show one program payload.")
    show.add_argument("umbrella_id")
    show.add_argument("--json", action="store_true", dest="as_json")

    status = subparsers.add_parser("status", help="Show one program summary and next posture.")
    status.add_argument("umbrella_id")
    status.add_argument("--json", action="store_true", dest="as_json")

    nxt = subparsers.add_parser("next", help="Return one truthful next authoring command.")
    nxt.add_argument("umbrella_id")
    nxt.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args(argv)


def _parse_wave_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith wave",
        description="Create, inspect, and maintain execution-wave members and gates.",
    )
    parser.add_argument("--repo-root", default=".")
    subparsers = parser.add_subparsers(dest="wave_command", required=True)

    create = subparsers.add_parser("create", help="Create one wave inside an existing program.")
    create.add_argument("umbrella_id")
    create.add_argument("wave_id")
    create.add_argument("--label", required=True)
    create.add_argument("--summary", default="")
    create.add_argument("--status", default="planned", choices=sorted(execution_wave_contract.VALID_WAVE_STATUSES))
    create.add_argument("--depends-on", action="append", default=[])
    create.add_argument("--dry-run", action="store_true")
    create.add_argument("--json", action="store_true", dest="as_json")

    update = subparsers.add_parser("update", help="Update one wave's label, summary, or status.")
    update.add_argument("umbrella_id")
    update.add_argument("wave_id")
    update.add_argument("--label")
    update.add_argument("--summary")
    update.add_argument("--status", choices=sorted(execution_wave_contract.VALID_WAVE_STATUSES))
    update.add_argument("--depends-on", action="append", default=[])
    update.add_argument("--clear-depends-on", action="store_true")
    update.add_argument("--dry-run", action="store_true")
    update.add_argument("--json", action="store_true", dest="as_json")

    assign = subparsers.add_parser("assign", help="Assign one workstream to one wave role.")
    assign.add_argument("umbrella_id")
    assign.add_argument("wave_id")
    assign.add_argument("workstream_id")
    assign.add_argument("--role", default="primary", choices=sorted(_ROLE_TO_FIELD))
    assign.add_argument("--dry-run", action="store_true")
    assign.add_argument("--json", action="store_true", dest="as_json")

    unassign = subparsers.add_parser("unassign", help="Remove one workstream from all roles in one wave.")
    unassign.add_argument("umbrella_id")
    unassign.add_argument("wave_id")
    unassign.add_argument("workstream_id")
    unassign.add_argument("--dry-run", action="store_true")
    unassign.add_argument("--json", action="store_true", dest="as_json")

    gate_add = subparsers.add_parser("gate-add", help="Add one gate ref for a wave member.")
    gate_add.add_argument("umbrella_id")
    gate_add.add_argument("wave_id")
    gate_add.add_argument("workstream_id")
    gate_add.add_argument("--label", default="")
    gate_add.add_argument("--plan-path", default="")
    gate_add.add_argument("--dry-run", action="store_true")
    gate_add.add_argument("--json", action="store_true", dest="as_json")

    gate_remove = subparsers.add_parser("gate-remove", help="Remove one gate ref for a wave member.")
    gate_remove.add_argument("umbrella_id")
    gate_remove.add_argument("wave_id")
    gate_remove.add_argument("workstream_id")
    gate_remove.add_argument("--dry-run", action="store_true")
    gate_remove.add_argument("--json", action="store_true", dest="as_json")

    status = subparsers.add_parser("status", help="Show one wave's current member and gate posture.")
    status.add_argument("umbrella_id")
    status.add_argument("wave_id")
    status.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args(argv)


def _idea_specs(repo_root: Path) -> dict[str, backlog_contract.IdeaSpec]:
    idea_specs, errors = backlog_contract._validate_idea_specs(repo_root / "odylith" / "radar" / "source" / "ideas")  # noqa: SLF001
    if errors:
        raise ValueError("\n".join(errors))
    return idea_specs


def _resolve_umbrella_spec(
    *,
    selector: str,
    idea_specs: Mapping[str, backlog_contract.IdeaSpec],
) -> backlog_contract.IdeaSpec:
    token = str(selector or "").strip().upper()
    spec = idea_specs.get(token)
    if spec is None:
        raise ValueError(f"unknown umbrella `{selector}`")
    if str(spec.metadata.get("workstream_type", "")).strip().lower() != "umbrella":
        raise ValueError(f"`{token}` is not an umbrella workstream")
    return spec


def _resolve_workstream_spec(
    *,
    selector: str,
    idea_specs: Mapping[str, backlog_contract.IdeaSpec],
) -> backlog_contract.IdeaSpec:
    token = str(selector or "").strip().upper()
    spec = idea_specs.get(token)
    if spec is None:
        raise ValueError(f"unknown workstream `{selector}`")
    return spec


def _ensure_child_of_umbrella(
    *,
    umbrella_id: str,
    workstream_spec: backlog_contract.IdeaSpec,
) -> None:
    workstream_id = str(workstream_spec.metadata.get("idea_id", "")).strip()
    parent = str(workstream_spec.metadata.get("workstream_parent", "")).strip()
    if workstream_id == umbrella_id:
        raise ValueError(f"umbrella `{umbrella_id}` cannot be assigned as a wave member")
    if parent != umbrella_id:
        raise ValueError(
            f"workstream `{workstream_id}` is not a child of umbrella `{umbrella_id}`"
        )


def _parse_front_matter(path: Path) -> tuple[list[tuple[str, str]], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing front matter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError(f"{path}: malformed front matter")
    header_text = text[4:end]
    body = text[end + 5 :]
    entries: list[tuple[str, str]] = []
    for line in header_text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        entries.append((key.strip(), value.strip()))
    return entries, body


def _write_front_matter(path: Path, entries: list[tuple[str, str]], body: str) -> None:
    rendered_header = "\n".join(f"{key}: {value}" for key, value in entries)
    path.write_text(f"---\n{rendered_header}\n---\n{body}", encoding="utf-8")


def _update_idea_metadata(path: Path, updates: Mapping[str, str]) -> None:
    entries, body = _parse_front_matter(path)
    index = {key: idx for idx, (key, _value) in enumerate(entries)}
    for key, value in updates.items():
        token = str(value or "").strip()
        if key in index:
            entries[index[key]] = (key, token)
        else:
            entries.append((key, token))
    _write_front_matter(path, entries, body)


def _program_path(repo_root: Path, umbrella_id: str) -> Path:
    return execution_wave_contract.program_path(repo_root=repo_root, umbrella_id=umbrella_id)


def _load_program_document(repo_root: Path, umbrella_id: str) -> dict[str, Any]:
    path = _program_path(repo_root, umbrella_id)
    if not path.is_file():
        raise ValueError(f"missing program file `{execution_wave_contract.program_relative_path(umbrella_id)}`")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_program_document(repo_root: Path, umbrella_id: str, payload: Mapping[str, Any]) -> Path:
    path = _program_path(repo_root, umbrella_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _metadata_list(spec: backlog_contract.IdeaSpec, key: str) -> list[str]:
    raw = str(spec.metadata.get(key, "")).strip()
    if not raw:
        return []
    return [token.strip() for token in raw.split(",") if token.strip()]


def _program_member_ids(document: Mapping[str, Any]) -> set[str]:
    members: set[str] = set()
    for wave in document.get("waves", []):
        if not isinstance(wave, Mapping):
            continue
        for field in _ROLE_TO_FIELD.values():
            for item in wave.get(field, []):
                token = str(item or "").strip()
                if token:
                    members.add(token)
    return members


def _sorted_waves(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [dict(row) for row in document.get("waves", []) if isinstance(row, Mapping)]
    return sorted(rows, key=lambda row: _wave_sort_key(str(row.get("wave_id", ""))))


def _find_wave(document: Mapping[str, Any], wave_id: str) -> dict[str, Any]:
    token = str(wave_id or "").strip()
    for wave in document.get("waves", []):
        if isinstance(wave, Mapping) and str(wave.get("wave_id", "")).strip() == token:
            return dict(wave)
    raise ValueError(f"unknown wave `{wave_id}`")


def _replace_wave(document: dict[str, Any], updated_wave: Mapping[str, Any]) -> None:
    token = str(updated_wave.get("wave_id", "")).strip()
    replaced = False
    waves: list[dict[str, Any]] = []
    for wave in document.get("waves", []):
        if not isinstance(wave, Mapping):
            continue
        if str(wave.get("wave_id", "")).strip() == token:
            waves.append(dict(updated_wave))
            replaced = True
        else:
            waves.append(dict(wave))
    if not replaced:
        waves.append(dict(updated_wave))
    document["waves"] = sorted(waves, key=lambda row: _wave_sort_key(str(row.get("wave_id", ""))))


def _scaffold_program_document(
    *,
    umbrella_id: str,
    umbrella_spec: backlog_contract.IdeaSpec,
    idea_specs: Mapping[str, backlog_contract.IdeaSpec],
) -> dict[str, Any]:
    children = _metadata_list(umbrella_spec, "workstream_children")
    if not children:
        raise ValueError(f"`{umbrella_id}` has no `workstream_children` to scaffold into waves")
    waves: list[dict[str, Any]] = []
    for index, child_id in enumerate(children, start=1):
        child = idea_specs.get(child_id)
        label = str(child.metadata.get("title", "")).strip() if child is not None else child_id
        waves.append(
            {
                "wave_id": f"W{index}",
                "label": label or child_id,
                "status": "active" if index == 1 else "planned",
                "summary": label or child_id,
                "depends_on": [] if index == 1 else [f"W{index - 1}"],
                "primary_workstreams": [child_id],
                "carried_workstreams": [],
                "in_band_workstreams": [],
                "gate_refs": [],
            }
        )
    return {"umbrella_id": umbrella_id, "version": "v1", "waves": waves}


def _sync_missing_children(
    *,
    document: dict[str, Any],
    umbrella_spec: backlog_contract.IdeaSpec,
    idea_specs: Mapping[str, backlog_contract.IdeaSpec],
) -> None:
    children = _metadata_list(umbrella_spec, "workstream_children")
    assigned = _program_member_ids(document)
    next_index = 1
    waves = _sorted_waves(document)
    if waves:
        next_index = _wave_sort_key(str(waves[-1].get("wave_id", "")))[0] + 1
    for child_id in children:
        if child_id in assigned:
            continue
        child = idea_specs.get(child_id)
        label = str(child.metadata.get("title", "")).strip() if child is not None else child_id
        document.setdefault("waves", []).append(
            {
                "wave_id": f"W{next_index}",
                "label": label or child_id,
                "status": "planned",
                "summary": label or child_id,
                "depends_on": [str(waves[-1].get("wave_id", "")).strip()] if waves else [],
                "primary_workstreams": [child_id],
                "carried_workstreams": [],
                "in_band_workstreams": [],
                "gate_refs": [],
            }
        )
        next_index += 1
        waves = _sorted_waves(document)


def _program_status_payload(
    *,
    umbrella_id: str,
    umbrella_spec: backlog_contract.IdeaSpec,
    document: Mapping[str, Any],
    idea_specs: Mapping[str, backlog_contract.IdeaSpec],
) -> dict[str, Any]:
    waves = _sorted_waves(document)
    active_wave = next((wave for wave in waves if str(wave.get("status", "")).strip() == "active"), None)
    completed_wave_ids = {
        str(wave.get("wave_id", "")).strip()
        for wave in waves
        if str(wave.get("status", "")).strip() == "complete"
    }
    next_wave = next(
        (
            wave
            for wave in waves
            if str(wave.get("status", "")).strip() == "planned"
            and all(dep in completed_wave_ids for dep in wave.get("depends_on", []))
        ),
        None,
    )
    child_ids = _metadata_list(umbrella_spec, "workstream_children")
    assigned = _program_member_ids(document)
    unassigned_children = [child for child in child_ids if child not in assigned]
    blocked = [str(wave.get("wave_id", "")).strip() for wave in waves if str(wave.get("status", "")).strip() == "blocked"]
    carried: list[str] = []
    for wave in waves:
        for item in wave.get("carried_workstreams", []):
            token = str(item or "").strip()
            if token and token not in carried:
                carried.append(token)
    return {
        "umbrella_id": umbrella_id,
        "title": str(umbrella_spec.metadata.get("title", "")).strip() or umbrella_id,
        "program_path": execution_wave_contract.program_relative_path(umbrella_id),
        "wave_count": len(waves),
        "active_wave": active_wave,
        "next_wave": next_wave,
        "blocked_waves": blocked,
        "carried_workstreams": carried,
        "unassigned_children": unassigned_children,
        "missing_structure": [f"unassigned:{child}" for child in unassigned_children],
        "host_general_contract": True,
        "execution_host_note": "host/model-specific nuance should stay behind detected execution profiles",
        "child_titles": {
            child_id: str(idea_specs[child_id].metadata.get("title", "")).strip() or child_id
            for child_id in child_ids
            if child_id in idea_specs
        },
    }


def _next_command(status_payload: Mapping[str, Any], *, idea_specs: Mapping[str, backlog_contract.IdeaSpec]) -> str:
    umbrella_id = str(status_payload.get("umbrella_id", "")).strip()
    active_wave = status_payload.get("active_wave")
    next_wave = status_payload.get("next_wave")
    unassigned_children = [str(item).strip() for item in status_payload.get("unassigned_children", []) if str(item).strip()]
    if not status_payload.get("wave_count"):
        return f"odylith program create {umbrella_id}"
    if not isinstance(active_wave, Mapping):
        if isinstance(next_wave, Mapping):
            return f"odylith program update {umbrella_id} --activate-wave {str(next_wave.get('wave_id', '')).strip()}"
        return f"odylith program status {umbrella_id}"
    active_wave_id = str(active_wave.get("wave_id", "")).strip()
    primary = [str(item).strip() for item in active_wave.get("primary_workstreams", []) if str(item).strip()]
    if not primary and unassigned_children:
        return f"odylith wave assign {umbrella_id} {active_wave_id} {unassigned_children[0]} --role primary"
    gate_workstreams = {
        str(row.get("workstream_id", "")).strip()
        for row in active_wave.get("gate_refs", [])
        if isinstance(row, Mapping)
    }
    for workstream_id in primary:
        spec = idea_specs.get(workstream_id)
        if spec is None:
            continue
        if str(spec.metadata.get("promoted_to_plan", "")).strip() and workstream_id not in gate_workstreams:
            title = str(spec.metadata.get("title", "")).strip() or workstream_id
            return f'odylith wave gate-add {umbrella_id} {active_wave_id} {workstream_id} --label "{title} gate"'
    return f"odylith program status {umbrella_id}"


def _print_program_payload(*, payload: Mapping[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2) + "\n", end="")
        return
    command = str(payload.get("command", "")).strip()
    if command == "list":
        programs = payload.get("programs", [])
        if not isinstance(programs, list) or not programs:
            print("no execution-wave programs")
            return
        print("execution-wave programs")
        for row in programs:
            if not isinstance(row, Mapping):
                continue
            print(
                "- "
                + f"{str(row.get('umbrella_id', '')).strip()} "
                + f"[waves={int(row.get('wave_count', 0) or 0)}] "
                + f"{str(row.get('title', '')).strip() or str(row.get('umbrella_id', '')).strip()}"
            )
        return
    if command == "next":
        print(str(payload.get("next_command", "")).strip())
        return
    if command == "status":
        print(str(payload.get("title", "")).strip() or str(payload.get("umbrella_id", "")).strip())
        active_wave = payload.get("active_wave")
        next_wave = payload.get("next_wave")
        print(f"- umbrella_id: {str(payload.get('umbrella_id', '')).strip()}")
        print(f"- active wave: {str(active_wave.get('wave_id', '')).strip() if isinstance(active_wave, Mapping) else '-'}")
        print(f"- next wave: {str(next_wave.get('wave_id', '')).strip() if isinstance(next_wave, Mapping) else '-'}")
        blocked = [str(item).strip() for item in payload.get("blocked_waves", []) if str(item).strip()]
        print(f"- blocked waves: {', '.join(blocked) if blocked else '-'}")
        unassigned = [str(item).strip() for item in payload.get("unassigned_children", []) if str(item).strip()]
        print(f"- unassigned children: {', '.join(unassigned) if unassigned else '-'}")
        print(f"- next command: {str(payload.get('next_command', '')).strip() or '-'}")
        return
    print(json.dumps(payload, indent=2) + "\n", end="")


def _print_wave_payload(*, payload: Mapping[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2) + "\n", end="")
        return
    wave = payload.get("wave")
    if isinstance(wave, Mapping):
        print(f"{str(payload.get('umbrella_id', '')).strip()} {str(wave.get('wave_id', '')).strip()}")
        print(f"- label: {str(wave.get('label', '')).strip()}")
        print(f"- status: {str(wave.get('status', '')).strip()}")
        print(
            "- primary: "
            + (", ".join(str(item).strip() for item in wave.get("primary_workstreams", []) if str(item).strip()) or "-")
        )
        print(
            "- carried: "
            + (", ".join(str(item).strip() for item in wave.get("carried_workstreams", []) if str(item).strip()) or "-")
        )
        print(
            "- in_band: "
            + (", ".join(str(item).strip() for item in wave.get("in_band_workstreams", []) if str(item).strip()) or "-")
        )
        gate_refs = wave.get("gate_refs", [])
        gate_labels = [str(row.get("label", "")).strip() for row in gate_refs if isinstance(row, Mapping)]
        print(f"- gates: {', '.join(label for label in gate_labels if label) if gate_labels else '-'}")
        return
    print(json.dumps(payload, indent=2) + "\n", end="")


def program_main(argv: Sequence[str] | None = None) -> int:
    args = _parse_program_args(argv)
    repo_root = Path(args.repo_root).resolve()
    idea_specs = _idea_specs(repo_root)

    if args.program_command == "list":
        programs: list[dict[str, Any]] = []
        for idea_id, spec in sorted(idea_specs.items()):
            if str(spec.metadata.get("workstream_type", "")).strip().lower() != "umbrella":
                continue
            program_path = _program_path(repo_root, idea_id)
            if not program_path.is_file() and str(spec.metadata.get("execution_model", "")).strip() != "umbrella_waves":
                continue
            wave_count = 0
            if program_path.is_file():
                try:
                    wave_count = len(json.loads(program_path.read_text(encoding="utf-8")).get("waves", []))
                except json.JSONDecodeError:
                    wave_count = 0
            programs.append(
                {
                    "umbrella_id": idea_id,
                    "title": str(spec.metadata.get("title", "")).strip() or idea_id,
                    "wave_count": wave_count,
                    "program_path": execution_wave_contract.program_relative_path(idea_id),
                }
            )
        _print_program_payload(payload={"command": "list", "programs": programs}, as_json=bool(args.as_json))
        return 0

    umbrella_spec = _resolve_umbrella_spec(selector=args.umbrella_id, idea_specs=idea_specs)
    umbrella_id = str(umbrella_spec.metadata.get("idea_id", "")).strip()

    if args.program_command == "create":
        if _program_path(repo_root, umbrella_id).is_file():
            raise ValueError(
                f"program `{execution_wave_contract.program_relative_path(umbrella_id)}` already exists"
            )
        governance = program_wave_execution_governance.program_governance_decision(
            repo_root=repo_root,
            umbrella_spec=umbrella_spec,
            document={"umbrella_id": umbrella_id, "version": "v1", "waves": []},
            args=args,
        )
        authoring_execution_policy.enforce_governed_authoring_action(governance)
        document = _scaffold_program_document(umbrella_id=umbrella_id, umbrella_spec=umbrella_spec, idea_specs=idea_specs)
        payload = {
            "command": "create",
            "umbrella_id": umbrella_id,
            "program": document,
            "execution_governance": governance.to_dict(),
        }
        if not args.dry_run:
            _update_idea_metadata(umbrella_spec.path, {"execution_model": "umbrella_waves"})
            _write_program_document(repo_root, umbrella_id, document)
        _print_program_payload(payload=payload, as_json=bool(args.as_json))
        return 0

    if args.program_command in {"status", "next"} and not _program_path(repo_root, umbrella_id).is_file():
        document = {"umbrella_id": umbrella_id, "version": "v1", "waves": []}
    else:
        document = _load_program_document(repo_root, umbrella_id)

    if args.program_command == "show":
        _print_program_payload(payload={"command": "show", "umbrella_id": umbrella_id, "program": document}, as_json=bool(args.as_json))
        return 0

    if args.program_command == "status":
        status_payload = _program_status_payload(
            umbrella_id=umbrella_id,
            umbrella_spec=umbrella_spec,
            document=document,
            idea_specs=idea_specs,
        )
        status_payload["command"] = "status"
        status_payload["next_command"] = _next_command(status_payload, idea_specs=idea_specs)
        _print_program_payload(payload=status_payload, as_json=bool(args.as_json))
        return 0

    if args.program_command == "next":
        status_payload = _program_status_payload(
            umbrella_id=umbrella_id,
            umbrella_spec=umbrella_spec,
            document=document,
            idea_specs=idea_specs,
        )
        payload = {
            "command": "next",
            "umbrella_id": umbrella_id,
            "next_command": _next_command(status_payload, idea_specs=idea_specs),
        }
        _print_program_payload(payload=payload, as_json=bool(args.as_json))
        return 0

    mutable_document = copy.deepcopy(document)
    if bool(args.sync_children):
        _sync_missing_children(document=mutable_document, umbrella_spec=umbrella_spec, idea_specs=idea_specs)
    activate_wave = str(args.activate_wave or "").strip()
    if activate_wave:
        found = False
        for wave in mutable_document.get("waves", []):
            if not isinstance(wave, dict):
                continue
            wave_id = str(wave.get("wave_id", "")).strip()
            if not wave_id:
                continue
            if wave_id == activate_wave:
                wave["status"] = "active"
                found = True
            elif str(wave.get("status", "")).strip() == "active":
                wave["status"] = "planned"
        if not found:
            raise ValueError(f"unknown wave `{activate_wave}`")
    for attribute, status_value in (
        ("complete_wave", "complete"),
        ("block_wave", "blocked"),
        ("plan_wave", "planned"),
    ):
        for wave_id in getattr(args, attribute, []):
            token = str(wave_id or "").strip()
            updated = False
            for wave in mutable_document.get("waves", []):
                if isinstance(wave, dict) and str(wave.get("wave_id", "")).strip() == token:
                    wave["status"] = status_value
                    updated = True
            if not updated:
                raise ValueError(f"unknown wave `{token}`")
    mutable_document["waves"] = _sorted_waves(mutable_document)
    governance = program_wave_execution_governance.program_governance_decision(
        repo_root=repo_root,
        umbrella_spec=umbrella_spec,
        document=mutable_document,
        args=args,
    )
    authoring_execution_policy.enforce_governed_authoring_action(governance)
    payload = {
        "command": "update",
        "umbrella_id": umbrella_id,
        "program": mutable_document,
        "execution_governance": governance.to_dict(),
    }
    if not args.dry_run:
        _update_idea_metadata(umbrella_spec.path, {"execution_model": "umbrella_waves"})
        _write_program_document(repo_root, umbrella_id, mutable_document)
    _print_program_payload(payload=payload, as_json=bool(args.as_json))
    return 0


def wave_main(argv: Sequence[str] | None = None) -> int:
    args = _parse_wave_args(argv)
    repo_root = Path(args.repo_root).resolve()
    idea_specs = _idea_specs(repo_root)
    umbrella_spec = _resolve_umbrella_spec(selector=args.umbrella_id, idea_specs=idea_specs)
    umbrella_id = str(umbrella_spec.metadata.get("idea_id", "")).strip()
    document = _load_program_document(repo_root, umbrella_id)
    mutable_document = copy.deepcopy(document)

    if args.wave_command == "create":
        governance = program_wave_execution_governance.wave_governance_decision(
            repo_root=repo_root,
            umbrella_spec=umbrella_spec,
            document=document,
            args=args,
        )
        authoring_execution_policy.enforce_governed_authoring_action(governance)
        wave_id = str(args.wave_id or "").strip()
        if any(str(row.get("wave_id", "")).strip() == wave_id for row in mutable_document.get("waves", [])):
            raise ValueError(f"wave `{wave_id}` already exists")
        mutable_document.setdefault("waves", []).append(
            {
                "wave_id": wave_id,
                "label": str(args.label or "").strip(),
                "status": str(args.status or "").strip(),
                "summary": str(args.summary or "").strip(),
                "depends_on": [str(item).strip() for item in args.depends_on if str(item).strip()],
                "primary_workstreams": [],
                "carried_workstreams": [],
                "in_band_workstreams": [],
                "gate_refs": [],
            }
        )
    else:
        governance = program_wave_execution_governance.wave_governance_decision(
            repo_root=repo_root,
            umbrella_spec=umbrella_spec,
            document=document,
            args=args,
        )
        authoring_execution_policy.enforce_governed_authoring_action(governance)
        wave = _find_wave(mutable_document, args.wave_id)
        if args.wave_command == "update":
            if args.label is not None:
                wave["label"] = str(args.label or "").strip()
            if args.summary is not None:
                wave["summary"] = str(args.summary or "").strip()
            if args.status is not None:
                wave["status"] = str(args.status or "").strip()
            if bool(args.clear_depends_on):
                wave["depends_on"] = []
            elif args.depends_on:
                wave["depends_on"] = [str(item).strip() for item in args.depends_on if str(item).strip()]
        elif args.wave_command == "assign":
            workstream_id = str(args.workstream_id or "").strip().upper()
            workstream_spec = _resolve_workstream_spec(selector=workstream_id, idea_specs=idea_specs)
            _ensure_child_of_umbrella(umbrella_id=umbrella_id, workstream_spec=workstream_spec)
            for field_name in _ROLE_TO_FIELD.values():
                existing = [str(item).strip() for item in wave.get(field_name, []) if str(item).strip()]
                if workstream_id in existing:
                    existing = [item for item in existing if item != workstream_id]
                wave[field_name] = existing
            target_field = _ROLE_TO_FIELD[str(args.role or "").strip()]
            wave[target_field] = [*wave.get(target_field, []), workstream_id]
        elif args.wave_command == "unassign":
            workstream_id = str(args.workstream_id or "").strip().upper()
            for field_name in _ROLE_TO_FIELD.values():
                wave[field_name] = [item for item in wave.get(field_name, []) if str(item).strip() != workstream_id]
            wave["gate_refs"] = [
                row
                for row in wave.get("gate_refs", [])
                if not isinstance(row, Mapping) or str(row.get("workstream_id", "")).strip() != workstream_id
            ]
        elif args.wave_command == "gate-add":
            workstream_id = str(args.workstream_id or "").strip().upper()
            members = _program_member_ids({"waves": [wave]})
            if workstream_id not in members:
                raise ValueError(f"wave `{args.wave_id}` does not include workstream `{workstream_id}`")
            spec = _resolve_workstream_spec(selector=workstream_id, idea_specs=idea_specs)
            plan_path = str(args.plan_path or "").strip() or str(spec.metadata.get("promoted_to_plan", "")).strip()
            if not plan_path:
                raise ValueError(f"`{workstream_id}` has no bound plan to use as a gate ref")
            label = str(args.label or "").strip() or f"{str(spec.metadata.get('title', '')).strip() or workstream_id} gate"
            gate_refs = [dict(row) for row in wave.get("gate_refs", []) if isinstance(row, Mapping)]
            gate_refs = [row for row in gate_refs if str(row.get("workstream_id", "")).strip() != workstream_id]
            gate_refs.append({"workstream_id": workstream_id, "plan_path": plan_path, "label": label})
            wave["gate_refs"] = gate_refs
        elif args.wave_command == "gate-remove":
            workstream_id = str(args.workstream_id or "").strip().upper()
            wave["gate_refs"] = [
                row
                for row in wave.get("gate_refs", [])
                if not isinstance(row, Mapping) or str(row.get("workstream_id", "")).strip() != workstream_id
            ]
        elif args.wave_command == "status":
            payload = {"command": "status", "umbrella_id": umbrella_id, "wave": wave}
            _print_wave_payload(payload=payload, as_json=bool(args.as_json))
            return 0
        _replace_wave(mutable_document, wave)

    payload = {"command": args.wave_command, "umbrella_id": umbrella_id}
    if args.wave_command != "status":
        target_wave = _find_wave(mutable_document, args.wave_id)
        payload["wave"] = target_wave
        payload["execution_governance"] = governance.to_dict()
        if not args.dry_run:
            _write_program_document(repo_root, umbrella_id, mutable_document)
        _print_wave_payload(payload=payload, as_json=bool(args.as_json))
    return 0


def run_program(argv: Sequence[str] | None = None) -> int:
    try:
        return program_main(argv)
    except ValueError as exc:
        print(str(exc))
        return 2


def run_wave(argv: Sequence[str] | None = None) -> int:
    try:
        return wave_main(argv)
    except ValueError as exc:
        print(str(exc))
        return 2
