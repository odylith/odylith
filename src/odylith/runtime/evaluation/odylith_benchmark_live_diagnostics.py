"""Focused workspace diagnostics for live benchmark failures."""

from __future__ import annotations

import contextlib
import difflib
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping, Sequence


_RUNTIME_STATE_PATHS = (
    ".odylith/install.json",
    ".odylith/consumer-profile.json",
    ".odylith/reasoning.config.v1.json",
    ".odylith/install-ledger.v1.jsonl",
    ".odylith/runtime/odylith-benchmarks/latest.v1.json",
    ".odylith/runtime/odylith-benchmarks/latest-proof.v1.json",
    ".odylith/runtime/odylith-benchmarks/latest-diagnostic.v1.json",
)
_MAX_STATUS_ROWS = 40
_MAX_TRACKED_PATHS = 80
_MAX_DIFFERENCES = 20
_MAX_DIFF_EXCERPT_CHARS = 2000
_BACKTICK_LITERAL_PATTERN = re.compile(r"`([^`]+)`")
_PROMPT_VISIBLE_PATH_PATTERN = re.compile(
    r"`([^`\n]+)`|(?<![A-Za-z0-9_])([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+|[A-Za-z0-9_.-]+\.(?:css|html|js|json|md|mmd|png|py|svg|toml|txt))(?=$|[\s`'\"),.:;\]])"
)
_PROMPT_VISIBLE_FILE_SUFFIXES = frozenset(
    {
        ".css",
        ".html",
        ".js",
        ".json",
        ".md",
        ".mmd",
        ".png",
        ".py",
        ".svg",
        ".toml",
        ".txt",
    }
)


