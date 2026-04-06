from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "validate_git_identity.py"
EXPECTED_NAME = "freedom-research"
EXPECTED_EMAIL = "freedom@freedompreetham.org"


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_git_identity", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    _run("git", "init", str(repo), cwd=tmp_path)
    _run("git", "config", "user.name", EXPECTED_NAME, cwd=repo)
    _run("git", "config", "user.email", EXPECTED_EMAIL, cwd=repo)
    _run("git", "config", "user.useConfigOnly", "true", cwd=repo)
    (repo / "README.md").write_text("# Test\n", encoding="utf-8")
    _run("git", "add", "README.md", cwd=repo)
    _run("git", "commit", "-m", "init", cwd=repo)
    return repo


def test_config_validation_accepts_canonical_local_identity(tmp_path: Path) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)

    assert module.main(["config", "--repo-root", str(repo)]) == 0


def test_config_validation_rejects_wrong_local_email(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    _run("git", "config", "user.email", "wrong@example.com", cwd=repo)

    assert module.main(["config", "--repo-root", str(repo)]) == 1
    stderr = capsys.readouterr().err
    assert "local user.email must be" in stderr


def test_history_validation_rejects_noncanonical_commit_identity(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "someone-else",
        "GIT_AUTHOR_EMAIL": "bad@example.com",
        "GIT_COMMITTER_NAME": "someone-else",
        "GIT_COMMITTER_EMAIL": "bad@example.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "bad", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "author email must be" in stderr
    assert "committer email must be" in stderr
