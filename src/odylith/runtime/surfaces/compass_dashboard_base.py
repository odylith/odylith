"""Shared Compass renderer constants and low-level data helpers.

This module holds the low-churn parsing, git, backlog, and path helpers used by
Compass runtime generation. The facade in `render_compass_dashboard.py` re-exports
these names to preserve the existing import surface while the implementation is
split into responsibility-aligned modules.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common import repo_path_resolver
from odylith.runtime.governance import component_registry_intelligence as component_registry
from odylith.runtime.governance import plan_progress
from odylith.runtime.context_engine import odylith_context_engine_store
from odylith.runtime.governance import validate_backlog_contract as backlog_contract
from odylith.runtime.governance import workstream_inference as ws_inference
from odylith.runtime.surfaces import surface_path_helpers

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CHECKBOX_RE = re.compile(r"^\s*-\s*\[(?P<mark>[xX ])\]\s+(?P<body>.+?)\s*$")
_HEADER_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$")
_BUG_TABLE_ROW_RE = re.compile(r"^\|.+\|\s*$")
_WORKSTREAM_ID_RE = re.compile(r"^B-\d{3,}$")
_WORKSTREAM_TOKEN_RE = re.compile(r"\b(B-\d{3,})\b", re.IGNORECASE)
_CONVENTIONAL_COMMIT_PREFIX_RE = re.compile(
    r"^(?:feat|fix|chore|refactor|docs|test|perf|ci|build)(?:\([^)]+\))?!?:\s*",
    re.IGNORECASE,
)
_RETIRED_SURFACE_MARKER = "sen" "tinel"
_RETIRED_SURFACE_LABEL = "retired control surface"
_CASEBOOK_BUG_PATH_PREFIX = "odylith/casebook/bugs/"
_UNIT_RUNTIME_TEST_PREFIX = "tests/unit/runtime/"
_ACTIVE_SURFACE_MODULE_STEMS: frozenset[str] = frozenset(
    {
        "compass_standup_brief_batch",
        "compass_standup_brief_maintenance",
        "compass_standup_brief_narrator",
        "compass_standup_brief_substrate",
        "compass_standup_brief_voice_validation",
        "tooling_dashboard_cheatsheet_presenter",
        "tooling_dashboard_release_presenter",
        "tooling_dashboard_shell_presenter",
        "tooling_dashboard_welcome_presenter",
    }
)
_GENERIC_TX_HEADLINE_RE = re.compile(
    r"^(?:"
    r"(?:edited|updated|modified|changed)\s+(?:\d+\s+)?files?"
    r"|execution update"
    r"|transaction(?:\s+update)?"
    r"|recent change"
    r"|code updates?"
    r")$",
    re.IGNORECASE,
)
_PLAN_CHECKLIST_PROGRESS_RE = re.compile(
    r"checklist\s+(?P<done>\d+)\s*/\s*(?P<total>\d+)\s+complete",
    re.IGNORECASE,
)
_PLAN_KICKOFF_RE = re.compile(
    r"\b(?:plan\s+kickoff|kickoff|plan\s+started?|started\s+plan)\b",
    re.IGNORECASE,
)
_BACKLOG_ROW_HEADERS: tuple[str, ...] = (
    "rank",
    "idea_id",
    "title",
    "priority",
    "ordering_score",
    "commercial_value",
    "product_impact",
    "market_value",
    "sizing",
    "complexity",
    "status",
    "link",
)
_PLAN_ROW_HEADERS: tuple[str, ...] = ("Plan", "Status", "Created", "Updated", "Backlog")
_SIZE_SCORE: dict[str, int] = {"XS": 1, "S": 2, "M": 3, "L": 5, "XL": 8}
_COMPLEXITY_SCORE: dict[str, int] = {"Low": 1, "Medium": 2, "High": 3, "VeryHigh": 5}
_SIZE_DAY_BASE: dict[str, int] = {"XS": 3, "S": 5, "M": 8, "L": 12, "XL": 18}
_COMPLEXITY_DAY_DELTA: dict[str, int] = {"Low": 0, "Medium": 2, "High": 4, "VeryHigh": 7}
_HEURISTIC_AI_ACCELERATION_FACTOR = 0.5
_DEFAULT_ACTIVE_WINDOW_MINUTES = 15
_DEFAULT_RECENT_FOCUS_WINDOW_MINUTES = 90
_TIMELINE_EVENT_LOOKBACK_HOURS = 72
_TIMELINE_EVENT_MAX_ROWS = 1200
_TIMELINE_GENERATED_NOISE_MAX_ROWS = 300
_TX_HEADLINE_MAX_CHARS = 180
_COMPASS_TIMEZONE = "America/Los_Angeles"
_COMPASS_TZ = ZoneInfo(_COMPASS_TIMEZONE)


def _resolve(repo_root: Path, value: str) -> Path:
    """Backward-compatible wrapper over the shared surface path resolver."""

    return surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=value)


def _as_href(output_path: Path, target: Path) -> str:
    """Backward-compatible wrapper for legacy Compass helper consumers."""

    return surface_path_helpers.relative_href(output_path=output_path, target=target)


def _as_repo_path(repo_root: Path, target: Path) -> str:
    return repo_path_resolver.display_repo_path(repo_root=repo_root, value=target)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def _load_component_index(
    *,
    repo_root: Path,
) -> Mapping[str, component_registry.ComponentEntry]:
    return _load_component_index_runtime(repo_root=repo_root, runtime_mode="auto")


def _load_component_index_runtime(
    *,
    repo_root: Path,
    runtime_mode: str,
) -> Mapping[str, component_registry.ComponentEntry]:
    try:
        from odylith.runtime.governance import component_registry_intelligence as registry_runtime
        from odylith.runtime.governance import sync_session as governed_sync_session
    except Exception:
        registry_runtime = None
        governed_sync_session = None
    if registry_runtime is not None and governed_sync_session is not None:
        session = governed_sync_session.active_sync_session()
        if session is not None and session.repo_root == Path(repo_root).resolve():
            try:
                report = registry_runtime.build_component_registry_report(repo_root=repo_root)
                if report.components:
                    return report.components
            except Exception:
                pass
    try:
        components = odylith_context_engine_store.load_component_index(
            repo_root=repo_root,
            runtime_mode=runtime_mode,
        )
    except Exception:
        return {}
    return components


def _component_rows_for_workstream(
    *,
    component_index: Mapping[str, component_registry.ComponentEntry],
    workstream_id: str,
) -> list[dict[str, str]]:
    component_ids = component_registry.component_ids_for_workstream(
        components=component_index,
        workstream_id=workstream_id,
    )
    rows: list[dict[str, str]] = []
    for component_id in component_ids:
        row = component_index.get(component_id)
        rows.append(
            {
                "component_id": component_id,
                "name": (row.name if row is not None else "") or component_id,
            }
        )
    return rows


def _parse_markdown_metadata_and_sections(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    metadata: dict[str, str] = {}
    sections: dict[str, list[str]] = {}
    current_section: str | None = None
    in_metadata = True

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        header_match = _HEADER_RE.match(raw_line)
        if header_match:
            in_metadata = False
            current_section = str(header_match.group("title")).strip()
            sections.setdefault(current_section, [])
            continue

        if in_metadata:
            line = raw_line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
            continue

        if current_section is not None:
            sections[current_section].append(raw_line)

    flattened: dict[str, str] = {}
    for key, lines in sections.items():
        merged = " ".join(token.strip() for token in lines if token.strip())
        flattened[key] = merged.strip()
    return metadata, flattened


def _collect_plan_progress(plan_path: Path) -> dict[str, Any]:
    return plan_progress.collect_plan_progress(plan_path)


def _parse_backlog_rows(
    *,
    repo_root: Path,
    index_path: Path,
    runtime_mode: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    def _source_rows() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        snapshot = backlog_contract.load_backlog_index_snapshot(index_path)
        active_rows = backlog_contract.rows_as_mapping(
            section=snapshot.get("active", {}),
            expected_headers=_BACKLOG_ROW_HEADERS,
        )
        execution_rows = backlog_contract.rows_as_mapping(
            section=snapshot.get("execution", {}),
            expected_headers=_BACKLOG_ROW_HEADERS,
        )
        return active_rows, execution_rows

    try:
        from odylith.runtime.governance import sync_session as governed_sync_session
    except Exception:
        governed_sync_session = None
    if governed_sync_session is not None:
        session = governed_sync_session.active_sync_session()
        if session is not None and session.repo_root == Path(repo_root).resolve() and index_path.is_file():
            built = False

            def _builder() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
                nonlocal built
                built = True
                return _source_rows()

            active_rows, execution_rows = session.get_or_compute(
                namespace="compass_backlog_rows",
                key=(
                    f"source:{str(runtime_mode).strip().lower()}\n"
                    f"generation={session.generation}\n"
                    f"index={index_path.resolve()}"
                ),
                builder=_builder,
            )
            session.record_cache_decision(
                category="compass_backlog_rows",
                cache_hit=not built,
                built_from="sync_session_source_truth",
                details={
                    "generation": session.generation,
                    "runtime_mode": str(runtime_mode).strip().lower(),
                    "index_path": str(index_path),
                },
            )
            return (
                [dict(row) for row in active_rows if isinstance(row, Mapping)],
                [dict(row) for row in execution_rows if isinstance(row, Mapping)],
            )
    if str(runtime_mode).strip().lower() != "standalone":
        projection: Mapping[str, Any]
        if governed_sync_session is not None:
            session = governed_sync_session.active_sync_session()
            if session is not None and session.repo_root == Path(repo_root).resolve():
                built = False

                def _builder() -> Mapping[str, Any]:
                    nonlocal built
                    built = True
                    return odylith_context_engine_store.load_backlog_rows(
                        repo_root=repo_root,
                        runtime_mode=runtime_mode,
                    )

                projection = session.get_or_compute(
                    namespace="compass_backlog_rows",
                    key=f"{str(runtime_mode).strip().lower()}\ngeneration={session.generation}",
                    builder=_builder,
                )
                session.record_cache_decision(
                    category="compass_backlog_rows",
                    cache_hit=not built,
                    built_from="sync_session",
                    details={
                        "generation": session.generation,
                        "runtime_mode": str(runtime_mode).strip().lower(),
                    },
                )
            else:
                projection = odylith_context_engine_store.load_backlog_rows(
                    repo_root=repo_root,
                    runtime_mode=runtime_mode,
                )
        else:
            projection = odylith_context_engine_store.load_backlog_rows(
                repo_root=repo_root,
                runtime_mode=runtime_mode,
            )
        return (
            [dict(row) for row in projection.get("active", []) if isinstance(row, Mapping)],
            [dict(row) for row in projection.get("execution", []) if isinstance(row, Mapping)],
        )
    return _source_rows()


def _parse_plan_active_rows(*, repo_root: Path, index_path: Path, runtime_mode: str) -> list[dict[str, str]]:
    if str(runtime_mode).strip().lower() != "standalone":
        return list(
            odylith_context_engine_store.load_plan_rows(
                repo_root=repo_root,
                runtime_mode=runtime_mode,
            ).get("active", [])
        )
    snapshot = backlog_contract.load_plan_index_snapshot(index_path)
    return backlog_contract.rows_as_mapping(
        section=snapshot.get("active", {}),
        expected_headers=_PLAN_ROW_HEADERS,
    )


def _parse_bugs_rows(*, repo_root: Path, index_path: Path, runtime_mode: str) -> list[dict[str, str]]:
    if str(runtime_mode).strip().lower() != "standalone":
        return odylith_context_engine_store.load_bug_rows(
            repo_root=repo_root,
            runtime_mode=runtime_mode,
        )
    lines = index_path.read_text(encoding="utf-8").splitlines()
    table_started = False
    headers: list[str] = []
    rows: list[dict[str, str]] = []

    for raw in lines:
        if not _BUG_TABLE_ROW_RE.match(raw.strip()):
            if table_started and rows:
                break
            continue
        cells = [cell.strip() for cell in raw.strip().split("|")[1:-1]]
        if not cells:
            continue
        if all(re.fullmatch(r"-+", token or "") for token in cells):
            continue
        if not table_started:
            headers = cells
            table_started = True
            continue
        if len(cells) != len(headers):
            continue
        payload = dict(zip(headers, cells, strict=True))
        if "Status" in payload:
            payload["Status"] = odylith_context_engine_store.canonicalize_bug_status(payload["Status"])
        rows.append(payload)

    return rows


def _extract_link_target(markdown_link: str) -> str:
    return backlog_contract._parse_link_target(markdown_link) or ""


def _normalize_repo_token(token: str, *, repo_root: Path | None = None) -> str:
    return ws_inference.normalize_repo_token(token, repo_root=repo_root)


def _safe_iso(ts: dt.datetime) -> str:
    return ts.astimezone(_COMPASS_TZ).isoformat(timespec="seconds")


def _parse_date(token: str) -> dt.date | None:
    raw = str(token or "").strip()
    if not _DATE_RE.fullmatch(raw):
        return None
    try:
        return dt.date.fromisoformat(raw)
    except ValueError:
        return None


def _extract_workstream_tokens_from_text(text: str) -> list[str]:
    tokens = {match.upper() for match in _WORKSTREAM_TOKEN_RE.findall(str(text or ""))}
    return sorted(token for token in tokens if _WORKSTREAM_ID_RE.fullmatch(token))


def _split_workstream_ids(value: object) -> list[str]:
    tokens: list[str] = []
    if isinstance(value, list):
        iterable = [str(item or "").strip() for item in value]
    else:
        iterable = [token.strip() for token in str(value or "").replace(";", ",").split(",")]
    seen: set[str] = set()
    for raw in iterable:
        token = raw.upper()
        if not _WORKSTREAM_ID_RE.fullmatch(token):
            continue
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def _file_mtime(path: Path) -> dt.datetime | None:
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return None
    return dt.datetime.fromtimestamp(stamp, tz=dt.timezone.utc).astimezone(_COMPASS_TZ)


def _date_midday_local(day: dt.date, *, tz: dt.tzinfo | None) -> dt.datetime:
    zone = tz or _COMPASS_TZ
    return dt.datetime.combine(day, dt.time(hour=12, minute=0), tzinfo=zone)


def _resolve_index_link_to_repo_path(
    *,
    repo_root: Path,
    index_path: Path,
    markdown_link: str,
) -> str:
    target = _extract_link_target(markdown_link)
    if not target:
        return ""
    raw = Path(target)
    if raw.is_absolute():
        resolved = raw.resolve()
    else:
        repo_relative_candidate = (repo_root / raw).resolve()
        index_relative_candidate = (index_path.parent / raw).resolve()
        resolved = repo_relative_candidate if repo_relative_candidate.exists() else index_relative_candidate
    return _as_repo_path(repo_root, resolved)


def _run_git(repo_root: Path, args: Sequence[str]) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return 127, ""
    return int(completed.returncode), str(completed.stdout or "")


def _git_identity(repo_root: Path) -> tuple[str, str]:
    _, name_out = _run_git(repo_root, ["config", "user.name"])
    _, email_out = _run_git(repo_root, ["config", "user.email"])
    return name_out.strip(), email_out.strip()


def _canonicalize_git_identity(repo_root: Path, *, name: str, email: str) -> tuple[str, str]:
    normalized_name = " ".join(str(name or "").split()).strip()
    normalized_email = " ".join(str(email or "").split()).strip()
    if not normalized_name and not normalized_email:
        return "", ""

    token = normalized_name
    if normalized_email:
        token = f"{normalized_name} <{normalized_email}>"
    rc, out = _run_git(repo_root, ["check-mailmap", token])
    if rc != 0:
        return normalized_name, normalized_email

    mapped = " ".join(str(out or "").split()).strip()
    if "<" not in mapped or ">" not in mapped:
        return normalized_name, normalized_email
    mapped_name, _, remainder = mapped.rpartition(" <")
    mapped_email = remainder[:-1] if remainder.endswith(">") else remainder
    return mapped_name.strip(), mapped_email.strip()


def _collect_git_commits(repo_root: Path, *, since_hours: int, my_name: str, my_email: str) -> list[dict[str, Any]]:
    log_args = [
        "log",
        f"--since={since_hours} hours ago",
        "--pretty=format:%H%x1f%ct%x1f%an%x1f%ae%x1f%s",
        "--name-only",
    ]
    rc, out = _run_git(repo_root, ["log", "--use-mailmap", *log_args[1:]])
    if rc != 0:
        rc, out = _run_git(repo_root, log_args)
    if rc != 0:
        return []

    commits: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    files: list[str] = []
    live_casebook_bug_paths = _load_casebook_index_paths(repo_root)

    for raw in out.splitlines():
        if "\x1f" in raw:
            if current is not None:
                current["files"] = _normalized_publishable_activity_files(
                    repo_root=repo_root,
                    files=files,
                    live_casebook_bug_paths=live_casebook_bug_paths,
                )
                commits.append(current)
            parts = raw.split("\x1f")
            if len(parts) < 5:
                current = None
                files = []
                continue
            try:
                ts = dt.datetime.fromtimestamp(int(parts[1]), tz=dt.timezone.utc)
            except (TypeError, ValueError, OSError):
                ts = dt.datetime.now(tz=dt.timezone.utc)
            author_name, author_email = _canonicalize_git_identity(
                repo_root,
                name=parts[2].strip(),
                email=parts[3].strip(),
            )
            current = {
                "sha": parts[0].strip(),
                "ts": ts,
                "author_name": author_name,
                "author_email": author_email,
                "subject": _sanitize_retired_surface_text(parts[4].strip()),
            }
            files = []
            continue

        if current is not None and raw.strip():
            files.append(raw.strip())

    if current is not None:
        current["files"] = _normalized_publishable_activity_files(
            repo_root=repo_root,
            files=files,
            live_casebook_bug_paths=live_casebook_bug_paths,
        )
        commits.append(current)

    name_token = my_name.strip().lower()
    email_token = my_email.strip().lower()

    def _is_mine(commit: Mapping[str, Any]) -> bool:
        author_name = str(commit.get("author_name", "")).strip().lower()
        author_email = str(commit.get("author_email", "")).strip().lower()
        if email_token and author_email == email_token:
            return True
        if name_token and author_name == name_token:
            return True
        if not email_token and not name_token:
            return False
        return False

    mine = [item for item in commits if _is_mine(item)]
    mine.sort(key=lambda item: item.get("ts", dt.datetime.min.replace(tzinfo=dt.timezone.utc)), reverse=True)
    return mine


def _collect_git_local_changes(repo_root: Path) -> list[dict[str, str]]:
    rc, out = _run_git(repo_root, ["status", "--porcelain", "--untracked-files=all"])
    if rc != 0:
        return []
    live_casebook_bug_paths = _load_casebook_index_paths(repo_root)
    rows: list[dict[str, str]] = []
    for raw in out.splitlines():
        if not raw:
            continue
        status = raw[:2]
        path = raw[3:].strip() if len(raw) > 3 else ""
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        token = _normalize_repo_token(path, repo_root=repo_root)
        if _should_skip_publishable_activity_path(
            repo_root=repo_root,
            path=token,
            live_casebook_bug_paths=live_casebook_bug_paths,
        ):
            continue
        if _should_skip_deleted_casebook_bug(
            repo_root=repo_root,
            status_token=status.strip() or status,
            path=token,
            live_casebook_bug_paths=live_casebook_bug_paths,
        ):
            continue
        if _should_skip_deleted_legacy_bug_path(
            repo_root=repo_root,
            status_token=status.strip() or status,
            path=token,
        ):
            continue
        rows.append({"status": status.strip() or status, "path": token})
    return rows


def _normalized_publishable_activity_files(
    *,
    repo_root: Path,
    files: Sequence[str],
    live_casebook_bug_paths: set[str],
) -> list[str]:
    return sorted(
        {
            normalized
            for item in files
            if str(item or "").strip()
            for normalized in [_normalize_repo_token(str(item), repo_root=repo_root)]
            if not _should_skip_publishable_activity_path(
                repo_root=repo_root,
                path=normalized,
                live_casebook_bug_paths=live_casebook_bug_paths,
            )
        }
    )


def _should_skip_publishable_activity_path(
    *,
    repo_root: Path,
    path: str,
    live_casebook_bug_paths: set[str],
) -> bool:
    token = str(path or "").strip()
    if not token:
        return True
    if _contains_retired_surface_marker(token):
        return True
    if _is_retired_surface_module_path(token):
        return True
    if _should_skip_internal_runtime_artifact(token):
        return True
    if _is_deindexed_missing_casebook_bug_path(
        repo_root=repo_root,
        path=token,
        live_casebook_bug_paths=live_casebook_bug_paths,
    ):
        return True
    return False


def _load_casebook_index_paths(repo_root: Path) -> set[str]:
    index_path = surface_path_helpers.resolve_repo_path(repo_root=repo_root, token="odylith/casebook/bugs/INDEX.md")
    if not index_path.is_file():
        return set()
    try:
        text = index_path.read_text(encoding="utf-8")
    except OSError:
        return set()
    paths: set[str] = set()
    for match in re.finditer(r"\(([^)\n]+\.md)\)", text):
        raw = match.group(1).strip()
        if not raw or raw.startswith("http://") or raw.startswith("https://"):
            continue
        candidate = raw
        if "/" not in candidate:
            candidate = f"odylith/casebook/bugs/{candidate}"
        normalized = _normalize_repo_token(candidate, repo_root=repo_root)
        if normalized:
            paths.add(normalized)
    return paths


def _should_skip_deleted_casebook_bug(
    *,
    repo_root: Path,
    status_token: str,
    path: str,
    live_casebook_bug_paths: set[str],
) -> bool:
    token = str(path or "").strip()
    if "D" not in str(status_token or "").upper():
        return False
    if not token.startswith("odylith/casebook/bugs/"):
        return False
    if token in live_casebook_bug_paths:
        return False
    return not surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=token).exists()


def _is_deindexed_missing_casebook_bug_path(
    *,
    repo_root: Path,
    path: str,
    live_casebook_bug_paths: set[str],
) -> bool:
    token = str(path or "").strip()
    if not token.startswith(_CASEBOOK_BUG_PATH_PREFIX) or not token.endswith(".md"):
        return False
    if token in live_casebook_bug_paths:
        return False
    return not surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=token).exists()


def _should_skip_internal_runtime_artifact(path: str) -> bool:
    token = str(path or "").strip().lower()
    if not token:
        return False
    return token.startswith(".odylith/") or token.startswith("odylith/.rollback/")


def _should_skip_deleted_legacy_bug_path(
    *,
    repo_root: Path,
    status_token: str,
    path: str,
) -> bool:
    token = str(path or "").strip()
    if "D" not in str(status_token or "").upper():
        return False
    if not token.startswith("bugs/"):
        return False
    if not (repo_root / "odylith" / "casebook" / "bugs" / "INDEX.md").is_file():
        return False
    return not surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=token).exists()


def _contains_retired_surface_marker(text: str) -> bool:
    token = str(text or "").strip().lower()
    return bool(token) and _RETIRED_SURFACE_MARKER in token


def _surface_module_stem_from_activity_path(path: str) -> str:
    token = str(path or "").strip().replace("\\", "/").lower()
    if token.startswith("src/odylith/runtime/surfaces/") and token.endswith(".py"):
        return Path(token).stem
    if token.startswith(_UNIT_RUNTIME_TEST_PREFIX) and token.endswith(".py"):
        stem = Path(token).stem
        if stem.startswith("test_"):
            return stem.removeprefix("test_")
    return ""


def _is_retired_surface_module_path(path: str) -> bool:
    stem = _surface_module_stem_from_activity_path(path)
    if not stem:
        return False
    governed_family = stem.startswith("compass_standup_brief_")
    shell_presenter_family = stem.startswith("tooling_dashboard_") and stem.endswith("_presenter")
    if not governed_family and not shell_presenter_family:
        return False
    return stem not in _ACTIVE_SURFACE_MODULE_STEMS


def _sanitize_retired_surface_text(text: str) -> str:
    token = str(text or "").strip()
    if not _contains_retired_surface_marker(token):
        return token
    return re.sub(
        rf"(?i)\b{re.escape(_RETIRED_SURFACE_MARKER)}\b",
        _RETIRED_SURFACE_LABEL,
        token,
    )


def _local_change_action(status_token: str) -> str:
    token = "".join(ch for ch in str(status_token or "") if ch != " ").upper()
    if token == "??":
        return "Added"
    if token == "!!":
        return "Ignored"
    if "U" in token:
        return "Conflict"
    if "R" in token:
        return "Renamed"
    if "D" in token:
        return "Deleted"
    if "A" in token and "M" in token:
        return "Added/Modified"
    if "A" in token:
        return "Added"
    if "M" in token:
        return "Modified"
    if "C" in token:
        return "Copied"
    return "Updated"


def _local_change_summary(*, status_token: str, path: str) -> str:
    action = _local_change_action(status_token)
    clean_path = str(path or "").strip()
    if clean_path:
        return f"{action} {clean_path}"
    return action


def _local_change_event_ts(
    *,
    repo_root: Path,
    path: str,
    fallback: dt.datetime,
) -> dt.datetime:
    token = str(path or "").strip()
    if token:
        resolved = surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=token)
        ts = _file_mtime(resolved)
        if isinstance(ts, dt.datetime):
            return ts
    # Deletions or unresolved paths cannot provide mtime; keep a deterministic fallback.
    return fallback


def _parse_iso_ts(raw: str) -> dt.datetime | None:
    token = str(raw or "").strip()
    if not token:
        return None
    if token.endswith("Z"):
        token = f"{token[:-1]}+00:00"
    try:
        parsed = dt.datetime.fromisoformat(token)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_COMPASS_TZ)
    return parsed.astimezone(_COMPASS_TZ)


def _load_agent_stream_events(
    *,
    repo_root: Path,
    stream_path: Path,
    ws_path_index: Mapping[str, set[str]],
) -> list[dict[str, Any]]:
    if not stream_path.is_file():
        return []

    events: list[dict[str, Any]] = []
    live_casebook_bug_paths = _load_casebook_index_paths(repo_root)
    for idx, raw in enumerate(stream_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = str(raw or "").strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, Mapping):
            continue

        kind = str(payload.get("kind", "")).strip().lower()
        if kind == "update":
            kind = "statement"
        if kind not in {"decision", "implementation", "statement"}:
            continue

        summary = " ".join(str(payload.get("summary", "")).split()).strip()
        if not summary:
            continue

        ts = _parse_iso_ts(str(payload.get("ts_iso", "")).strip())
        if ts is None:
            continue

        workstreams: list[str] = []
        ws_values = payload.get("workstreams", [])
        if isinstance(ws_values, list):
            seen_ws: set[str] = set()
            for token in ws_values:
                ws_id = str(token or "").strip().upper()
                if not _WORKSTREAM_ID_RE.fullmatch(ws_id):
                    continue
                if ws_id in seen_ws:
                    continue
                seen_ws.add(ws_id)
                workstreams.append(ws_id)

        artifacts: list[str] = []
        artifact_values = payload.get("artifacts", [])
        if isinstance(artifact_values, list):
            seen_artifacts: set[str] = set()
            for token in artifact_values:
                normalized = _normalize_repo_token(str(token or "").strip(), repo_root=repo_root)
                if normalized in seen_artifacts:
                    continue
                if _should_skip_publishable_activity_path(
                    repo_root=repo_root,
                    path=normalized,
                    live_casebook_bug_paths=live_casebook_bug_paths,
                ):
                    continue
                seen_artifacts.add(normalized)
                artifacts.append(normalized)

        if not workstreams and artifacts:
            workstreams = _map_paths_to_workstreams(artifacts, ws_path_index)

        author = " ".join(str(payload.get("author", "")).split()).strip() or "assistant"
        source = " ".join(str(payload.get("source", "")).split()).strip() or "assistant"
        session_id = " ".join(str(payload.get("session_id", "")).split()).strip()
        transaction_id = " ".join(str(payload.get("transaction_id", "")).split()).strip()
        transaction_seq_raw = payload.get("transaction_seq")
        transaction_seq = int(transaction_seq_raw) if isinstance(transaction_seq_raw, int) and transaction_seq_raw >= 0 else None
        context = " ".join(str(payload.get("context", "")).split()).strip()
        headline_hint = " ".join(str(payload.get("headline_hint", "")).split()).strip()
        boundary = str(payload.get("transaction_boundary", "")).strip().lower()
        if boundary not in {"start", "end"}:
            boundary = ""
        events.append(
            {
                "id": agent_runtime_contract.timeline_event_id(
                    kind=kind,
                    index=idx,
                    ts_iso=ts.isoformat(timespec="seconds"),
                ),
                "kind": kind,
                "ts": ts,
                "ts_iso": _safe_iso(ts),
                "summary": summary,
                "author": author,
                "sha": "",
                "files": artifacts[:12],
                "workstreams": workstreams,
                "source": source,
                "session_id": session_id,
                "transaction_id": transaction_id,
                "transaction_seq": transaction_seq,
                "context": context,
                "headline_hint": headline_hint,
                "transaction_boundary": boundary,
            }
        )

    events.sort(key=lambda item: item.get("ts", dt.datetime.min.replace(tzinfo=dt.timezone.utc)), reverse=True)
    return events


def _load_codex_stream_events(
    *,
    repo_root: Path,
    stream_path: Path,
    ws_path_index: Mapping[str, set[str]],
) -> list[dict[str, Any]]:
    return _load_agent_stream_events(
        repo_root=repo_root,
        stream_path=stream_path,
        ws_path_index=ws_path_index,
    )


def _collect_workstream_path_index(
    *,
    repo_root: Path,
    traceability_graph: Mapping[str, Any],
    mermaid_catalog: Mapping[str, Any],
) -> dict[str, set[str]]:
    return ws_inference.collect_workstream_path_index_from_traceability(
        repo_root=repo_root,
        traceability_graph=traceability_graph,
        mermaid_catalog=mermaid_catalog,
    )


def _map_paths_to_workstreams(paths: Iterable[str], ws_path_index: Mapping[str, set[str]]) -> list[str]:
    return ws_inference.map_paths_to_workstreams(paths, ws_path_index)


def _build_window_activity(events: list[dict[str, Any]], *, now: dt.datetime, hours: int) -> list[dict[str, Any]]:
    cutoff = now - dt.timedelta(hours=hours)
    selected: list[dict[str, Any]] = []
    for event in events:
        ts = event.get("ts")
        if not isinstance(ts, dt.datetime):
            continue
        if ts >= cutoff:
            selected.append(event)
    selected.sort(key=lambda row: row.get("ts", now), reverse=True)
    return selected


__all__ = [
    name
    for name in globals()
    if name.startswith('_') and name not in {'__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__spec__'}
]
