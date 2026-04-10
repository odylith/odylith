from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from odylith.runtime import release_notes

RELEASES_DIR = Path("odylith/radar/source/releases")
RELEASES_REGISTRY_PATH = RELEASES_DIR / "releases.v1.json"
RELEASE_ASSIGNMENT_EVENT_LOG_PATH = RELEASES_DIR / "release-assignment-events.v1.jsonl"

_VALID_RELEASE_STATUSES = frozenset({"planning", "active", "shipped", "closed"})
_TERMINAL_RELEASE_STATUSES = frozenset({"shipped", "closed"})
_VALID_EVENT_ACTIONS = frozenset({"add", "remove", "move"})
_WORKSTREAM_ID_RE = re.compile(r"^B-\d{3,}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_EMPTY_RELEASE_REGISTRY = {
    "version": "v1",
    "updated_utc": "",
    "aliases": {},
    "releases": [],
}


class ReleaseSelectorError(ValueError):
    def __init__(self, selector: str, matches: Sequence[str], *, message: str = "") -> None:
        self.selector = str(selector or "").strip()
        self.matches = tuple(str(item).strip() for item in matches if str(item).strip())
        if message:
            detail = message
        elif self.matches:
            detail = f"selector `{self.selector}` is ambiguous: {', '.join(self.matches)}"
        else:
            detail = f"selector `{self.selector}` did not match any release"
        super().__init__(detail)


@dataclass(frozen=True)
class ReleaseRecord:
    release_id: str
    status: str
    version: str
    tag: str
    name: str
    inherited_name: str
    notes: str
    created_utc: str
    shipped_utc: str
    closed_utc: str
    source_path: Path

    @property
    def terminal(self) -> bool:
        return self.status in _TERMINAL_RELEASE_STATUSES

    @property
    def effective_name(self) -> str:
        return self.name or self.version or self.tag or self.release_id

    @property
    def display_label(self) -> str:
        return self.effective_name

    def as_dict(
        self,
        *,
        aliases: Sequence[str] = (),
        active_workstreams: Sequence[str] = (),
        completed_workstreams: Sequence[str] = (),
    ) -> dict[str, Any]:
        return {
            "release_id": self.release_id,
            "status": self.status,
            "version": self.version,
            "tag": self.tag,
            "name": self.name,
            "inherited_name": self.inherited_name,
            "effective_name": self.effective_name,
            "display_label": self.display_label,
            "notes": self.notes,
            "created_utc": self.created_utc,
            "shipped_utc": self.shipped_utc,
            "closed_utc": self.closed_utc,
            "aliases": [str(token).strip() for token in aliases if str(token).strip()],
            "active_workstreams": [str(token).strip() for token in active_workstreams if str(token).strip()],
            "completed_workstreams": [str(token).strip() for token in completed_workstreams if str(token).strip()],
            "source_path": str(self.source_path),
            "terminal": self.terminal,
        }


@dataclass(frozen=True)
class ReleaseAssignmentEvent:
    action: str
    workstream_id: str
    release_id: str
    from_release_id: str
    to_release_id: str
    recorded_at: str
    note: str
    source_path: Path
    line_number: int

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "action": self.action,
            "workstream_id": self.workstream_id,
            "recorded_at": self.recorded_at,
            "note": self.note,
        }
        if self.release_id:
            payload["release_id"] = self.release_id
        if self.from_release_id:
            payload["from_release_id"] = self.from_release_id
        if self.to_release_id:
            payload["to_release_id"] = self.to_release_id
        return payload


@dataclass(frozen=True)
class ReleaseHistoryEntry:
    action: str
    workstream_id: str
    release_id: str
    from_release_id: str
    to_release_id: str
    recorded_at: str
    note: str

    def as_dict(self) -> dict[str, str]:
        return {
            "action": self.action,
            "workstream_id": self.workstream_id,
            "release_id": self.release_id,
            "from_release_id": self.from_release_id,
            "to_release_id": self.to_release_id,
            "recorded_at": self.recorded_at,
            "note": self.note,
        }


@dataclass(frozen=True)
class ReleasePlanningState:
    releases_by_id: dict[str, ReleaseRecord]
    alias_to_release_id: dict[str, str]
    selector_to_release_ids: dict[str, tuple[str, ...]]
    active_release_by_workstream: dict[str, str]
    history_by_workstream: dict[str, tuple[ReleaseHistoryEntry, ...]]
    workstream_status_by_id: dict[str, str]
    registry_path: Path
    event_log_path: Path

    def aliases_for_release(self, release_id: str) -> list[str]:
        token = str(release_id or "").strip()
        return sorted(
            alias
            for alias, owner in self.alias_to_release_id.items()
            if str(owner).strip() == token
        )

    def release_for_selector(self, selector: str) -> ReleaseRecord:
        return resolve_release_selector(self, selector)


