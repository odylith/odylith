from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from typing import Mapping, Sequence

from odylith.runtime.reasoning import odylith_reasoning


def _copy_tree_if_exists(*, source: Path, target: Path) -> None:
    if not source.exists():
        return
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


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
    "odylith/runtime/source/optimization-evaluation-corpus.v1.json",
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
        if not source.exists() or source.is_dir():
            continue
        _copy_tree_if_exists(source=source, target=target_root / relative_path)


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
        if not source.exists() or source.is_dir():
            continue
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        _copy_tree_if_exists(source=source, target=target)


def sandbox_process_env(
    *,
    repo_root: Path,
    execution_contract: Mapping[str, str],
    codex_home_root: Path,
    sandbox_root: Path,
) -> dict[str, str]:
    repo_root = Path(repo_root).resolve()
    resolved_codex = shutil.which(odylith_reasoning.resolve_codex_bin(execution_contract.get("codex_bin", "codex")))
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
                (repo_root / ".venv" / "bin").resolve(),
                Path(resolved_codex).resolve().parent if resolved_codex else None,
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
        "HOME": str(codex_home_root),
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
    for key in ("CODEX_THREAD_ID", "CODEX_SHELL", "__CFBundleIdentifier"):
        value = str(os.environ.get(key, "")).strip()
        if value:
            env[key] = value
    return env
