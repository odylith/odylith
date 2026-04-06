from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _release_semver_module():
    return _load_module(
        SCRIPTS_ROOT / "release_semver.py",
        "release_semver",
    )


def _release_version_session_module():
    return _load_module(
        SCRIPTS_ROOT / "release_version_session.py",
        "release_version_session",
    )


def _show_release_version_state_module():
    return _load_module(
        SCRIPTS_ROOT / "show_release_version_state.py",
        "show_release_version_state",
    )


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    )


def _init_git_repo(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    _run("git", "init", "--bare", str(remote), cwd=tmp_path)
    _run("git", "init", str(repo), cwd=tmp_path)
    _run("git", "config", "user.name", "Odylith Tests", cwd=repo)
    _run("git", "config", "user.email", "odylith-tests@example.invalid", cwd=repo)
    (repo / "README.md").write_text("# Odylith Test Repo\n", encoding="utf-8")
    _run("git", "add", "README.md", cwd=repo)
    _run("git", "commit", "-m", "init", cwd=repo)
    _run("git", "branch", "-M", "main", cwd=repo)
    _run("git", "remote", "add", "origin", str(remote), cwd=repo)
    _run("git", "push", "-u", "origin", "main", cwd=repo)
    return repo, remote


def test_release_session_resolve_explicit_version_creates_tag_and_session(tmp_path: Path, monkeypatch) -> None:
    module = _release_version_session_module()
    repo, remote = _init_git_repo(tmp_path)
    monkeypatch.chdir(repo)

    session_file = repo / ".odylith" / "locks" / "release-session.json"
    exit_code = module.main(
        [
            "resolve",
            "--session-file",
            str(session_file),
            "--remote",
            "origin",
            "--target",
            "release-preflight",
            "--requested-version",
            "0.1.0",
        ]
    )

    assert exit_code == 0
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    assert payload["version"] == "0.1.0"
    assert payload["tag"] == "v0.1.0"
    assert payload["initialized_by_target"] == "release-preflight"
    assert payload["head_sha"] == _run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()

    remote_tags = _run("git", "--git-dir", str(remote), "tag", "-l", cwd=repo).stdout
    assert "v0.1.0" in remote_tags


def test_release_session_resolve_explicit_version_pushes_tag_when_branch_uses_same_name(
    tmp_path: Path, monkeypatch
) -> None:
    module = _release_version_session_module()
    repo, remote = _init_git_repo(tmp_path)
    monkeypatch.chdir(repo)

    _run("git", "checkout", "-b", "v0.1.0", cwd=repo)
    _run("git", "push", "-u", "origin", "v0.1.0", cwd=repo)
    _run("git", "checkout", "main", cwd=repo)

    session_file = repo / ".odylith" / "locks" / "release-session.json"
    exit_code = module.main(
        [
            "resolve",
            "--session-file",
            str(session_file),
            "--remote",
            "origin",
            "--target",
            "release-preflight",
            "--requested-version",
            "0.1.0",
        ]
    )

    assert exit_code == 0
    remote_tags = _run("git", "--git-dir", str(remote), "tag", "-l", cwd=repo).stdout.splitlines()
    remote_heads = _run("git", "--git-dir", str(remote), "branch", "--list", cwd=repo).stdout
    assert "v0.1.0" in remote_tags
    assert "v0.1.0" in remote_heads


def test_release_session_resolve_auto_tags_next_patch(tmp_path: Path, monkeypatch) -> None:
    module = _release_version_session_module()
    repo, remote = _init_git_repo(tmp_path)
    monkeypatch.chdir(repo)

    _run("git", "tag", "-a", "v0.1.0", "-m", "v0.1.0", cwd=repo)
    _run("git", "push", "origin", "v0.1.0", cwd=repo)
    session_file = repo / ".odylith" / "locks" / "release-session.json"

    exit_code = module.main(
        [
            "resolve",
            "--session-file",
            str(session_file),
            "--remote",
            "origin",
            "--target",
            "release-preflight",
        ]
    )

    assert exit_code == 0
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    assert payload["version"] == "0.1.1"
    assert payload["tag"] == "v0.1.1"

    remote_tags = _run("git", "--git-dir", str(remote), "tag", "-l", cwd=repo).stdout
    assert "v0.1.1" in remote_tags


def test_release_session_auto_tag_respects_source_version_floor(tmp_path: Path, monkeypatch) -> None:
    module = _release_version_session_module()
    repo, remote = _init_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    (repo / "pyproject.toml").write_text("[project]\nname='odylith'\nversion='0.1.0'\n", encoding="utf-8")

    session_file = repo / ".odylith" / "locks" / "release-session.json"
    exit_code = module.main(
        [
            "resolve",
            "--session-file",
            str(session_file),
            "--remote",
            "origin",
            "--target",
            "release-preflight",
        ]
    )

    assert exit_code == 0
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    assert payload["version"] == "0.1.0"
    assert payload["tag"] == "v0.1.0"

    remote_tags = _run("git", "--git-dir", str(remote), "tag", "-l", cwd=repo).stdout
    assert "v0.1.0" in remote_tags


def test_release_session_auto_tag_reuses_same_unpublished_tag_on_retry(tmp_path: Path, monkeypatch) -> None:
    module = _release_version_session_module()
    repo, remote = _init_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    (repo / "pyproject.toml").write_text("[project]\nname='odylith'\nversion='0.1.1'\n", encoding="utf-8")

    _run("git", "tag", "-a", "v0.1.1", "-m", "v0.1.1", cwd=repo)
    _run("git", "push", "origin", "v0.1.1", cwd=repo)
    monkeypatch.setattr(
        module.release_semver,
        "resolve_highest_published_release_tag",
        lambda **kwargs: ("v0.1.0", module.release_semver.parse_stable_semver("0.1.0")),
    )
    monkeypatch.setattr(module.release_semver, "published_release_exists", lambda **kwargs: False)

    session_file = repo / ".odylith" / "locks" / "release-session.json"
    exit_code = module.main(
        [
            "resolve",
            "--session-file",
            str(session_file),
            "--remote",
            "origin",
            "--target",
            "release-preflight",
        ]
    )

    assert exit_code == 0
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    assert payload["version"] == "0.1.1"
    assert payload["tag"] == "v0.1.1"

    remote_tags = _run("git", "--git-dir", str(remote), "tag", "-l", cwd=repo).stdout.splitlines()
    assert "v0.1.1" in remote_tags
    assert "v0.1.2" not in remote_tags


def test_release_session_rebinds_unpublished_tag_to_current_head_on_retry_after_fix(
    tmp_path: Path, monkeypatch
) -> None:
    module = _release_version_session_module()
    repo, remote = _init_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    (repo / "pyproject.toml").write_text("[project]\nname='odylith'\nversion='0.1.1'\n", encoding="utf-8")

    _run("git", "tag", "-a", "v0.1.1", "-m", "v0.1.1", cwd=repo)
    _run("git", "push", "origin", "v0.1.1", cwd=repo)

    (repo / "CHANGELOG.md").write_text("fix the blocker\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "fix blocker", cwd=repo)
    _run("git", "push", "origin", "main", cwd=repo)
    current_head = _run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()

    monkeypatch.setattr(
        module.release_semver,
        "resolve_highest_published_release_tag",
        lambda **kwargs: ("v0.1.0", module.release_semver.parse_stable_semver("0.1.0")),
    )
    monkeypatch.setattr(module.release_semver, "published_release_exists", lambda **kwargs: False)

    session_file = repo / ".odylith" / "locks" / "release-session.json"
    exit_code = module.main(
        [
            "resolve",
            "--session-file",
            str(session_file),
            "--remote",
            "origin",
            "--target",
            "release-preflight",
        ]
    )

    assert exit_code == 0
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    assert payload["version"] == "0.1.1"
    assert payload["tag"] == "v0.1.1"
    assert payload["head_sha"] == current_head

    remote_commit = (
        _run("git", "--git-dir", str(remote), "rev-list", "-n", "1", "v0.1.1^{commit}", cwd=repo)
        .stdout.strip()
    )
    assert remote_commit == current_head


def test_release_session_rejects_explicit_version_when_existing_tag_points_to_other_commit(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _release_version_session_module()
    repo, _remote = _init_git_repo(tmp_path)
    monkeypatch.chdir(repo)

    _run("git", "tag", "-a", "v0.1.0", "-m", "v0.1.0", cwd=repo)
    _run("git", "push", "origin", "v0.1.0", cwd=repo)
    (repo / "README.md").write_text("# Changed\n", encoding="utf-8")
    _run("git", "add", "README.md", cwd=repo)
    _run("git", "commit", "-m", "next", cwd=repo)
    _run("git", "push", "origin", "main", cwd=repo)

    session_file = repo / ".odylith" / "locks" / "release-session.json"
    exit_code = module.main(
        [
            "resolve",
            "--session-file",
            str(session_file),
            "--remote",
            "origin",
            "--target",
            "release-preflight",
            "--requested-version",
            "0.1.0",
        ]
    )

    assert exit_code == 2
    assert "bound to commit" in capsys.readouterr().err


def test_release_session_rejects_reuse_after_commit_drift(tmp_path: Path, monkeypatch, capsys) -> None:
    module = _release_version_session_module()
    repo, _remote = _init_git_repo(tmp_path)
    monkeypatch.chdir(repo)

    session_file = repo / ".odylith" / "locks" / "release-session.json"
    assert (
        module.main(
            [
                "resolve",
                "--session-file",
                str(session_file),
                "--remote",
                "origin",
                "--target",
                "release-preflight",
                "--requested-version",
                "0.1.0",
            ]
        )
        == 0
    )

    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "drift", cwd=repo)
    _run("git", "push", "origin", "main", cwd=repo)

    exit_code = module.main(
        [
            "resolve",
            "--session-file",
            str(session_file),
            "--remote",
            "origin",
            "--target",
            "release-dispatch",
            "--allow-session-init",
            "false",
        ]
    )

    assert exit_code == 2
    assert "invalidated because HEAD changed" in capsys.readouterr().err
    assert not session_file.exists()


def test_show_release_version_state_clears_stale_session(tmp_path: Path, monkeypatch, capsys) -> None:
    session_module = _release_version_session_module()
    show_module = _show_release_version_state_module()
    repo, _remote = _init_git_repo(tmp_path)
    monkeypatch.chdir(repo)

    session_file = repo / ".odylith" / "locks" / "release-session.json"
    assert (
        session_module.main(
            [
                "resolve",
                "--session-file",
                str(session_file),
                "--remote",
                "origin",
                "--target",
                "release-preflight",
                "--requested-version",
                "0.1.0",
            ]
        )
        == 0
    )

    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "drift", cwd=repo)
    _run("git", "push", "origin", "main", cwd=repo)

    exit_code = show_module.main(
        [
            "show",
            "--session-file",
            str(session_file),
            "--remote",
            "origin",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "active: no" in output
    assert "stale_cleared: yes" in output
    assert "stale_reason: active release session was invalidated because HEAD changed" in output
    assert not session_file.exists()


def test_show_release_version_state_reports_session_and_next_auto_version(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    session_module = _release_version_session_module()
    show_module = _show_release_version_state_module()
    repo, _remote = _init_git_repo(tmp_path)
    monkeypatch.chdir(repo)

    session_file = repo / ".odylith" / "locks" / "release-session.json"
    assert (
        session_module.main(
            [
                "resolve",
                "--session-file",
                str(session_file),
                "--remote",
                "origin",
                "--target",
                "release-preflight",
                "--requested-version",
                "0.1.0",
            ]
        )
        == 0
    )

    exit_code = show_module.main(
        [
            "show",
            "--session-file",
            str(session_file),
            "--remote",
            "origin",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "session_version: 0.1.0" in output
    assert "highest_published_release_tag: <none>" in output
    assert "next_auto_anchor: highest_tag" in output
    assert "next_auto_version: 0.1.1" in output


def test_show_release_version_state_prefers_highest_published_release_over_higher_unpublished_tags(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _release_version_session_module()
    show_module = _show_release_version_state_module()
    repo, _remote = _init_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    (repo / "pyproject.toml").write_text("[project]\nname='odylith'\nversion='0.1.3'\n", encoding="utf-8")

    session_file = repo / ".odylith" / "locks" / "release-session.json"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        show_module.release_semver,
        "resolve_highest_published_release_tag",
        lambda **kwargs: ("v0.1.2", module.release_semver.parse_stable_semver("0.1.2")),
    )
    monkeypatch.setattr(
        show_module.release_semver,
        "resolve_highest_semver_tag",
        lambda **kwargs: ("v0.1.5", module.release_semver.parse_stable_semver("0.1.5")),
    )

    exit_code = show_module.main(["show", "--session-file", str(session_file), "--remote", "origin"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "highest_published_release_tag: v0.1.2" in output
    assert "highest_semver_tag: v0.1.5" in output
    assert "next_auto_anchor: published_release" in output
    assert "next_auto_tag: v0.1.3" in output
    assert "next_auto_version: 0.1.3" in output


def test_show_release_version_state_applies_source_version_floor(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _show_release_version_state_module()
    repo, _remote = _init_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    (repo / "pyproject.toml").write_text("[project]\nname='odylith'\nversion='0.1.0'\n", encoding="utf-8")

    exit_code = module.main(["preview", "--remote", "origin"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "0.1.0"
