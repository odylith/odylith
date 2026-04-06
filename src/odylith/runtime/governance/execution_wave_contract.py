"""Shared umbrella-owned execution-wave contract helpers.

This module centralizes parsing and validation for portfolio execution waves so
backlog validation and traceability generation consume one canonical contract.

Invariants:
- wave metadata is opt-in and owned by umbrella workstreams only;
- generic workstream topology stays canonical for repo-wide relationships;
- execution-wave program files live under a deterministic source path;
- gate refs are declared integrity links, not live checkbox state evaluation.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

EXECUTION_MODEL_FIELD = "execution_model"
EXECUTION_MODEL_STANDARD = "standard"
EXECUTION_MODEL_UMBRELLA_WAVES = "umbrella_waves"
VALID_EXECUTION_MODELS: set[str] = {
    EXECUTION_MODEL_STANDARD,
    EXECUTION_MODEL_UMBRELLA_WAVES,
}
VALID_WAVE_STATUSES: set[str] = {"planned", "active", "complete", "blocked"}
PROGRAMS_DIR = Path("odylith/radar/source/programs")

_IDEA_ID_RE = re.compile(r"^B-\d{3,}$")
_WAVE_ID_RE = re.compile(r"^W[1-9]\d*$")


class IdeaSpecLike(Protocol):
    path: Path
    metadata: Mapping[str, str]


@dataclass(frozen=True)
class ExecutionWaveGateRef:
    workstream_id: str
    plan_path: str
    label: str

    def to_dict(self) -> dict[str, str]:
        return {
            "workstream_id": self.workstream_id,
            "plan_path": self.plan_path,
            "label": self.label,
        }


@dataclass(frozen=True)
class ExecutionWave:
    wave_id: str
    label: str
    status: str
    summary: str
    depends_on: tuple[str, ...]
    primary_workstreams: tuple[str, ...]
    carried_workstreams: tuple[str, ...]
    in_band_workstreams: tuple[str, ...]
    gate_refs: tuple[ExecutionWaveGateRef, ...]

    def all_workstreams(self) -> tuple[str, ...]:
        ordered = [
            *self.primary_workstreams,
            *self.carried_workstreams,
            *self.in_band_workstreams,
        ]
        deduped: list[str] = []
        seen: set[str] = set()
        for workstream_id in ordered:
            if workstream_id in seen:
                continue
            seen.add(workstream_id)
            deduped.append(workstream_id)
        return tuple(deduped)

    def to_dict(self) -> dict[str, Any]:
        return {
            "wave_id": self.wave_id,
            "label": self.label,
            "status": self.status,
            "summary": self.summary,
            "depends_on": list(self.depends_on),
            "primary_workstreams": list(self.primary_workstreams),
            "carried_workstreams": list(self.carried_workstreams),
            "in_band_workstreams": list(self.in_band_workstreams),
            "gate_refs": [gate.to_dict() for gate in self.gate_refs],
        }


@dataclass(frozen=True)
class ExecutionProgram:
    umbrella_id: str
    version: str
    source_file: str
    waves: tuple[ExecutionWave, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "umbrella_id": self.umbrella_id,
            "version": self.version,
            "source_file": self.source_file,
            "waves": [wave.to_dict() for wave in self.waves],
        }


def execution_model_for_metadata(metadata: Mapping[str, str]) -> str:
    token = str(metadata.get(EXECUTION_MODEL_FIELD, EXECUTION_MODEL_STANDARD)).strip().lower()
    return token or EXECUTION_MODEL_STANDARD


def program_relative_path(umbrella_id: str) -> str:
    return PROGRAMS_DIR.joinpath(f"{umbrella_id}.execution-waves.v1.json").as_posix()


def program_path(*, repo_root: Path, umbrella_id: str) -> Path:
    return (repo_root / program_relative_path(umbrella_id)).resolve()


def _as_repo_path(*, repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _normalize_repo_path(*, repo_root: Path, token: str) -> str:
    raw = str(token or "").strip()
    if not raw:
        return ""
    path = Path(raw)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            return ""
    return path.as_posix().lstrip("./")


def _wave_sort_key(wave_id: str) -> tuple[int, str]:
    match = _WAVE_ID_RE.fullmatch(str(wave_id or "").strip())
    if match is None:
        return (10_000, str(wave_id or ""))
    return (int(str(wave_id).strip()[1:]), str(wave_id).strip())


def _dedupe_ids(values: Sequence[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _validate_wave_dependency_cycles(*, waves: Sequence[ExecutionWave], source_file: str) -> list[str]:
    errors: list[str] = []
    edges = {wave.wave_id: set(wave.depends_on) for wave in waves}
    visiting: set[str] = set()
    visited: set[str] = set()

    def _visit(node: str, stack: list[str]) -> None:
        if node in visited:
            return
        if node in visiting:
            cycle = " -> ".join([*stack, node])
            errors.append(f"{source_file}: execution wave dependency cycle detected `{cycle}`")
            return
        visiting.add(node)
        stack.append(node)
        for nxt in sorted(edges.get(node, set()), key=_wave_sort_key):
            _visit(nxt, stack)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for wave in sorted(waves, key=lambda row: _wave_sort_key(row.wave_id)):
        _visit(wave.wave_id, [])
    return errors


def _load_program(
    *,
    path: Path,
    repo_root: Path,
    umbrella_id: str,
    umbrella_spec: IdeaSpecLike,
    idea_specs: Mapping[str, IdeaSpecLike],
) -> tuple[ExecutionProgram | None, list[str]]:
    source_file = _as_repo_path(repo_root=repo_root, path=path)
    errors: list[str] = []
    if not path.is_file():
        return None, [f"{umbrella_spec.path}: missing execution wave program file `{source_file}`"]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"{source_file}: invalid json ({exc})"]

    if not isinstance(payload, dict):
        return None, [f"{source_file}: top-level payload must be an object"]

    declared_umbrella_id = str(payload.get("umbrella_id", "")).strip()
    if declared_umbrella_id != umbrella_id:
        errors.append(
            f"{source_file}: `umbrella_id` must be `{umbrella_id}`, got `{declared_umbrella_id or '<empty>'}`"
        )

    version = str(payload.get("version", "")).strip()
    if version != "v1":
        errors.append(f"{source_file}: `version` must be `v1`, got `{version or '<empty>'}`")

    raw_waves = payload.get("waves")
    if not isinstance(raw_waves, list) or not raw_waves:
        errors.append(f"{source_file}: `waves` must be a non-empty list")
        return None, errors

    waves: list[ExecutionWave] = []
    seen_wave_ids: set[str] = set()
    for idx, raw_wave in enumerate(raw_waves, start=1):
        if not isinstance(raw_wave, dict):
            errors.append(f"{source_file}: wave entry #{idx} must be an object")
            continue

        wave_id = str(raw_wave.get("wave_id", "")).strip()
        label = str(raw_wave.get("label", "")).strip()
        status = str(raw_wave.get("status", "")).strip().lower()
        summary = str(raw_wave.get("summary", "")).strip()
        depends_on = _dedupe_ids(raw_wave.get("depends_on", []) if isinstance(raw_wave.get("depends_on"), list) else [])
        primary = _dedupe_ids(
            raw_wave.get("primary_workstreams", []) if isinstance(raw_wave.get("primary_workstreams"), list) else []
        )
        carried = _dedupe_ids(
            raw_wave.get("carried_workstreams", []) if isinstance(raw_wave.get("carried_workstreams"), list) else []
        )
        in_band = _dedupe_ids(
            raw_wave.get("in_band_workstreams", []) if isinstance(raw_wave.get("in_band_workstreams"), list) else []
        )
        raw_gate_refs = raw_wave.get("gate_refs", [])

        if not _WAVE_ID_RE.fullmatch(wave_id):
            errors.append(f"{source_file}: wave entry #{idx} has invalid `wave_id` `{wave_id or '<empty>'}`")
        elif wave_id in seen_wave_ids:
            errors.append(f"{source_file}: duplicate `wave_id` `{wave_id}`")
        else:
            seen_wave_ids.add(wave_id)

        if not label:
            errors.append(f"{source_file}: wave `{wave_id or f'#{idx}'}` missing `label`")
        if status not in VALID_WAVE_STATUSES:
            errors.append(
                f"{source_file}: wave `{wave_id or f'#{idx}'}` invalid `status` `{status or '<empty>'}`"
            )
        if not summary:
            errors.append(f"{source_file}: wave `{wave_id or f'#{idx}'}` missing `summary`")

        role_members: dict[str, str] = {}
        for role_name, values in (
            ("primary", primary),
            ("carried", carried),
            ("in_band", in_band),
        ):
            for workstream_id in values:
                if not _IDEA_ID_RE.fullmatch(workstream_id):
                    errors.append(
                        f"{source_file}: wave `{wave_id or f'#{idx}'}` {role_name} workstream "
                        f"`{workstream_id}` is not a valid workstream id"
                    )
                    continue
                spec = idea_specs.get(workstream_id)
                if spec is None:
                    errors.append(
                        f"{source_file}: wave `{wave_id or f'#{idx}'}` references unknown workstream `{workstream_id}`"
                    )
                    continue
                if workstream_id == umbrella_id:
                    errors.append(
                        f"{source_file}: wave `{wave_id}` must not list umbrella `{umbrella_id}` as a member"
                    )
                parent = str(spec.metadata.get("workstream_parent", "")).strip()
                if parent != umbrella_id:
                    errors.append(
                        f"{source_file}: wave `{wave_id}` member `{workstream_id}` must be a child of `{umbrella_id}`, "
                        f"got parent `{parent or '<empty>'}`"
                    )
                current_role = role_members.get(workstream_id)
                if current_role is not None:
                    errors.append(
                        f"{source_file}: wave `{wave_id}` assigns workstream `{workstream_id}` to both "
                        f"`{current_role}` and `{role_name}` roles"
                    )
                else:
                    role_members[workstream_id] = role_name

        if not role_members:
            errors.append(f"{source_file}: wave `{wave_id or f'#{idx}'}` must reference at least one workstream")

        gate_refs: list[ExecutionWaveGateRef] = []
        if not isinstance(raw_gate_refs, list):
            errors.append(f"{source_file}: wave `{wave_id or f'#{idx}'}` `gate_refs` must be a list")
            raw_gate_refs = []
        for gate_idx, raw_gate in enumerate(raw_gate_refs, start=1):
            if not isinstance(raw_gate, dict):
                errors.append(f"{source_file}: wave `{wave_id}` gate ref #{gate_idx} must be an object")
                continue
            workstream_id = str(raw_gate.get("workstream_id", "")).strip()
            plan_path = _normalize_repo_path(repo_root=repo_root, token=str(raw_gate.get("plan_path", "")).strip())
            label_text = str(raw_gate.get("label", "")).strip()
            if not _IDEA_ID_RE.fullmatch(workstream_id):
                errors.append(
                    f"{source_file}: wave `{wave_id}` gate ref #{gate_idx} has invalid `workstream_id` "
                    f"`{workstream_id or '<empty>'}`"
                )
                continue
            if workstream_id not in role_members:
                errors.append(
                    f"{source_file}: wave `{wave_id}` gate ref workstream `{workstream_id}` is not a member of that wave"
                )
            if not plan_path:
                errors.append(f"{source_file}: wave `{wave_id}` gate ref `{workstream_id}` missing `plan_path`")
            if not label_text:
                errors.append(f"{source_file}: wave `{wave_id}` gate ref `{workstream_id}` missing `label`")
            spec = idea_specs.get(workstream_id)
            expected_plan = (
                _normalize_repo_path(
                    repo_root=repo_root,
                    token=str(spec.metadata.get("promoted_to_plan", "")).strip(),
                )
                if spec is not None
                else ""
            )
            if expected_plan and plan_path and plan_path != expected_plan:
                errors.append(
                    f"{source_file}: wave `{wave_id}` gate ref `{workstream_id}` points to `{plan_path}` "
                    f"but bound plan is `{expected_plan}`"
                )
            gate_refs.append(
                ExecutionWaveGateRef(
                    workstream_id=workstream_id,
                    plan_path=plan_path,
                    label=label_text,
                )
            )

        waves.append(
            ExecutionWave(
                wave_id=wave_id,
                label=label,
                status=status,
                summary=summary,
                depends_on=tuple(depends_on),
                primary_workstreams=tuple(primary),
                carried_workstreams=tuple(carried),
                in_band_workstreams=tuple(in_band),
                gate_refs=tuple(gate_refs),
            )
        )

    wave_ids = {wave.wave_id for wave in waves}
    for wave in waves:
        for dep in wave.depends_on:
            if dep == wave.wave_id:
                errors.append(f"{source_file}: wave `{wave.wave_id}` must not depend on itself")
            elif dep not in wave_ids:
                errors.append(
                    f"{source_file}: wave `{wave.wave_id}` depends on unknown wave `{dep}`"
                )

    errors.extend(_validate_wave_dependency_cycles(waves=waves, source_file=source_file))
    if errors:
        return None, errors
    waves_sorted = tuple(sorted(waves, key=lambda row: _wave_sort_key(row.wave_id)))
    return (
        ExecutionProgram(
            umbrella_id=umbrella_id,
            version=version,
            source_file=source_file,
            waves=waves_sorted,
        ),
        [],
    )


def collect_execution_programs(
    *,
    repo_root: Path,
    idea_specs: Mapping[str, IdeaSpecLike],
) -> tuple[list[ExecutionProgram], list[str]]:
    errors: list[str] = []
    programs: list[ExecutionProgram] = []
    enabled_umbrellas: dict[str, IdeaSpecLike] = {}
    for idea_id, spec in sorted(idea_specs.items()):
        execution_model = execution_model_for_metadata(spec.metadata)
        if execution_model not in VALID_EXECUTION_MODELS:
            errors.append(
                f"{spec.path}: invalid `{EXECUTION_MODEL_FIELD}` `{execution_model}`; "
                f"expected one of {sorted(VALID_EXECUTION_MODELS)}"
            )
            continue
        if execution_model != EXECUTION_MODEL_UMBRELLA_WAVES:
            continue
        workstream_type = str(spec.metadata.get("workstream_type", "")).strip().lower()
        if workstream_type != "umbrella":
            errors.append(
                f"{spec.path}: `{EXECUTION_MODEL_FIELD}={EXECUTION_MODEL_UMBRELLA_WAVES}` "
                "is only valid for umbrella workstreams"
            )
            continue
        enabled_umbrellas[idea_id] = spec

    expected_paths: set[str] = set()
    for umbrella_id, umbrella_spec in enabled_umbrellas.items():
        target = program_path(repo_root=repo_root, umbrella_id=umbrella_id)
        expected_paths.add(_as_repo_path(repo_root=repo_root, path=target))
        program, program_errors = _load_program(
            path=target,
            repo_root=repo_root,
            umbrella_id=umbrella_id,
            umbrella_spec=umbrella_spec,
            idea_specs=idea_specs,
        )
        errors.extend(program_errors)
        if program is not None:
            programs.append(program)

    programs_dir = (repo_root / PROGRAMS_DIR).resolve()
    if programs_dir.is_dir():
        for path in sorted(programs_dir.glob("*.execution-waves.v1.json")):
            rel = _as_repo_path(repo_root=repo_root, path=path)
            if rel not in expected_paths:
                errors.append(
                    f"{rel}: no umbrella idea currently opts into `{EXECUTION_MODEL_UMBRELLA_WAVES}` for this file"
                )

    return sorted(programs, key=lambda row: row.umbrella_id), errors


def derive_workstream_wave_refs(
    programs: Sequence[ExecutionProgram],
) -> dict[str, list[dict[str, str]]]:
    refs: dict[str, list[dict[str, str]]] = {}
    for program in sorted(programs, key=lambda row: row.umbrella_id):
        for wave in sorted(program.waves, key=lambda row: _wave_sort_key(row.wave_id)):
            for role, values in (
                ("primary", wave.primary_workstreams),
                ("carried", wave.carried_workstreams),
                ("in_band", wave.in_band_workstreams),
            ):
                for workstream_id in values:
                    refs.setdefault(workstream_id, []).append(
                        {
                            "umbrella_id": program.umbrella_id,
                            "wave_id": wave.wave_id,
                            "wave_label": wave.label,
                            "wave_status": wave.status,
                            "role": role,
                            "source_file": program.source_file,
                        }
                    )
    return refs
