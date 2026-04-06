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