def _resolve_path(*, repo_root: Path, token: Path | str) -> Path:
    path = Path(str(token or "").strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def releases_registry_path(*, repo_root: Path) -> Path:
    return _resolve_path(repo_root=repo_root, token=RELEASES_REGISTRY_PATH)


def release_assignment_event_log_path(*, repo_root: Path) -> Path:
    return _resolve_path(repo_root=repo_root, token=RELEASE_ASSIGNMENT_EVENT_LOG_PATH)


def default_registry_document() -> dict[str, Any]:
    return json.loads(json.dumps(_EMPTY_RELEASE_REGISTRY))


def load_registry_document(*, path: Path) -> tuple[dict[str, Any], list[str]]:
    target = Path(path).resolve()
    if not target.is_file():
        return default_registry_document(), []
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return default_registry_document(), [f"{target}: invalid release registry json: {exc}"]
    if not isinstance(payload, Mapping):
        return default_registry_document(), [f"{target}: release registry root must be an object"]
    document = default_registry_document()
    document.update(
        {
            "version": str(payload.get("version", "v1")).strip() or "v1",
            "updated_utc": str(payload.get("updated_utc", "")).strip(),
            "aliases": dict(payload.get("aliases", {})) if isinstance(payload.get("aliases"), Mapping) else {},
            "releases": list(payload.get("releases", [])) if isinstance(payload.get("releases"), list) else [],
        }
    )
    return document, []


def load_assignment_event_documents(*, path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    target = Path(path).resolve()
    if not target.is_file():
        return [], []
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_number, raw in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
        line = str(raw or "").strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{target}:{line_number}: invalid release assignment event json: {exc}")
            continue
        if not isinstance(payload, Mapping):
            errors.append(f"{target}:{line_number}: release assignment event must be an object")
            continue
        row = dict(payload)
        row["_line_number"] = line_number
        rows.append(row)
    return rows, errors


def utc_now_iso() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_release_selector(value: str) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    lower = token.casefold()
    if lower in {"current release", "release current"}:
        return "current"
    if lower in {"next release", "release next"}:
        return "next"
    if lower.startswith("release:"):
        token = token.split(":", 1)[1].strip()
    return token


def canonical_alias_token(value: str) -> str:
    token = str(value or "").strip().casefold()
    return re.sub(r"\s+", "-", token)


def _valid_date_token(value: str) -> bool:
    token = str(value or "").strip()
    if not token:
        return True
    if not _DATE_RE.fullmatch(token):
        return False
    try:
        dt.date.fromisoformat(token)
    except ValueError:
        return False
    return True


def _valid_iso_ts_token(value: str) -> bool:
    token = str(value or "").strip()
    if not token:
        return False
    if not _ISO_TS_RE.fullmatch(token):
        return False
    try:
        dt.datetime.fromisoformat(token.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _release_note_title(*, repo_root: Path, version: str) -> str:
    note = release_notes.load_release_notes_source(repo_root=repo_root, version=version)
    return str(note.title).strip() if note is not None else ""


def _selector_tokens(
    *,
    release: ReleaseRecord,
    aliases: Sequence[str],
) -> dict[str, tuple[str, ...]]:
    return {
        "release_id": tuple(token for token in [release.release_id] if token),
        "alias": tuple(token for token in aliases if token),
        "version": tuple(token for token in [release.version] if token),
        "tag": tuple(token for token in [release.tag] if token),
        "name": tuple(token for token in [release.name] if token),
    }


def _canonical_selector_key(value: str) -> str:
    return str(value or "").strip().casefold()


def validate_release_planning_payload(
    *,
    repo_root: Path,
    idea_specs: Mapping[str, Any] | None,
    registry_document: Mapping[str, Any] | None,
    event_documents: Sequence[Mapping[str, Any]] | None,
    registry_path: Path | None = None,
    event_log_path: Path | None = None,
) -> tuple[ReleasePlanningState, list[str]]:
    root = Path(repo_root).resolve()
    registry_file = registry_path if registry_path is not None else releases_registry_path(repo_root=root)
    event_file = event_log_path if event_log_path is not None else release_assignment_event_log_path(repo_root=root)
    errors: list[str] = []

    registry = dict(registry_document or {})
    aliases_payload = dict(registry.get("aliases", {})) if isinstance(registry.get("aliases"), Mapping) else {}
    release_rows = list(registry.get("releases", [])) if isinstance(registry.get("releases"), list) else []
    updated_utc = str(registry.get("updated_utc", "")).strip()
    if updated_utc and not _valid_date_token(updated_utc):
        errors.append(f"{registry_file}: `updated_utc` must use YYYY-MM-DD when present")

    releases_by_id: dict[str, ReleaseRecord] = {}
    for index, row in enumerate(release_rows, start=1):
        if not isinstance(row, Mapping):
            errors.append(f"{registry_file}: release row {index} must be an object")
            continue
        release_id = str(row.get("release_id", "")).strip()
        if not release_id:
            errors.append(f"{registry_file}: release row {index} missing `release_id`")
            continue
        if release_id in releases_by_id:
            errors.append(f"{registry_file}: duplicate release_id `{release_id}`")
            continue
        status = str(row.get("status", "")).strip().lower() or "planning"
        if status not in _VALID_RELEASE_STATUSES:
            errors.append(
                f"{registry_file}: `{release_id}` status must be one of {sorted(_VALID_RELEASE_STATUSES)}, got `{status}`"
            )
            status = "planning"
        version = str(row.get("version", "")).strip()
        tag = str(row.get("tag", "")).strip()
        name = str(row.get("name", "")).strip()
        created_utc = str(row.get("created_utc", "")).strip()
        shipped_utc = str(row.get("shipped_utc", "")).strip()
        closed_utc = str(row.get("closed_utc", "")).strip()
        notes = str(row.get("notes", "")).strip()
        for field_name, token in (
            ("created_utc", created_utc),
            ("shipped_utc", shipped_utc),
            ("closed_utc", closed_utc),
        ):
            if token and not _valid_date_token(token):
                errors.append(f"{registry_file}: `{release_id}` `{field_name}` must use YYYY-MM-DD")
        inherited_name = _release_note_title(repo_root=root, version=version) if version else ""
        releases_by_id[release_id] = ReleaseRecord(
            release_id=release_id,
            status=status,
            version=version,
            tag=tag,
            name=name,
            inherited_name=inherited_name,
            notes=notes,
            created_utc=created_utc,
            shipped_utc=shipped_utc,
            closed_utc=closed_utc,
            source_path=Path(registry_file).resolve(),
        )

    alias_to_release_id: dict[str, str] = {}
    for raw_alias, raw_release_id in aliases_payload.items():
        alias = canonical_alias_token(str(raw_alias or ""))
        release_id = str(raw_release_id or "").strip()
        if not alias:
            errors.append(f"{registry_file}: alias keys must be non-empty")
            continue
        if release_id not in releases_by_id:
            errors.append(f"{registry_file}: alias `{alias}` points to unknown release `{release_id}`")
            continue
        owner = releases_by_id[release_id]
        if alias in {"current", "next"} and owner.status in _TERMINAL_RELEASE_STATUSES:
            errors.append(
                f"{registry_file}: alias `{alias}` cannot point to terminal release `{release_id}` with status `{owner.status}`"
            )
        alias_to_release_id[alias] = release_id

    selector_map: dict[str, set[str]] = {}
    for release_id, record in releases_by_id.items():
        tokens = _selector_tokens(
            release=record,
            aliases=[alias for alias, owner in alias_to_release_id.items() if owner == release_id],
        )
        for _kind, values in tokens.items():
            for value in values:
                key = _canonical_selector_key(value)
                if not key:
                    continue
                selector_map.setdefault(key, set()).add(release_id)
    for selector_key, release_ids in sorted(selector_map.items()):
        if len(release_ids) > 1:
            errors.append(
                f"{registry_file}: selector `{selector_key}` is ambiguous across releases {sorted(release_ids)}"
            )

    events: list[ReleaseAssignmentEvent] = []
    for row in event_documents or []:
        if not isinstance(row, Mapping):
            continue
        action = str(row.get("action", "")).strip().lower()
        workstream_id = str(row.get("workstream_id", "")).strip().upper()
        release_id = str(row.get("release_id", "")).strip()
        from_release_id = str(row.get("from_release_id", "")).strip()
        to_release_id = str(row.get("to_release_id", "")).strip()
        recorded_at = str(row.get("recorded_at", "")).strip()
        note = str(row.get("note", "")).strip()
        line_number = int(row.get("_line_number", 0) or 0)
        if action not in _VALID_EVENT_ACTIONS:
            errors.append(f"{event_file}:{line_number}: action must be one of {sorted(_VALID_EVENT_ACTIONS)}")
            continue
        if not _WORKSTREAM_ID_RE.fullmatch(workstream_id):
            errors.append(f"{event_file}:{line_number}: invalid workstream id `{workstream_id}`")
            continue
        if idea_specs is not None and workstream_id not in idea_specs:
            errors.append(f"{event_file}:{line_number}: unknown workstream `{workstream_id}`")
        if not _valid_iso_ts_token(recorded_at):
            errors.append(f"{event_file}:{line_number}: `recorded_at` must use UTC ISO format `YYYY-MM-DDTHH:MM:SSZ`")
        if action == "add":
            if not release_id:
                errors.append(f"{event_file}:{line_number}: add event requires `release_id`")
            elif release_id not in releases_by_id:
                errors.append(f"{event_file}:{line_number}: add event targets unknown release `{release_id}`")
        elif action == "remove":
            if not release_id:
                errors.append(f"{event_file}:{line_number}: remove event requires `release_id`")
            elif release_id not in releases_by_id:
                errors.append(f"{event_file}:{line_number}: remove event targets unknown release `{release_id}`")
        elif action == "move":
            if not from_release_id or not to_release_id:
                errors.append(f"{event_file}:{line_number}: move event requires `from_release_id` and `to_release_id`")
            if from_release_id and from_release_id not in releases_by_id:
                errors.append(f"{event_file}:{line_number}: move event references unknown `from_release_id` `{from_release_id}`")
            if to_release_id and to_release_id not in releases_by_id:
                errors.append(f"{event_file}:{line_number}: move event references unknown `to_release_id` `{to_release_id}`")
            release_id = to_release_id
        events.append(
            ReleaseAssignmentEvent(
                action=action,
                workstream_id=workstream_id,
                release_id=release_id,
                from_release_id=from_release_id,
                to_release_id=to_release_id,
                recorded_at=recorded_at,
                note=note,
                source_path=Path(event_file).resolve(),
                line_number=line_number,
            )
        )

    active_release_by_workstream: dict[str, str] = {}
    history_by_workstream: dict[str, list[ReleaseHistoryEntry]] = {}
    for event in events:
        history_by_workstream.setdefault(event.workstream_id, []).append(
            ReleaseHistoryEntry(
                action=event.action,
                workstream_id=event.workstream_id,
                release_id=event.release_id,
                from_release_id=event.from_release_id,
                to_release_id=event.to_release_id,
                recorded_at=event.recorded_at,
                note=event.note,
            )
        )
        current = active_release_by_workstream.get(event.workstream_id, "")
        if event.action == "add":
            if current:
                errors.append(
                    f"{event.source_path}:{event.line_number}: `{event.workstream_id}` already targets `{current}`; use move instead of add"
                )
                continue
            active_release_by_workstream[event.workstream_id] = event.release_id
            continue
        if event.action == "remove":
            if current != event.release_id:
                errors.append(
                    f"{event.source_path}:{event.line_number}: `{event.workstream_id}` cannot remove `{event.release_id}` because active target is `{current or 'none'}`"
                )
                continue
            active_release_by_workstream.pop(event.workstream_id, None)
            continue
        if event.action == "move":
            if current != event.from_release_id:
                errors.append(
                    f"{event.source_path}:{event.line_number}: `{event.workstream_id}` cannot move from `{event.from_release_id}` because active target is `{current or 'none'}`"
                )
                continue
            if event.to_release_id == event.from_release_id:
                errors.append(
                    f"{event.source_path}:{event.line_number}: `{event.workstream_id}` move target matches source `{event.to_release_id}`"
                )
                continue
            active_release_by_workstream[event.workstream_id] = event.to_release_id

    if idea_specs is not None:
        for workstream_id, release_id in sorted(active_release_by_workstream.items()):
            spec = idea_specs.get(workstream_id)
            if spec is None:
                continue
            status = str(getattr(spec, "status", "")).strip().lower()
            if status in {"finished", "parked", "superseded"}:
                errors.append(
                    f"{event_file}: `{workstream_id}` with status `{status}` cannot target active release `{release_id}`"
                )
            release = releases_by_id.get(release_id)
            if release is None:
                continue
            if release.status in _TERMINAL_RELEASE_STATUSES:
                errors.append(
                    f"{event_file}: `{workstream_id}` cannot target terminal release `{release_id}` with status `{release.status}`"
                )

    state = ReleasePlanningState(
        releases_by_id=dict(releases_by_id),
        alias_to_release_id=dict(alias_to_release_id),
        selector_to_release_ids={
            key: tuple(sorted(value))
            for key, value in selector_map.items()
        },
        active_release_by_workstream=dict(active_release_by_workstream),
        history_by_workstream={
            key: tuple(rows)
            for key, rows in history_by_workstream.items()
        },
        workstream_status_by_id={
            str(workstream_id).strip().upper(): str(getattr(spec, "status", "")).strip().lower()
            for workstream_id, spec in (idea_specs or {}).items()
            if str(workstream_id).strip()
        },
        registry_path=Path(registry_file).resolve(),
        event_log_path=Path(event_file).resolve(),
    )
    return state, errors


def validate_release_planning(
    *,
    repo_root: Path,
    idea_specs: Mapping[str, Any] | None,
) -> tuple[ReleasePlanningState, list[str]]:
    root = Path(repo_root).resolve()
    registry_path = releases_registry_path(repo_root=root)
    event_log_path = release_assignment_event_log_path(repo_root=root)
    registry_document, registry_errors = load_registry_document(path=registry_path)
    event_documents, event_errors = load_assignment_event_documents(path=event_log_path)
    state, errors = validate_release_planning_payload(
        repo_root=root,
        idea_specs=idea_specs,
        registry_document=registry_document,
        event_documents=event_documents,
        registry_path=registry_path,
        event_log_path=event_log_path,
    )
    return state, [*registry_errors, *event_errors, *errors]


def resolve_release_selector(state: ReleasePlanningState, selector: str) -> ReleaseRecord:
    token = normalize_release_selector(selector)
    key = _canonical_selector_key(token)
    if not key:
        raise ReleaseSelectorError(selector, ())
    matches = tuple(sorted(state.selector_to_release_ids.get(key, ())))
    if not matches:
        raise ReleaseSelectorError(selector, ())
    if len(matches) > 1:
        raise ReleaseSelectorError(selector, matches)
    release = state.releases_by_id.get(matches[0])
    if release is None:
        raise ReleaseSelectorError(selector, ())
    return release


def render_registry_document(
    *,
    releases: Sequence[Mapping[str, Any]],
    aliases: Mapping[str, str],
    updated_utc: str,
) -> str:
    payload = {
        "version": "v1",
        "updated_utc": str(updated_utc or "").strip(),
        "aliases": {
            canonical_alias_token(alias): str(release_id or "").strip()
            for alias, release_id in sorted(aliases.items())
            if canonical_alias_token(alias) and str(release_id or "").strip()
        },
        "releases": [
            {
                "release_id": str(row.get("release_id", "")).strip(),
                "status": str(row.get("status", "")).strip() or "planning",
                "version": str(row.get("version", "")).strip(),
                "tag": str(row.get("tag", "")).strip(),
                "name": str(row.get("name", "")).strip(),
                "notes": str(row.get("notes", "")).strip(),
                "created_utc": str(row.get("created_utc", "")).strip(),
                "shipped_utc": str(row.get("shipped_utc", "")).strip(),
                "closed_utc": str(row.get("closed_utc", "")).strip(),
            }
            for row in sorted(
                releases,
                key=lambda item: str(item.get("release_id", "")).strip(),
            )
            if str(row.get("release_id", "")).strip()
        ],
    }
    return json.dumps(payload, indent=2) + "\n"


def render_assignment_event(event: Mapping[str, Any]) -> str:
    payload = {
        key: value
        for key, value in {
            "action": str(event.get("action", "")).strip(),
            "workstream_id": str(event.get("workstream_id", "")).strip(),
            "release_id": str(event.get("release_id", "")).strip(),
            "from_release_id": str(event.get("from_release_id", "")).strip(),
            "to_release_id": str(event.get("to_release_id", "")).strip(),
            "recorded_at": str(event.get("recorded_at", "")).strip(),
            "note": str(event.get("note", "")).strip(),
        }.items()
        if value
    }
    return json.dumps(payload, sort_keys=True) + "\n"


__all__ = [
    "RELEASES_DIR",
    "RELEASES_REGISTRY_PATH",
    "RELEASE_ASSIGNMENT_EVENT_LOG_PATH",
    "ReleaseAssignmentEvent",
    "ReleasePlanningState",
    "ReleaseRecord",
    "ReleaseSelectorError",
    "canonical_alias_token",
    "default_registry_document",
    "load_assignment_event_documents",
    "load_registry_document",
    "normalize_release_selector",
    "release_assignment_event_log_path",
    "releases_registry_path",
    "render_assignment_event",
    "render_registry_document",
    "resolve_release_selector",
    "utc_now_iso",
    "validate_release_planning",
    "validate_release_planning_payload",
]
