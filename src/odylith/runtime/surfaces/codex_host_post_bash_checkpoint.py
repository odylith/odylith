"""Codex PostToolUse checkpoint for edit-like Codex tool calls.

When Codex finishes an edit-like Bash command or native patch tool call
(``apply_patch``, ``cp``, ``mv``, ``sed -i``, etc. -- see
``codex_host_shared.edit_like_bash``), this hook nudges Odylith in two
narrow steps:

1. Run ``odylith start --repo-root .`` through a short repo-local
   cache so the session stays grounded without paying the launcher cost
   after every edit.
2. If the edit touched any repo-relative path under the Odylith
   governed source-of-truth subtrees, run
   ``odylith sync --impact-mode selective <paths>`` so the derived
   dashboards stay aligned.

The second step is Bash-checkpoint parity with Claude's
``post-edit-checkpoint`` hook
(``claude_host_post_edit_checkpoint.refresh_governance``). Current Codex hook
schemas expose ``PostToolUse`` for ``Bash`` only; native desktop/app tool
payloads can still be parsed by this module in tests or manual fallback
commands, but they are not claimed as automatically hook-dispatched.

The hook never blocks the tool call. It always exits 0; on failure
it emits a fail-soft ``systemMessage`` and assistant-visible fallback context
describing what went wrong so the operator can recover manually if needed.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import surface_runtime as intervention_surface_runtime
from odylith.runtime.intervention_engine import visibility_replay
from odylith.runtime.surfaces import claude_host_shared
from odylith.runtime.surfaces import codex_host_shared

_PATCH_PATH_RE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.MULTILINE)
_PATCH_MOVE_RE = re.compile(r"^\*\*\* Move to: (.+)$", re.MULTILINE)
_REDIRECT_TARGET_RE = re.compile(r">\s*(?:'([^']+)'|\"([^\"]+)\"|([^\s;&|]+))")
_NODE_SINGLE_PATH_CALL_RE = re.compile(
    r"""
    \b(?:[\w$]+\.)*
    (?:
        writeFileSync|appendFileSync|rmSync|unlinkSync|mkdirSync|openSync|
        writeFile|appendFile|rm|unlink|mkdir
    )
    \(\s*(['"])([^'"]+)\1
    """,
    re.VERBOSE,
)
_NODE_TWO_PATH_CALL_RE = re.compile(
    r"""
    \b(?:[\w$]+\.)*
    (?:
        renameSync|copyFileSync|
        rename|copyFile
    )
    \(\s*(['"])([^'"]+)\1\s*,\s*(['"])([^'"]+)\3
    """,
    re.VERBOSE,
)
_SHELL_CONTROL_TOKENS: frozenset[str] = frozenset({"&&", "||", ";", "|", "&"})
_START_GROUND_CACHE_RELATIVE = Path(
    ".odylith/runtime/latency-cache/codex-post-bash-start.v1.json"
)
_START_GROUND_CACHE_TTL_SECONDS = 20 * 60
_PROCESS_FALLBACK_SESSION_RE = re.compile(r"^agent-\d+$")


def _is_shell_redirection_token(token: str) -> bool:
    candidate = str(token or "").strip()
    if not candidate:
        return False
    if candidate.startswith((">", "<", "&>")):
        return True
    return bool(re.match(r"^\d+[<>]", candidate))


def _trim_shell_command_tokens(tokens: list[str]) -> list[str]:
    trimmed: list[str] = []
    for token in tokens:
        if token in _SHELL_CONTROL_TOKENS or _is_shell_redirection_token(token):
            break
        trimmed.append(token)
    return trimmed


def should_checkpoint(command: str) -> bool:
    return codex_host_shared.edit_like_bash(command)


def _start_ground_cache_path(*, project_dir: Path | str) -> Path:
    return Path(project_dir).expanduser().resolve() / _START_GROUND_CACHE_RELATIVE


def _start_ground_cache_key(session_id: str) -> str:
    token = str(session_id or "").strip()
    if not token or _PROCESS_FALLBACK_SESSION_RE.match(token):
        return "codex-default"
    return token


def _load_start_ground_cache(*, project_dir: Path | str) -> dict[str, Any]:
    path = _start_ground_cache_path(project_dir=project_dir)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _write_start_ground_cache(*, project_dir: Path | str, payload: Mapping[str, Any]) -> None:
    path = _start_ground_cache_path(project_dir=project_dir)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(dict(payload), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError:
        return


def should_run_start_grounding(
    *,
    project_dir: Path | str,
    session_id: str,
    now_seconds: float | None = None,
    ttl_seconds: int = _START_GROUND_CACHE_TTL_SECONDS,
) -> bool:
    cache = _load_start_ground_cache(project_dir=project_dir)
    sessions = cache.get("sessions")
    if not isinstance(sessions, Mapping):
        return True
    record = sessions.get(_start_ground_cache_key(session_id))
    if not isinstance(record, Mapping):
        return True
    try:
        attempted_at = float(record.get("attempted_at_seconds"))
    except (TypeError, ValueError):
        return True
    now = time.time() if now_seconds is None else float(now_seconds)
    age_seconds = now - attempted_at
    return not (0 <= age_seconds < max(1, int(ttl_seconds)))


def record_start_grounding_attempt(
    *,
    project_dir: Path | str,
    session_id: str,
    completed: subprocess.CompletedProcess[str] | None,
    now_seconds: float | None = None,
) -> None:
    cache = _load_start_ground_cache(project_dir=project_dir)
    sessions = cache.get("sessions")
    if not isinstance(sessions, dict):
        sessions = {}
    now = time.time() if now_seconds is None else float(now_seconds)
    sessions[_start_ground_cache_key(session_id)] = {
        "attempted_at_seconds": now,
        "returncode": completed.returncode if completed is not None else None,
        "status": (
            "launcher_unavailable"
            if completed is None
            else "completed"
            if completed.returncode == 0
            else "failed"
        ),
    }
    _write_start_ground_cache(
        project_dir=project_dir,
        payload={
            "version": 1,
            "ttl_seconds": _START_GROUND_CACHE_TTL_SECONDS,
            "sessions": sessions,
        },
    )


def run_start_grounding_if_due(*, project_dir: Path | str, session_id: str) -> None:
    if not should_run_start_grounding(project_dir=project_dir, session_id=session_id):
        return
    completed = codex_host_shared.run_odylith(
        project_dir=project_dir,
        args=["start", "--repo-root", "."],
        timeout=20,
    )
    record_start_grounding_attempt(
        project_dir=project_dir,
        session_id=session_id,
        completed=completed,
    )


def dirty_governed_paths(*, project_dir: Path | str) -> list[str]:
    """Return repo-relative governed paths with uncommitted changes.

    Uses ``git status --porcelain -z`` rooted at the project dir,
    filters through
    ``claude_host_shared.should_refresh_governed_edit``, and returns
    the list in the order git reports. Fails soft to an empty list if
    git is unavailable or errors.
    """
    project = Path(project_dir).expanduser().resolve()
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain", "-z"],
            cwd=str(project),
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0:
        return []

    paths: list[str] = []
    records = completed.stdout.split("\x00")
    if records and records[-1] == "":
        records.pop()
    index = 0
    while index < len(records):
        record = records[index]
        if len(record) < 3:
            index += 1
            continue
        status_xy = record[:2]
        path = record[3:]
        if "R" in status_xy:
            if claude_host_shared.should_refresh_governed_edit(path):
                paths.append(path)
            if index + 1 < len(records):
                old_path = records[index + 1]
                if claude_host_shared.should_refresh_governed_edit(old_path):
                    paths.append(old_path)
            index += 2
            continue
        if "C" in status_xy:
            if claude_host_shared.should_refresh_governed_edit(path):
                paths.append(path)
            index += 2
            continue
        if claude_host_shared.should_refresh_governed_edit(path):
            paths.append(path)
        index += 1
    return _dedupe_paths(paths)


def governed_changed_paths(*, project_dir: Path | str) -> list[str]:
    """Back-compat alias for repo-wide dirty governed paths."""
    return dirty_governed_paths(project_dir=project_dir)


def _project_relative_path(*, project_dir: Path, raw_path: str) -> str:
    token = str(raw_path or "").strip()
    if not token:
        return ""
    candidate = Path(token).expanduser()
    resolved = candidate.resolve() if candidate.is_absolute() else (project_dir / candidate).resolve()
    try:
        return resolved.relative_to(project_dir).as_posix()
    except ValueError:
        return ""


def _dedupe_paths(paths: list[str]) -> list[str]:
    collected: list[str] = []
    for path in paths:
        if path and path not in collected:
            collected.append(path)
    return collected


def _parts(*values: str) -> str:
    rows: list[str] = []
    for value in values:
        token = str(value or "").strip()
        if token and token not in rows:
            rows.append(token)
    return "\n\n".join(rows).strip()


def _paths_from_apply_patch(*, command: str, project_dir: Path) -> list[str]:
    tokens = [match.strip() for match in _PATCH_PATH_RE.findall(command)]
    tokens.extend(match.strip() for match in _PATCH_MOVE_RE.findall(command))
    return _dedupe_paths(
        [
            relative
            for relative in (_project_relative_path(project_dir=project_dir, raw_path=token) for token in tokens)
            if relative
        ]
    )


def _shell_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return []


def _operand_tokens(tokens: list[str]) -> list[str]:
    operands: list[str] = []
    after_double_dash = False
    for token in tokens:
        if after_double_dash:
            operands.append(token)
            continue
        if token == "--":
            after_double_dash = True
            continue
        if token.startswith("-"):
            continue
        operands.append(token)
    return operands


def _copy_move_sources_and_destination(tokens: list[str]) -> tuple[list[str], str]:
    operands: list[str] = []
    after_double_dash = False
    target_directory = ""
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if after_double_dash:
            operands.append(token)
            index += 1
            continue
        if token == "--":
            after_double_dash = True
            index += 1
            continue
        if token in {"-t", "--target-directory"} and index + 1 < len(tokens):
            target_directory = tokens[index + 1]
            index += 2
            continue
        if token.startswith("--target-directory="):
            target_directory = token.split("=", 1)[1].strip()
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        operands.append(token)
        index += 1
    if target_directory:
        return operands, target_directory
    if len(operands) < 2:
        return [], ""
    return operands[:-1], operands[-1]


def _copy_destinations(*, tokens: list[str], project_dir: Path) -> list[str]:
    sources, destination = _copy_move_sources_and_destination(tokens)
    if not sources or not destination:
        return []
    destination_path = Path(destination).expanduser()
    resolved_destination = destination_path.resolve() if destination_path.is_absolute() else (project_dir / destination_path).resolve()
    if len(sources) == 1 and not resolved_destination.is_dir() and not destination.endswith("/"):
        relative = _project_relative_path(project_dir=project_dir, raw_path=destination)
        return [relative] if relative else []
    targets: list[str] = []
    for source in sources:
        source_name = Path(source).name
        if not source_name:
            continue
        relative = _project_relative_path(
            project_dir=project_dir,
            raw_path=str(Path(destination) / source_name),
        )
        if relative:
            targets.append(relative)
    return _dedupe_paths(targets)


def _move_paths(*, tokens: list[str], project_dir: Path) -> list[str]:
    sources, destination = _copy_move_sources_and_destination(tokens)
    if not sources or not destination:
        return []
    destination_path = Path(destination).expanduser()
    resolved_destination = destination_path.resolve() if destination_path.is_absolute() else (project_dir / destination_path).resolve()
    targets: list[str] = []
    multi_target_dir = len(sources) > 1 or resolved_destination.is_dir() or destination.endswith("/")
    if not multi_target_dir:
        source_relative = _project_relative_path(project_dir=project_dir, raw_path=sources[0])
        if source_relative:
            targets.append(source_relative)
        destination_relative = _project_relative_path(project_dir=project_dir, raw_path=destination)
        if destination_relative:
            targets.append(destination_relative)
        return _dedupe_paths(targets)
    for source in sources:
        source_relative = _project_relative_path(project_dir=project_dir, raw_path=source)
        if source_relative:
            targets.append(source_relative)
        source_name = Path(source).name
        if not source_name:
            continue
        destination_relative = _project_relative_path(
            project_dir=project_dir,
            raw_path=str(Path(destination) / source_name),
        )
        if destination_relative:
            targets.append(destination_relative)
    return _dedupe_paths(targets)


def _targets_after_script_operand(*, tokens: list[str]) -> list[str]:
    args = tokens[1:]
    if not args:
        return []
    saw_explicit_script_option = False
    expect_script_argument = False
    pending_inplace_suffix = False
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--":
            return args[index + 1 :]
        if expect_script_argument:
            expect_script_argument = False
            saw_explicit_script_option = True
            index += 1
            continue
        if pending_inplace_suffix:
            pending_inplace_suffix = False
            if token == "" or token.startswith("."):
                index += 1
                continue
        if token in {"-e", "-f"}:
            expect_script_argument = True
            index += 1
            continue
        if token == "-i":
            pending_inplace_suffix = True
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        if saw_explicit_script_option:
            return args[index:]
        return args[index + 1 :]
    return []


def _inline_script(tokens: list[str], *, option: str) -> str:
    if option not in tokens:
        return ""
    index = tokens.index(option)
    if index + 1 >= len(tokens):
        return ""
    return str(tokens[index + 1] or "")


def _literal_string(node: ast.AST | None, *, bindings: dict[str, str]) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return bindings.get(node.id, "")
    return ""


def _is_path_ctor(node: ast.AST | None) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "Path"
    if isinstance(node, ast.Attribute) and node.attr == "Path":
        return isinstance(node.value, ast.Name) and node.value.id == "pathlib"
    return False


def _path_from_expr(node: ast.AST | None, *, bindings: dict[str, str]) -> str:
    literal = _literal_string(node, bindings=bindings)
    if literal:
        return literal
    if not isinstance(node, ast.Call) or not _is_path_ctor(node.func) or not node.args:
        return ""
    return _literal_string(node.args[0], bindings=bindings)


def _mode_writes(mode: str) -> bool:
    candidate = str(mode or "")
    return any(flag in candidate for flag in ("w", "a", "x", "+"))


class _PythonInlineWriteCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.bindings: dict[str, str] = {}
        self.paths: list[str] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        value = _path_from_expr(node.value, bindings=self.bindings) or _literal_string(node.value, bindings=self.bindings)
        if value:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.bindings[target.id] = value
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self.paths.extend(self._paths_from_call(node))
        self.generic_visit(node)

    def _paths_from_call(self, node: ast.Call) -> list[str]:
        func = node.func
        if isinstance(func, ast.Name) and func.id == "open" and node.args:
            mode = ""
            if len(node.args) > 1:
                mode = _literal_string(node.args[1], bindings=self.bindings)
            if not mode:
                for keyword in node.keywords:
                    if keyword.arg == "mode":
                        mode = _literal_string(keyword.value, bindings=self.bindings)
                        break
            if _mode_writes(mode):
                path = _path_from_expr(node.args[0], bindings=self.bindings)
                return [path] if path else []
            return []
        if isinstance(func, ast.Attribute):
            if func.attr in {"write_text", "write_bytes", "touch", "unlink", "mkdir"}:
                path = _path_from_expr(func.value, bindings=self.bindings)
                return [path] if path else []
            if func.attr == "open":
                mode = ""
                if node.args:
                    mode = _literal_string(node.args[0], bindings=self.bindings)
                if not mode:
                    for keyword in node.keywords:
                        if keyword.arg == "mode":
                            mode = _literal_string(keyword.value, bindings=self.bindings)
                            break
                if _mode_writes(mode):
                    path = _path_from_expr(func.value, bindings=self.bindings)
                    return [path] if path else []
                return []
            if func.attr in {"rename", "replace"}:
                source = _path_from_expr(func.value, bindings=self.bindings)
                destination = _path_from_expr(node.args[0], bindings=self.bindings) if node.args else ""
                return [path for path in (source, destination) if path]
            if isinstance(func.value, ast.Name) and func.value.id == "shutil":
                if func.attr in {"copy", "copy2", "copyfile"}:
                    destination = _path_from_expr(node.args[1], bindings=self.bindings) if len(node.args) > 1 else ""
                    return [destination] if destination else []
                if func.attr == "move":
                    source = _path_from_expr(node.args[0], bindings=self.bindings) if node.args else ""
                    destination = _path_from_expr(node.args[1], bindings=self.bindings) if len(node.args) > 1 else ""
                    return [path for path in (source, destination) if path]
                return []
            if isinstance(func.value, ast.Name) and func.value.id == "os" and func.attr in {"remove", "unlink"}:
                path = _path_from_expr(node.args[0], bindings=self.bindings) if node.args else ""
                return [path] if path else []
        return []


def _paths_from_python_inline_script(*, tokens: list[str], project_dir: Path) -> list[str]:
    script = _inline_script(tokens, option="-c")
    if not script:
        return []
    try:
        tree = ast.parse(script, mode="exec")
    except SyntaxError:
        return []
    collector = _PythonInlineWriteCollector()
    collector.visit(tree)
    return _dedupe_paths(
        [
            relative
            for relative in (_project_relative_path(project_dir=project_dir, raw_path=path) for path in collector.paths)
            if relative
        ]
    )


def _paths_from_node_inline_script(*, tokens: list[str], project_dir: Path) -> list[str]:
    script = _inline_script(tokens, option="-e")
    if not script:
        return []
    raw_paths: list[str] = []
    for match in _NODE_TWO_PATH_CALL_RE.finditer(script):
        raw_paths.extend([match.group(2).strip(), match.group(4).strip()])
    for match in _NODE_SINGLE_PATH_CALL_RE.finditer(script):
        raw_paths.append(match.group(2).strip())
    return _dedupe_paths(
        [
            relative
            for relative in (_project_relative_path(project_dir=project_dir, raw_path=path) for path in raw_paths)
            if relative
        ]
    )


def _paths_from_token_list(*, tokens: list[str], project_dir: Path, raw_command: str) -> list[str]:
    tokens = _trim_shell_command_tokens(tokens)
    if not tokens:
        return []
    command = tokens[0]
    raw_targets: list[str] = []
    if command == "cp":
        return _copy_destinations(tokens=tokens[1:], project_dir=project_dir)
    if command == "mv":
        return _move_paths(tokens=tokens[1:], project_dir=project_dir)
    if command == "touch":
        raw_targets = _operand_tokens(tokens[1:])
    elif command == "mkdir":
        raw_targets = []
    elif command == "sed":
        raw_targets = _targets_after_script_operand(tokens=tokens)
    elif command == "perl":
        raw_targets = _targets_after_script_operand(tokens=tokens)
    elif command == "tee":
        raw_targets = _operand_tokens(tokens[1:])
    elif command == "cat":
        match = _REDIRECT_TARGET_RE.search(raw_command)
        if match:
            raw_targets = [next(group for group in match.groups() if group)]
    elif command in {"python", "python3"}:
        return _paths_from_python_inline_script(tokens=tokens, project_dir=project_dir)
    elif command == "node":
        return _paths_from_node_inline_script(tokens=tokens, project_dir=project_dir)
    return _dedupe_paths(
        [
            relative
            for relative in (_project_relative_path(project_dir=project_dir, raw_path=token) for token in raw_targets)
            if relative
        ]
    )


def inferred_command_paths(*, project_dir: Path | str, command: str) -> list[str]:
    """Infer exact repo-relative paths targeted by the current Bash command."""
    project = Path(project_dir).expanduser().resolve()
    raw_command = str(command or "")
    if not raw_command.strip():
        return []
    if "apply_patch" in raw_command:
        apply_patch_paths = _paths_from_apply_patch(command=raw_command, project_dir=project)
        if apply_patch_paths:
            return apply_patch_paths
    return _paths_from_token_list(tokens=_shell_tokens(raw_command), project_dir=project, raw_command=raw_command)


def command_scoped_governed_paths(*, project_dir: Path | str, command: str) -> list[str]:
    """Return dirty governed paths explicitly targeted by the current Bash command."""
    command_paths = inferred_command_paths(project_dir=project_dir, command=command)
    if not command_paths:
        return []
    dirty = set(dirty_governed_paths(project_dir=project_dir))
    return [path for path in command_paths if path in dirty and claude_host_shared.should_refresh_governed_edit(path)]


def _changed_paths_preview(paths: list[str]) -> str:
    preview = ", ".join(paths[:3])
    if len(paths) > 3:
        preview = f"{preview}, +{len(paths) - 3} more"
    return preview


def refresh_governance(*, project_dir: Path | str, paths: list[str]) -> dict[str, str] | None:
    """Run ``odylith sync --impact-mode selective <paths>`` and return the systemMessage.

    Returns ``None`` when there are no governed changed paths to refresh.
    """
    if not paths:
        return None
    project = Path(project_dir).expanduser().resolve()
    completed = codex_host_shared.run_odylith(
        project_dir=project,
        args=[
            "sync",
            "--repo-root",
            str(project),
            "--impact-mode",
            "selective",
            *paths,
        ],
        timeout=180,
    )
    preview = _changed_paths_preview(paths)
    if completed is None:
        return {
            "systemMessage": (
                f"Odylith governance refresh skipped after edit-like Bash command "
                f"touched {preview}: the repo-local launcher was not available."
            )
        }
    if completed.returncode == 0:
        return {
            "systemMessage": (
                f"Odylith governance refresh completed after edit-like Bash command "
                f"touched {preview}."
            )
        }
    detail = "\n".join(
        line.strip()
        for line in (completed.stderr or completed.stdout or "").splitlines()[-8:]
        if line.strip()
    )
    if not detail:
        detail = f"exit code {completed.returncode}"
    return {
        "systemMessage": (
            f"Odylith governance refresh failed after edit-like Bash command "
            f"touched {preview}: {detail}"
        )
    }


def _post_bash_bundle(
    *,
    project_dir: Path,
    command: str,
    session_id: str = "",
) -> dict[str, Any]:
    changed_paths = inferred_command_paths(project_dir=project_dir, command=command)
    if not changed_paths:
        return {}
    return host_surface_runtime.compose_host_conversation_bundle(
        repo_root=project_dir,
        host_family="codex",
        turn_phase="post_bash_checkpoint",
        session_id=session_id,
        changed_paths=changed_paths,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith codex post-bash-checkpoint",
        description="Nudge Odylith checkpointing after edit-like Bash commands in Codex.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for launcher resolution.")
    args = parser.parse_args(list(argv or sys.argv[1:]))
    payload = codex_host_shared.load_payload()
    command = codex_host_shared.command_from_hook_payload(payload)
    session_id = codex_host_shared.hook_session_id(payload)
    if not should_checkpoint(command):
        return 0

    project_dir = claude_host_shared.resolve_repo_root(args.repo_root)

    # Keep grounding in the edit-like checkpoint lane without paying the
    # launcher/start cost for every hook process in the same active session.
    run_start_grounding_if_due(project_dir=project_dir, session_id=session_id)

    # If the edit-like Bash command touched any governed source-of-truth
    # subtree, refresh the derived dashboards via selective sync. This
    # is Bash-checkpoint parity with Claude's post-edit lane; non-Bash
    # edit surfaces would need their own hook.
    changed = command_scoped_governed_paths(project_dir=project_dir, command=command)
    governance_message = refresh_governance(project_dir=project_dir, paths=changed)
    bundle = _post_bash_bundle(
        project_dir=project_dir,
        command=command,
        session_id=session_id,
    )
    decision = (
        host_surface_runtime.visible_intervention_decision(
            repo_root=project_dir,
            bundle=bundle,
            host_family="codex",
            turn_phase="post_bash_checkpoint",
            session_id=session_id,
            include_proposal=True,
            include_closeout=False,
            developer_include_closeout=True,
        )
        if bundle
        else None
    )
    developer_context = decision.developer_context if decision is not None else ""
    live_intervention = decision.visible_markdown if decision is not None else ""
    replay = visibility_replay.replayable_chat_markdown(
        repo_root=project_dir,
        host_family="codex",
        session_id=session_id,
        max_live_blocks=4,
        ambient_cap=3,
        include_assist=False,
        include_teaser=False,
    )
    developer_context = _parts(replay, developer_context) if replay else developer_context
    live_intervention = replay or live_intervention
    if bundle and decision is not None and developer_context:
        host_surface_runtime.append_visible_intervention_events(
            repo_root=project_dir,
            bundle=bundle,
            decision=decision,
            render_surface="codex_post_tool_use",
        )
    payload_out = host_surface_runtime.codex_post_tool_payload(
        developer_context=developer_context,
        system_message=host_surface_runtime.compose_checkpoint_system_message(
            live_intervention=live_intervention,
            governance_status=(governance_message or {}).get("systemMessage", ""),
        ),
    )
    if payload_out:
        sys.stdout.write(json.dumps(payload_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
