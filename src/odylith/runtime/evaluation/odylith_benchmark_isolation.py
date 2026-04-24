"""Odylith Benchmark Isolation helpers for the Odylith evaluation layer."""

from __future__ import annotations

import contextlib
import errno
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Iterator, Mapping, Sequence

from odylith.runtime.reasoning import odylith_reasoning


_TEMPORARY_DIRECTORY_CLEANUP_RETRYABLE_ERRNOS = frozenset({errno.ENOTEMPTY, errno.EBUSY, errno.EPERM})
_TEMPORARY_DIRECTORY_CLEANUP_RETRY_COUNT = 4
_TEMPORARY_DIRECTORY_CLEANUP_RETRY_DELAY_SECONDS = 0.05
_BENCHMARK_TOOL_SUPPORT_MODULES = ("pytest", "httpx")
_BENCHMARK_TOOL_SUPPORT_CACHE: dict[str, bool] = {}
_BENCHMARK_TOOL_BIN_CACHE: dict[str, Path] = {}
_HARDLINK_COPY_FALLBACK_ERRNOS = frozenset(
    {
        errno.EXDEV,
        errno.EPERM,
        errno.ENOTSUP,
        getattr(errno, "EOPNOTSUPP", errno.ENOTSUP),
    }
)


def _python_supports_benchmark_tools(python_path: Path) -> bool:
    resolved_python = Path(python_path).resolve()
    cache_key = str(resolved_python)
    cached = _BENCHMARK_TOOL_SUPPORT_CACHE.get(cache_key)
    if cached is not None:
        return cached
    try:
        completed = subprocess.run(
            [
                str(resolved_python),
                "-c",
                (
                    "import importlib.util; "
                    f"mods={_BENCHMARK_TOOL_SUPPORT_MODULES!r}; "
                    "raise SystemExit(0 if all(importlib.util.find_spec(m) is not None for m in mods) else 1)"
                ),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        _BENCHMARK_TOOL_SUPPORT_CACHE[cache_key] = False
        return False
    supported = int(completed.returncode or 0) == 0
    _BENCHMARK_TOOL_SUPPORT_CACHE[cache_key] = supported
    return supported


def benchmark_tool_bin(*, repo_root: Path) -> Path:
    root = Path(repo_root).resolve()
    cache_key = f"{root}::{Path(sys.executable).resolve()}"
    cached = _BENCHMARK_TOOL_BIN_CACHE.get(cache_key)
    if cached is not None:
        return cached

    local_bin = (root / ".venv" / "bin").resolve()
    local_python = local_bin / "python"
    if local_bin.is_dir() and not local_python.exists():
        _BENCHMARK_TOOL_BIN_CACHE[cache_key] = local_bin
        return local_bin

    candidates: list[Path] = []
    seen_candidates: set[str] = set()
    for candidate in (
        local_python,
        Path(sys.executable).resolve(),
        (Path(sys.prefix).resolve() / "bin" / Path(sys.executable).name).resolve(),
    ):
        token = str(candidate)
        if token in seen_candidates:
            continue
        seen_candidates.add(token)
        candidates.append(candidate)

    chosen: Path | None = None
    for candidate in candidates:
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            continue
        if _python_supports_benchmark_tools(candidate):
            chosen = candidate.parent.resolve()
            break

    if chosen is None:
        chosen = local_bin if local_bin.is_dir() else Path(sys.executable).resolve().parent
    _BENCHMARK_TOOL_BIN_CACHE[cache_key] = chosen
    return chosen


def _copy_file(source: Path, target: Path) -> None:
    source_path = Path(source)
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)


def _hardlink_or_copy_file(source: Path, target: Path) -> None:
    source_path = Path(source)
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(FileNotFoundError):
        target_path.unlink()
    try:
        os.link(source_path, target_path)
    except OSError as exc:
        if exc.errno not in _HARDLINK_COPY_FALLBACK_ERRNOS:
            raise
        shutil.copy2(source_path, target_path)


def _copy_tree_if_exists(*, source: Path, target: Path, prefer_hardlinks: bool = False) -> None:
    if not source.exists():
        return
    copy_function = _hardlink_or_copy_file if prefer_hardlinks else _copy_file
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True, copy_function=copy_function)
        return
    copy_function(source, target)


