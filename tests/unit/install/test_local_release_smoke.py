from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from urllib.error import HTTPError


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _module():
    return _load_module(SCRIPTS_ROOT / "local_release_smoke.py", "local_release_smoke")


def test_local_release_env_forces_deterministic_reasoning(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("ODYLITH_REASONING_MODE", "auto")
    monkeypatch.setenv("ODYLITH_REASONING_PROVIDER", "codex-cli")

    module = _module()
    env = module._local_release_env(base_url="http://127.0.0.1:8123", version="0.1.6")

    assert env["ODYLITH_RELEASE_BASE_URL"] == "http://127.0.0.1:8123"
    assert env["ODYLITH_RELEASE_MAINTAINER_ROOT"] == str(module.REPO_ROOT)
    assert env["ODYLITH_REASONING_MODE"] == "disabled"
    assert env["ODYLITH_REASONING_PROVIDER"] == "auto-local"
    assert env["ODYLITH_VERSION"] == "0.1.6"


def test_force_deterministic_reasoning_env_overrides_exported_provider() -> None:
    module = _module()

    env = module._force_deterministic_reasoning_env(
        {
            "ODYLITH_REASONING_MODE": "auto",
            "ODYLITH_REASONING_PROVIDER": "codex-cli",
        }
    )

    assert env["ODYLITH_REASONING_MODE"] == "disabled"
    assert env["ODYLITH_REASONING_PROVIDER"] == "auto-local"


def test_previous_release_is_published_treats_404_as_missing(monkeypatch) -> None:
    module = _module()

    def fake_fetch_release(**kwargs):  # noqa: ANN001
        raise HTTPError("https://example.invalid", 404, "Not Found", hdrs=None, fp=None)

    monkeypatch.setattr(module, "fetch_release", fake_fetch_release)

    assert module._previous_release_is_published(version="0.1.5") is False


def test_previous_release_is_published_returns_true_when_release_exists(monkeypatch) -> None:
    module = _module()

    seen: dict[str, object] = {}

    def fake_fetch_release(**kwargs):  # noqa: ANN001
        seen.update(kwargs)
        return object()

    monkeypatch.setattr(module, "fetch_release", fake_fetch_release)

    assert module._previous_release_is_published(version="0.1.5") is True
    assert seen["repo"] == "odylith/odylith"
    assert seen["version"] == "0.1.5"


def test_main_skips_upgrade_cycle_when_previous_release_missing(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "install.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")

    events: list[str] = []

    class _DummyServer:
        def shutdown(self) -> None:
            events.append("shutdown")

        def server_close(self) -> None:
            events.append("server_close")

    monkeypatch.setattr(module, "_serve_directory", lambda directory: (_DummyServer(), "http://127.0.0.1:8123"))
    monkeypatch.setattr(module, "_install_and_smoke", lambda **kwargs: events.append("install"))
    monkeypatch.setattr(module, "_upgrade_cycle", lambda **kwargs: events.append("upgrade"))
    monkeypatch.setattr(module, "_previous_release_is_published", lambda **kwargs: False)

    rc = module.main(["--version", "0.1.6", "--dist-dir", str(dist_dir)])

    assert rc == 0
    assert events == ["install", "shutdown", "server_close"]


def test_main_runs_upgrade_cycle_when_previous_release_exists(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "install.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")

    events: list[str] = []

    class _DummyServer:
        def shutdown(self) -> None:
            events.append("shutdown")

        def server_close(self) -> None:
            events.append("server_close")

    monkeypatch.setattr(module, "_serve_directory", lambda directory: (_DummyServer(), "http://127.0.0.1:8123"))
    monkeypatch.setattr(module, "_install_and_smoke", lambda **kwargs: events.append("install"))
    monkeypatch.setattr(module, "_upgrade_cycle", lambda **kwargs: events.append("upgrade"))
    monkeypatch.setattr(module, "_previous_release_is_published", lambda **kwargs: True)

    rc = module.main(["--version", "0.1.6", "--dist-dir", str(dist_dir)])

    assert rc == 0
    assert events == ["install", "upgrade", "shutdown", "server_close"]


def test_upgrade_cycle_proves_dashboard_refresh_after_each_target_activation(
    monkeypatch, tmp_path: Path
) -> None:
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    install_script = tmp_path / "install.sh"
    install_script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")

    commands: list[tuple[str, ...]] = []
    history_checks: list[str] = []

    def fake_run(**kwargs):  # noqa: ANN001
        command = tuple(str(part) for part in kwargs["command"])
        commands.append(command)

        class Result:
            stdout = ""

        return Result()

    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(module, "_install_cwd", lambda root: root)
    monkeypatch.setattr(module, "_seed_legacy_compass_archive_fixture", lambda **kwargs: history_checks.append("seed"))
    monkeypatch.setattr(module, "_require_compass_history_layout", lambda **kwargs: history_checks.append("check"))

    module._upgrade_cycle(
        repo_root=repo_root,
        install_script=install_script,
        previous_version="0.1.10",
        target_version="0.1.11",
        local_env={"ODYLITH_VERSION": "0.1.11"},
    )

    dashboard_commands = [
        command
        for command in commands
        if "dashboard" in command and "refresh" in command
    ]
    assert len(dashboard_commands) == 3
    assert all(command[-3:] == ("refresh", "--repo-root", ".") for command in dashboard_commands)
    assert history_checks == ["seed", "check", "seed", "check", "seed", "check"]
    assert sum(1 for command in commands if command == ("bash", str(install_script))) == 4


def test_install_clean_previous_release_resets_generated_install_state(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    install_script = tmp_path / "install.sh"
    install_script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    for relative_path in (".odylith", "odylith", ".agents", ".claude"):
        path = repo_root / relative_path
        path.mkdir()
        (path / "stale").write_text("stale\n", encoding="utf-8")
    (repo_root / "AGENTS.md").write_text("stale agent guidance\n", encoding="utf-8")

    seen: list[dict[str, object]] = []

    def fake_run(**kwargs):  # noqa: ANN001
        seen.append(kwargs)
        for relative_path in (".odylith", "odylith", ".agents", ".claude"):
            assert not (repo_root / relative_path).exists()

        class Result:
            stdout = ""

        return Result()

    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(module, "_install_cwd", lambda root: root)

    module._install_clean_previous_release(
        repo_root=repo_root,
        install_script=install_script,
        previous_version="0.1.10",
    )

    assert seen
    assert seen[0]["command"] == ["bash", str(install_script)]
    assert seen[0]["env"]["ODYLITH_VERSION"] == "0.1.10"
    assert (repo_root / "AGENTS.md").read_text(encoding="utf-8") == "# Repo Root\n\nLocal release smoke repo.\n"


def test_compass_history_layout_check_rejects_legacy_archive(tmp_path: Path) -> None:
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    module._seed_legacy_compass_archive_fixture(repo_root=repo_root)

    try:
        module._require_compass_history_layout(repo_root=repo_root)
    except RuntimeError as exc:
        assert "archive metadata was not cleared" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("legacy Compass archive fixture should fail the release-smoke layout check")


def test_compass_history_layout_check_accepts_cleared_archive(tmp_path: Path) -> None:
    module = _module()
    repo_root = tmp_path / "repo"
    history_dir = repo_root / "odylith" / "compass" / "runtime" / "history"
    history_dir.mkdir(parents=True)
    (history_dir / "index.v1.json").write_text(
        '{"version":"v1","retention_days":15,"dates":[],"restored_dates":[],"archive":{"compressed":false,"path":"","count":0,"dates":[],"newest_date":"","oldest_date":""}}\n',
        encoding="utf-8",
    )

    module._require_compass_history_layout(repo_root=repo_root)