def _dedupe_strings(rows: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in rows:
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _string_rows(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(token).strip() for token in value if str(token).strip()]


def _safe_resolve_path(path: Path) -> Path | None:
    with contextlib.suppress(OSError, RuntimeError):
        return path.resolve()
    return None


def _existing_path_kind(path: Path) -> str:
    with contextlib.suppress(OSError):
        if path.is_file():
            return "file"
        if path.is_dir():
            return "dir"
    return ""


def _safe_read_text_preview(path: Path, *, max_chars: int = 12000) -> str:
    try:
        payload = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    return payload[:max_chars]


def _looks_like_prompt_visible_repo_path(token: str) -> bool:
    normalized = str(token or "").strip().strip("`'\"()[]{}<>.,:;")
    if not normalized or "://" in normalized or normalized.startswith("--"):
        return False
    if "/" in normalized:
        return True
    if normalized in {"AGENTS.md", "CLAUDE.md", "README.md", "Makefile", "Dockerfile"}:
        return True
    return Path(normalized).suffix.lower() in _PROMPT_VISIBLE_FILE_SUFFIXES


def _existing_repo_paths(*, repo_root: Path, paths: Sequence[str]) -> list[str]:
    resolved_root = Path(repo_root).resolve()
    rows: list[str] = []
    for raw in paths:
        token = str(raw or "").strip().replace("\\", "/").lstrip("./")
        if not token:
            continue
        candidate = (resolved_root / token).resolve()
        try:
            candidate.relative_to(resolved_root)
        except ValueError:
            continue
        if candidate.exists():
            rows.append(token)
    return _dedupe_strings(rows)


def _git_status_path_from_line(line: str) -> str:
    token = str(line or "").rstrip()
    if len(token) <= 3:
        return ""
    body = token[3:].strip()
    if " -> " in body:
        body = body.rsplit(" -> ", 1)[-1]
    return body.strip()


def _workspace_git_status_entries(*, workspace_root: Path) -> list[dict[str, str]]:
    workspace = Path(workspace_root).resolve()
    if not workspace.is_dir():
        return []
    try:
        completed = subprocess.run(
            ["git", "status", "--short", "--untracked-files=all"],
            cwd=str(workspace),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return []
    if int(completed.returncode or 0) != 0:
        return []
    entries: list[dict[str, str]] = []
    for raw_line in str(completed.stdout or "").splitlines():
        line = str(raw_line or "").rstrip()
        if not line:
            continue
        entries.append({"line": line, "path": _git_status_path_from_line(line)})
        if len(entries) >= _MAX_STATUS_ROWS:
            break
    return entries


def failure_artifact_paths(
    *,
    scenario: Mapping[str, Any],
    effective_snapshot_paths: Sequence[str],
    observed_paths: Sequence[str],
    candidate_write_paths: Sequence[str],
    structured_output: Mapping[str, Any],
    strip_paths: Sequence[Path],
) -> list[str]:
    rows: list[str] = []
    for key in (
        "changed_paths",
        "required_paths",
        "critical_paths",
    ):
        rows.extend(str(token).strip() for token in scenario.get(key, []) if str(token).strip())
    rows.extend(str(token).strip() for token in effective_snapshot_paths if str(token).strip())
    rows.extend(str(token).strip() for token in observed_paths if str(token).strip())
    rows.extend(str(token).strip() for token in candidate_write_paths if str(token).strip())
    rows.extend(str(token).strip() for token in structured_output.get("changed_files", []) if str(token).strip())
    rows.extend(path.as_posix() for path in strip_paths if path.as_posix().strip())
    rows.extend(_RUNTIME_STATE_PATHS)
    return _dedupe_strings(rows)[:_MAX_TRACKED_PATHS]


def focused_local_check_commands(*, focused_local_checks: Sequence[str]) -> list[str]:
    rows: list[str] = []
    for raw in focused_local_checks:
        text = str(raw or "").strip()
        if not text:
            continue
        match = _BACKTICK_LITERAL_PATTERN.search(text)
        command = str(match.group(1) if match else text).strip()
        if not command:
            continue
        if command.startswith("tests/"):
            rows.append(f"PYTHONPATH=src .venv/bin/pytest -q {command}")
            continue
        if command.startswith(("odylith ", "PYTHONPATH=", ".venv/bin/", "./.venv/bin/", "python ", "/")):
            rows.append(command)
    return _dedupe_strings(rows)


def focused_local_check_result_lines(*, result: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(result, Mapping):
        return []
    rows: list[str] = []
    for item in result.get("results", []):
        if not isinstance(item, Mapping):
            continue
        status = str(item.get("status", "")).strip()
        command = str(item.get("command", "")).strip()
        if not status or not command:
            continue
        label = command
        if "pytest -q " in command:
            label = command.split("pytest -q ", 1)[1].strip()
        rows.append(f"{status}: {label}")
    return rows[:8]


def prompt_payload_selected_docs(*, prompt_payload: Mapping[str, Any] | None) -> list[str]:
    payload = dict(prompt_payload or {})
    context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    retrieval_plan = (
        dict(context_packet.get("retrieval_plan", {}))
        if isinstance(context_packet.get("retrieval_plan"), Mapping)
        else {}
    )
    architecture_audit = (
        dict(payload.get("architecture_audit", {}))
        if isinstance(payload.get("architecture_audit"), Mapping)
        else {}
    )
    return _dedupe_strings(
        [
            *_string_rows(payload.get("docs")),
            *_string_rows(payload.get("relevant_docs")),
            *_string_rows(retrieval_plan.get("selected_docs")),
            *_string_rows(architecture_audit.get("required_reads")),
        ]
    )


def prompt_payload_observed_paths(*, prompt_payload: Mapping[str, Any] | None) -> list[str]:
    payload = dict(prompt_payload or {})
    context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    anchors = dict(context_packet.get("anchors", {})) if isinstance(context_packet.get("anchors"), Mapping) else {}
    retrieval_plan = (
        dict(context_packet.get("retrieval_plan", {}))
        if isinstance(context_packet.get("retrieval_plan"), Mapping)
        else {}
    )
    architecture_audit = (
        dict(payload.get("architecture_audit", {}))
        if isinstance(payload.get("architecture_audit"), Mapping)
        else {}
    )
    return _dedupe_strings(
        [
            *_string_rows(payload.get("changed_paths")),
            *prompt_payload_selected_docs(prompt_payload=payload),
            *_string_rows(payload.get("implementation_anchors")),
            *_string_rows(anchors.get("changed_paths")),
            *_string_rows(anchors.get("explicit_paths")),
            *_string_rows(architecture_audit.get("changed_paths")),
            *_string_rows(architecture_audit.get("implementation_anchors")),
            *_string_rows(retrieval_plan.get("selected_docs")),
        ]
    )


def raw_prompt_visible_paths(*, repo_root: Path, raw_prompt: Mapping[str, Any] | None) -> list[str]:
    payload = dict(raw_prompt or {})
    texts: list[str] = []
    prompt = str(payload.get("prompt", "")).strip()
    if prompt:
        texts.append(prompt)
    acceptance = payload.get("acceptance_criteria", [])
    if isinstance(acceptance, list):
        texts.extend(str(token).strip() for token in acceptance if str(token).strip())
    candidates: list[str] = []
    for text in texts:
        for match in _PROMPT_VISIBLE_PATH_PATTERN.finditer(text):
            token = str(match.group(1) or match.group(2) or "").strip().strip("`'\"()[]{}<>.,:;")
            if not _looks_like_prompt_visible_repo_path(token):
                continue
            candidates.append(token.replace("\\", "/").lstrip("./"))
    return _existing_repo_paths(repo_root=repo_root, paths=_dedupe_strings(candidates))


def workspace_state_diff(
    *,
    repo_root: Path,
    workspace_root: Path,
    tracked_paths: Sequence[str],
) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    workspace = Path(workspace_root).resolve()
    paths = _dedupe_strings([str(token).strip() for token in tracked_paths if str(token).strip()])
    if not workspace.is_dir():
        return {
            "workspace_root": workspace.as_posix(),
            "workspace_root_exists": False,
            "tracked_path_count": len(paths),
            "tracked_paths": paths[:_MAX_STATUS_ROWS],
            "difference_count": 1,
            "differences": [
                {
                    "path": ".",
                    "status": "workspace_root_missing",
                    "repo_kind": "dir",
                    "workspace_kind": "",
                }
            ],
            "git_status": [],
            "git_status_paths": [],
        }
    status_entries = _workspace_git_status_entries(workspace_root=workspace)
    paths = _dedupe_strings(
        [
            *paths,
            *[str(entry.get("path", "")).strip() for entry in status_entries if str(entry.get("path", "")).strip()],
        ]
    )
    differences: list[dict[str, Any]] = []
    for token in paths:
        repo_path = _safe_resolve_path(repo / token)
        workspace_path = _safe_resolve_path(workspace / token)
        repo_kind = _existing_path_kind(repo_path) if repo_path is not None else ""
        workspace_kind = _existing_path_kind(workspace_path) if workspace_path is not None else ""
        if repo_kind == workspace_kind == "file" and repo_path is not None and workspace_path is not None:
            try:
                same = repo_path.read_bytes() == workspace_path.read_bytes()
            except OSError:
                same = False
            if same:
                continue
            diff_excerpt = ""
            repo_text = _safe_read_text_preview(repo_path)
            workspace_text = _safe_read_text_preview(workspace_path)
            if repo_text or workspace_text:
                diff_excerpt = "".join(
                    difflib.unified_diff(
                        repo_text.splitlines(True),
                        workspace_text.splitlines(True),
                        fromfile=f"repo/{token}",
                        tofile=f"workspace/{token}",
                    )
                )[:_MAX_DIFF_EXCERPT_CHARS]
            differences.append(
                {
                    "path": token,
                    "status": "different_file",
                    "repo_kind": repo_kind,
                    "workspace_kind": workspace_kind,
                    "diff_excerpt": diff_excerpt,
                }
            )
            continue
        if repo_kind != workspace_kind:
            status = "workspace_missing" if repo_kind and not workspace_kind else "workspace_extra" if workspace_kind else ""
            if not status:
                continue
            differences.append(
                {
                    "path": token,
                    "status": status,
                    "repo_kind": repo_kind,
                    "workspace_kind": workspace_kind,
                }
            )
    return {
        "workspace_root": workspace.as_posix(),
        "workspace_root_exists": True,
        "tracked_path_count": len(paths),
        "tracked_paths": paths[:_MAX_STATUS_ROWS],
        "difference_count": len(differences),
        "differences": differences[:_MAX_DIFFERENCES],
        "git_status": [str(entry.get("line", "")).strip() for entry in status_entries if str(entry.get("line", "")).strip()],
        "git_status_paths": [
            str(entry.get("path", "")).strip()
            for entry in status_entries
            if str(entry.get("path", "")).strip()
        ],
    }


__all__ = [
    "failure_artifact_paths",
    "focused_local_check_commands",
    "focused_local_check_result_lines",
    "prompt_payload_observed_paths",
    "prompt_payload_selected_docs",
    "raw_prompt_visible_paths",
    "workspace_state_diff",
]