def provision_workspace_odylith_root(*, repo_root: Path, workspace_root: Path) -> None:
    source_root = (Path(repo_root).resolve() / ".odylith").resolve()
    if not source_root.exists():
        return
    target_root = (Path(workspace_root).resolve() / ".odylith").resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    for relative in (
        Path("bin"),
        Path("install.json"),
        Path("install-ledger.v1.jsonl"),
        Path("consumer-profile.json"),
        Path("reasoning.config.v1.json"),
        Path("runtime/odylith-benchmarks/latest.v1.json"),
        Path("runtime/odylith-benchmarks/latest-proof.v1.json"),
        Path("runtime/odylith-benchmarks/latest-diagnostic.v1.json"),
        Path("runtime/odylith-context-engine-state.v1.js"),
        Path("runtime/odylith-context-engine-state.v1.json"),
    ):
        _copy_tree_if_exists(source=source_root / relative, target=target_root / relative)
    for relative in (
        Path("runtime"),
        Path("runtime/bootstraps"),
        Path("runtime/current"),
        Path("runtime/odylith-benchmarks"),
        Path("runtime/odylith-compiler"),
        Path("runtime/odylith-memory"),
        Path("runtime/sessions"),
        Path("runtime/versions"),
        Path("locks"),
        Path("cache"),
        Path("cache/odylith-context-engine"),
        Path("cache/releases"),
        Path("subagent_orchestrator"),
        Path("subagent_orchestrator/decision-ledgers"),
        Path("compass"),
    ):
        (target_root / relative).mkdir(parents=True, exist_ok=True)


def _dedupe_relative_paths(paths: Sequence[Path]) -> list[Path]:
    seen: set[str] = set()
    rows: list[Path] = []
    for path in paths:
        token = path.as_posix()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(path)
    return rows


def _normalized_preserve_paths(values: Sequence[str]) -> set[str]:
    rows: set[str] = set()
    for raw in values:
        token = str(raw or "").strip().replace("\\", "/")
        if not token:
            continue
        while token.startswith("./"):
            token = token[2:]
        rows.add(Path(token).as_posix())
    return rows


def _normalized_allowed_paths(values: Sequence[str]) -> set[str]:
    rows: set[str] = set()
    for raw in values:
        token = str(raw or "").strip().replace("\\", "/")
        if not token:
            continue
        while token.startswith("./"):
            token = token[2:]
        rows.add(Path(token).as_posix().rstrip("/"))
    return rows


def _tracked_strip_file_paths(*, workspace_root: Path, strip_paths: Sequence[Path]) -> list[Path]:
    pathspecs = [path.as_posix() for path in strip_paths if path.as_posix()]
    if not pathspecs:
        return []
    completed = subprocess.run(
        ["git", "-C", str(Path(workspace_root).resolve()), "ls-files", "-z", "--", *pathspecs],
        text=False,
        capture_output=True,
        check=False,
    )
    if int(completed.returncode or 0) != 0:
        return []
    rows: list[Path] = []
    for raw_line in bytes(completed.stdout or b"").split(b"\0"):
        token = raw_line.decode("utf-8", errors="ignore").strip()
        if token:
            rows.append(Path(token))
    return _dedupe_relative_paths(rows)


def _mark_strip_paths_skip_worktree(*, workspace_root: Path, strip_paths: Sequence[Path]) -> None:
    tracked_files = _tracked_strip_file_paths(workspace_root=workspace_root, strip_paths=strip_paths)
    if not tracked_files:
        return
    subprocess.run(
        [
            "git",
            "-C",
            str(Path(workspace_root).resolve()),
            "update-index",
            "--skip-worktree",
            "--",
            *[path.as_posix() for path in tracked_files],
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def apply_workspace_strip_paths(*, workspace_root: Path, strip_paths: Sequence[Path]) -> None:
    _mark_strip_paths_skip_worktree(workspace_root=workspace_root, strip_paths=strip_paths)
    for relative_path in strip_paths:
        path = (workspace_root / relative_path).resolve()
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path)
            continue
        path.unlink()


def benchmark_workspace_parent(*, repo_root: Path, create: bool = True) -> Path:
    resolved_repo_root = Path(repo_root).resolve()
    root = (
        resolved_repo_root.parent
        / ".odylith-benchmark-worktrees"
        / f"{resolved_repo_root.name}-{hashlib.sha256(str(resolved_repo_root).encode('utf-8')).hexdigest()[:12]}"
    ).resolve()
    if create:
        root.mkdir(parents=True, exist_ok=True)
    return root


def cleanup_temporary_directory(path: Path) -> None:
    target = Path(path)
    last_error: OSError | None = None
    for attempt in range(_TEMPORARY_DIRECTORY_CLEANUP_RETRY_COUNT + 1):
        try:
            shutil.rmtree(target)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            last_error = exc
            if exc.errno not in _TEMPORARY_DIRECTORY_CLEANUP_RETRYABLE_ERRNOS:
                break
            if attempt >= _TEMPORARY_DIRECTORY_CLEANUP_RETRY_COUNT:
                break
            time.sleep(_TEMPORARY_DIRECTORY_CLEANUP_RETRY_DELAY_SECONDS)
    if last_error is None:
        return
    with contextlib.suppress(OSError, FileNotFoundError):
        shutil.rmtree(target, ignore_errors=True)


@contextlib.contextmanager
def temporary_workspace_checkout(
    repo_root: Path,
    *,
    strip_paths: Sequence[Path],
    snapshot_paths: Sequence[str],
) -> Iterator[tuple[Path, Path]]:
    root = Path(repo_root).resolve()
    temp_root = Path(
        tempfile.mkdtemp(
            prefix="odylith-benchmark-live-",
            dir=str(benchmark_workspace_parent(repo_root=root, create=True)),
        )
    ).resolve()
    try:
        workspace_root = (temp_root / "workspace").resolve()
        validator_truth_root = (temp_root / "validator-truth").resolve()
        subprocess.run(
            ["git", "clone", "--quiet", "--local", "--no-checkout", str(root), str(workspace_root)],
            cwd=str(root),
            text=True,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(workspace_root), "checkout", "--quiet", "--detach", "HEAD"],
            cwd=str(root),
            text=True,
            capture_output=True,
            check=True,
        )
        overlay_workspace_repo_snapshot(
            repo_root=root,
            workspace_root=workspace_root,
            allowed_paths=snapshot_paths,
        )
        provision_workspace_odylith_root(repo_root=root, workspace_root=workspace_root)
        capture_workspace_validator_truth(
            workspace_root=workspace_root,
            truth_root=validator_truth_root,
            strip_paths=strip_paths,
        )
        apply_workspace_strip_paths(workspace_root=workspace_root, strip_paths=strip_paths)
        yield workspace_root, validator_truth_root
    finally:
        cleanup_temporary_directory(temp_root)


_BENCHMARK_SELF_REFERENCE_ALLOWED_FAMILIES = frozenset(
    {
        "release_publication",
        "validation_heavy_fix",
    }
)
_BENCHMARK_SELF_REFERENCE_GLOBS: tuple[str, ...] = (
    ".odylith/runtime/odylith-benchmarks/**/*",
    "docs/benchmarks/**/*",
    "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
    "odylith/maintainer/skills/release-benchmark-publishing/**/*",
    "odylith/runtime/source/discipline-evaluation-corpus.v1.json",
    "odylith/runtime/source/guidance-behavior-evaluation-corpus.v1.json",
    "odylith/runtime/source/optimization-evaluation-corpus.v1.json",
    "src/odylith/bundle/assets/odylith/runtime/source/discipline-evaluation-corpus.v1.json",
    "src/odylith/bundle/assets/odylith/runtime/source/guidance-behavior-evaluation-corpus.v1.json",
    "src/odylith/bundle/assets/odylith/runtime/source/optimization-evaluation-corpus.v1.json",
    "src/odylith/runtime/evaluation/odylith_benchmark*.py",
    "src/odylith/runtime/reasoning/*.py",
    "tests/unit/runtime/test_odylith_benchmark*.py",
)


def _path_conflicts_with_preserved(*, relative_path: Path, preserved_paths: set[str]) -> bool:
    token = relative_path.as_posix().rstrip("/")
    if not token:
        return False
    return any(
        token == preserved
        or token.startswith(f"{preserved}/")
        or preserved.startswith(f"{token}/")
        for preserved in preserved_paths
    )


def scenario_workspace_self_reference_strip_paths(
    *,
    repo_root: Path,
    scenario: Mapping[str, object] | None,
    preserve_paths: Sequence[str] = (),
) -> list[Path]:
    family = str((scenario or {}).get("family", "")).strip()
    if family in _BENCHMARK_SELF_REFERENCE_ALLOWED_FAMILIES:
        return []
    root = Path(repo_root).resolve()
    preserved = _normalized_preserve_paths(preserve_paths)
    rows: list[Path] = []
    for pattern in _BENCHMARK_SELF_REFERENCE_GLOBS:
        rows.extend(
            path.relative_to(root)
            for path in root.glob(pattern)
            if path.exists() and path.is_file()
        )
    filtered = [
        path
        for path in _dedupe_relative_paths(rows)
        if not _path_conflicts_with_preserved(relative_path=path, preserved_paths=preserved)
    ]
    return sorted(filtered, key=lambda path: (len(path.parts), path.as_posix()), reverse=True)


def workspace_strip_paths(*, repo_root: Path, preserve_paths: Sequence[str] = ()) -> list[Path]:
    root = Path(repo_root).resolve()
    preserved = _normalized_preserve_paths(preserve_paths)
    rows = [
        path.relative_to(root)
        for pattern in ("AGENTS.md", "AGENTS.override.md", "CLAUDE.md", "CLAUDE.local.md", ".cursorrules", ".windsurfrules")
        for path in root.rglob(pattern)
    ]
    for name in (".cursor", ".windsurf", ".codex"):
        path = (root / name).resolve()
        if path.is_dir():
            rows.append(path.relative_to(root))
    filtered = [path for path in _dedupe_relative_paths(rows) if path.as_posix() not in preserved]
    return sorted(filtered, key=lambda path: (len(path.parts), path.as_posix()), reverse=True)


def _git_path_lines(*, repo_root: Path, command: Sequence[str]) -> list[Path]:
    completed = subprocess.run(
        list(command),
        cwd=str(Path(repo_root).resolve()),
        text=True,
        capture_output=True,
        check=False,
    )
    if int(completed.returncode or 0) != 0:
        return []
    rows: list[Path] = []
    for raw_line in str(completed.stdout or "").splitlines():
        token = str(raw_line or "").strip()
        if not token:
            continue
        rows.append(Path(token))
    return _dedupe_relative_paths(rows)


def _path_is_allowed(*, relative_path: Path, allowed_paths: set[str]) -> bool:
    if not allowed_paths:
        return True
    token = relative_path.as_posix().rstrip("/")
    for allowed in allowed_paths:
        if token == allowed or token.startswith(f"{allowed}/"):
            return True
    return False


def overlay_workspace_repo_snapshot(
    *,
    repo_root: Path,
    workspace_root: Path,
    allowed_paths: Sequence[str] = (),
) -> None:
    root = Path(repo_root).resolve()
    workspace = Path(workspace_root).resolve()
    allowed = _normalized_allowed_paths(allowed_paths)
    for allowed_token in sorted(allowed):
        relative_path = Path(allowed_token)
        token = relative_path.as_posix()
        if token == ".git" or token.startswith(".git/"):
            continue
        source = root / relative_path
        if source.is_dir():
            # Atlas and governance validators can watch whole directories. Mirror
            # allowed directory trees explicitly so empty or untracked children stay
            # visible inside the disposable benchmark workspace.
            _copy_tree_if_exists(source=source, target=workspace / relative_path)
            continue
        if source.is_file():
            # Runtime state under `.odylith/` is usually ignored by Git, so the
            # overlay must still copy explicitly allowed files even when Git
            # plumbing would never surface them as dirty or untracked paths.
            _copy_tree_if_exists(source=source, target=workspace / relative_path)
    copy_paths = _dedupe_relative_paths(
        [
            *_git_path_lines(
                repo_root=root,
                command=("git", "diff", "--name-only", "--diff-filter=ACMRTUXB", "HEAD", "--"),
            ),
            *_git_path_lines(
                repo_root=root,
                command=("git", "ls-files", "--others", "--exclude-standard"),
            ),
        ]
    )
    copy_paths = [path for path in copy_paths if _path_is_allowed(relative_path=path, allowed_paths=allowed)]
    delete_paths = _git_path_lines(
        repo_root=root,
        command=("git", "diff", "--name-only", "--diff-filter=D", "HEAD", "--"),
    )
    delete_paths = [path for path in delete_paths if _path_is_allowed(relative_path=path, allowed_paths=allowed)]
    for relative_path in copy_paths:
        token = relative_path.as_posix()
        if token.startswith(".git/"):
            continue
        _copy_tree_if_exists(source=root / relative_path, target=workspace / relative_path)
    for relative_path in delete_paths:
        target = (workspace / relative_path).resolve()
        if not target.exists():
            continue
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()


def capture_workspace_validator_truth(
    *,
    workspace_root: Path,
    truth_root: Path,
    strip_paths: Sequence[Path],
) -> None:
    workspace = Path(workspace_root).resolve()
    target_root = Path(truth_root).resolve()
    for relative_path in strip_paths:
        source = (workspace / relative_path).resolve()
        if not source.exists():
            continue
        _copy_tree_if_exists(
            source=source,
            target=target_root / relative_path,
            prefer_hardlinks=True,
        )


def restore_workspace_validator_truth(
    *,
    truth_root: Path,
    workspace_root: Path,
    strip_paths: Sequence[Path],
) -> None:
    root = Path(truth_root).resolve()
    workspace = Path(workspace_root).resolve()
    if not workspace.is_dir():
        return
    for relative_path in strip_paths:
        source = (root / relative_path).resolve()
        target = (workspace / relative_path).resolve()
        if not source.exists():
            continue
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        _copy_tree_if_exists(source=source, target=target)


def _host_playwright_browsers_path() -> str:
    explicit = str(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")).strip()
    candidates: list[Path] = []
    if explicit and explicit != "0":
        candidates.append(Path(explicit).expanduser())

    home = str(os.environ.get("HOME", "")).strip()
    if home:
        home_path = Path(home).expanduser()
        candidates.extend(
            [
                home_path / "Library" / "Caches" / "ms-playwright",
                home_path / ".cache" / "ms-playwright",
            ]
        )
    xdg_cache_home = str(os.environ.get("XDG_CACHE_HOME", "")).strip()
    if xdg_cache_home:
        candidates.append(Path(xdg_cache_home).expanduser() / "ms-playwright")

    for candidate in candidates:
        if candidate.is_dir():
            return str(candidate.resolve())
    return ""


def sandbox_process_env(
    *,
    repo_root: Path,
    execution_contract: Mapping[str, str],
    host_home_root: Path | None = None,
    codex_home_root: Path | None = None,
    sandbox_root: Path,
) -> dict[str, str]:
    repo_root = Path(repo_root).resolve()
    tool_bin = benchmark_tool_bin(repo_root=repo_root)
    local_venv_bin = (repo_root / ".venv" / "bin").resolve()
    provider = str(execution_contract.get("provider", "")).strip().lower()
    if provider == "claude-cli":
        resolved_host_bin = odylith_reasoning.resolve_claude_bin(
            str(execution_contract.get("claude_bin", "")).strip() or "claude"
        )
    else:
        resolved_host_bin = odylith_reasoning.resolve_codex_bin(
            str(execution_contract.get("codex_bin", "")).strip() or "codex"
        )
    resolved_host = shutil.which(resolved_host_bin) or (
        str(Path(resolved_host_bin).expanduser().resolve())
        if Path(resolved_host_bin).expanduser().exists()
        else ""
    )
    effective_home_root = Path(host_home_root or codex_home_root or sandbox_root).resolve()
    xdg_cache_home = (sandbox_root / "xdg-cache").resolve()
    xdg_config_home = (sandbox_root / "xdg-config").resolve()
    xdg_data_home = (sandbox_root / "xdg-data").resolve()
    xdg_state_home = (sandbox_root / "xdg-state").resolve()
    pycache_root = (sandbox_root / "pycache").resolve()
    python_user_base = (sandbox_root / "python-user-base").resolve()
    pip_cache = (sandbox_root / "pip-cache").resolve()
    uv_cache = (sandbox_root / "uv-cache").resolve()
    sqlite_home = (sandbox_root / "codex-sqlite").resolve()
    tmp_root = (sandbox_root / "tmp").resolve()
    pytest_tmp = (sandbox_root / "pytest-tmp").resolve()
    pytest_cache = (sandbox_root / "pytest-cache").resolve()
    git_config = (sandbox_root / "gitconfig").resolve()
    pip_config = (sandbox_root / "pip.conf").resolve()
    empty_env = (sandbox_root / "empty.env").resolve()
    tool_path = ":".join(
        dict.fromkeys(
            str(path)
            for path in (
                tool_bin,
                local_venv_bin if local_venv_bin != tool_bin else None,
                Path(resolved_host).resolve().parent if resolved_host else None,
                Path("/opt/homebrew/bin"),
                Path("/opt/homebrew/sbin"),
                Path("/usr/bin"),
                Path("/bin"),
                Path("/usr/sbin"),
                Path("/sbin"),
            )
            if path and Path(path).is_dir()
        )
    )
    for path in (
        xdg_cache_home,
        xdg_config_home,
        xdg_data_home,
        xdg_state_home,
        pycache_root,
        python_user_base,
        pip_cache,
        uv_cache,
        sqlite_home,
        tmp_root,
        pytest_tmp,
        pytest_cache,
    ):
        path.mkdir(parents=True, exist_ok=True)
    git_config.write_text("", encoding="utf-8")
    pip_config.write_text("[global]\ndisable-pip-version-check = true\nno-input = true\n", encoding="utf-8")
    empty_env.write_text("", encoding="utf-8")
    env = {
        "HOME": str(effective_home_root),
        "PATH": tool_path,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "LC_CTYPE": "C.UTF-8",
        "TERM": "dumb",
        "NO_COLOR": "1",
        "SHELL": "/bin/bash",
        "USER": str(os.environ.get("USER", "benchmark")),
        "LOGNAME": str(os.environ.get("LOGNAME", "benchmark")),
        "XDG_CACHE_HOME": str(xdg_cache_home),
        "XDG_CONFIG_HOME": str(xdg_config_home),
        "XDG_DATA_HOME": str(xdg_data_home),
        "XDG_STATE_HOME": str(xdg_state_home),
        "CODEX_SQLITE_HOME": str(sqlite_home),
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": "",
        "PYTHONPYCACHEPREFIX": str(pycache_root),
        "PYTHONUSERBASE": str(python_user_base),
        "PIP_CACHE_DIR": str(pip_cache),
        "PIP_CONFIG_FILE": str(pip_config),
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_INPUT": "1",
        "UV_CACHE_DIR": str(uv_cache),
        "TMPDIR": str(tmp_root),
        "TMP": str(tmp_root),
        "TEMP": str(tmp_root),
        "PYTEST_ADDOPTS": f"--basetemp={pytest_tmp} -o cache_dir={pytest_cache}",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(git_config),
        "GIT_PAGER": "cat",
        "GIT_TERMINAL_PROMPT": "0",
        "PAGER": "cat",
        "GH_PAGER": "cat",
        "BASH_ENV": str(empty_env),
        "ENV": str(empty_env),
    }
    if provider == "claude-cli":
        env["CLAUDE_CONFIG_DIR"] = str((effective_home_root / ".claude").resolve())
    else:
        env["CODEX_HOME"] = str((effective_home_root / ".codex").resolve())
    for key in ("CODEX_THREAD_ID", "CODEX_SHELL", "__CFBundleIdentifier"):
        value = str(os.environ.get(key, "")).strip()
        if value:
            env[key] = value
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"):
        value = str(os.environ.get(key, "")).strip()
        if value:
            env[key] = value
    playwright_browsers_path = _host_playwright_browsers_path()
    if playwright_browsers_path:
        env["PLAYWRIGHT_BROWSERS_PATH"] = playwright_browsers_path
    return env
