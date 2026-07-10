from __future__ import annotations

import errno
import importlib.util
import shutil
import subprocess
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
    assert env["ODYLITH_REASONING_TIMEOUT_SECONDS"] == "1"
    assert env["ODYLITH_REASONING_CODEX_BIN"] == "/usr/bin/false"
    assert env["ODYLITH_REASONING_CLAUDE_BIN"] == "/usr/bin/false"
    assert env["ODYLITH_COMPASS_STANDUP_BACKGROUND_DISABLE"] == "1"
    assert env["ODYLITH_NO_BROWSER"] == "1"
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
    assert env["ODYLITH_REASONING_TIMEOUT_SECONDS"] == "1"
    assert env["ODYLITH_REASONING_CODEX_BIN"] == "/usr/bin/false"
    assert env["ODYLITH_REASONING_CLAUDE_BIN"] == "/usr/bin/false"
    assert env["ODYLITH_COMPASS_STANDUP_BACKGROUND_DISABLE"] == "1"
    assert env["ODYLITH_NO_BROWSER"] == "1"


def test_cleanup_smoke_temp_root_retries_enotempty(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    module = _module()
    target = tmp_path / "release-smoke"
    (target / "upgrade-cycle" / ".odylith").mkdir(parents=True)
    (target / "upgrade-cycle" / ".odylith" / "runtime.json").write_text("{}", encoding="utf-8")
    calls: list[bool] = []
    real_rmtree = shutil.rmtree

    def flaky_rmtree(path, *args, **kwargs):  # noqa: ANN001
        calls.append(bool(kwargs.get("ignore_errors")))
        if len(calls) == 1:
            raise OSError(errno.ENOTEMPTY, "Directory not empty")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(module.shutil, "rmtree", flaky_rmtree)

    module._cleanup_smoke_temp_root(target)

    assert not target.exists()
    assert calls[0] is False
    assert len(calls) >= 2


def test_cleanup_smoke_temp_root_removes_post_success_runtime_residue(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    module = _module()
    target = tmp_path / "release-smoke"
    (target / ".odylith" / "compass").mkdir(parents=True)
    (target / ".odylith" / "compass" / "standup-brief-cache.v25.json").write_text("{}", encoding="utf-8")
    real_rmtree = shutil.rmtree
    calls = 0

    def rmtree_then_recreate(path, *args, **kwargs):  # noqa: ANN001
        nonlocal calls
        calls += 1
        result = real_rmtree(path, *args, **kwargs)
        if calls == 1:
            (target / ".odylith" / "locks" / "odylith-context-engine").mkdir(parents=True)
            (target / ".odylith" / "locks" / "odylith-context-engine" / "late.lock").write_text(
                "",
                encoding="utf-8",
            )
        return result

    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(module.shutil, "rmtree", rmtree_then_recreate)

    module._cleanup_smoke_temp_root(target)

    assert not target.exists()
    assert calls >= 2


def test_cleanup_smoke_temp_root_swallows_persistent_cleanup_noise(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    module = _module()
    target = tmp_path / "release-smoke"
    (target / "upgrade-cycle" / ".odylith").mkdir(parents=True)
    calls: list[bool] = []

    def always_fail(path, *args, **kwargs):  # noqa: ANN001
        calls.append(bool(kwargs.get("ignore_errors")))
        if kwargs.get("ignore_errors"):
            return None
        raise OSError(errno.ENOTEMPTY, "Directory not empty")

    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(module.shutil, "rmtree", always_fail)

    module._cleanup_smoke_temp_root(target)

    assert calls[-1] is True


def test_previous_release_is_published_treats_404_as_missing(monkeypatch) -> None:
    module = _module()

    def fake_fetch_release(**kwargs):  # noqa: ANN001
        raise HTTPError("https://example.invalid", 404, "Not Found", hdrs=None, fp=None)

    monkeypatch.setattr(module, "fetch_release", fake_fetch_release)

    assert module._previous_release_is_published(version="0.1.5") is False


def test_previous_release_is_published_treats_wrapped_404_as_missing(monkeypatch) -> None:
    module = _module()

    def fake_fetch_release(**kwargs):  # noqa: ANN001
        raise ValueError("failed to fetch release metadata: HTTP Error 404: Not Found")

    monkeypatch.setattr(module, "fetch_release", fake_fetch_release)

    assert module._previous_release_is_published(version="0.0.0") is False


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


def test_run_reports_timeout_with_command_and_cwd(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    module = _module()

    def fake_run(*args, **kwargs):  # noqa: ANN001
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=300, output="out", stderr="err")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    try:
        module._run(cwd=tmp_path, env={}, command=["odylith", "sync", "--force"])
    except RuntimeError as exc:
        message = str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("timeout should raise RuntimeError")

    assert "command timed out after" in message
    assert "odylith sync --force" in message
    assert f"cwd: {tmp_path}" in message
    assert "out" in message
    assert "err" in message


def test_greenfield_propose_apply_smoke_runs_exact_release_journey(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    odylith = repo_root / ".odylith" / "bin" / "odylith"
    commands: list[tuple[str, ...]] = []

    for relative_path in (
        "odylith/radar/radar.html",
        "odylith/registry/registry.html",
        "odylith/atlas/atlas.html",
        "odylith/compass/compass.html",
        "odylith/casebook/casebook.html",
        "odylith/runtime/source/accepted-project.v1.json",
        "odylith/runtime/delivery_intelligence.v4.json",
        "odylith/radar/traceability-graph.v1.json",
    ):
        path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok\n", encoding="utf-8")

    def fake_run(**kwargs):  # noqa: ANN001
        command = tuple(str(part) for part in kwargs["command"])
        commands.append(command)

        class Result:
            if "show" in command:
                stdout = "Odylith read this repo: no application source was found.\n"
            elif "propose" in command and "--confirm-intent" not in command:
                stdout = (
                    '{\n'
                    '  "mode": "product_intent_reasoning_request",\n'
                    '  "write_policy": "host_reason_product_intent_before_confirmed_greenfield_create",\n'
                    '  "host_reasoning_task": {"must_not": []}\n'
                    '}\n'
                )
            elif "propose" in command:
                stdout = (
                    '{\n'
                    '  "mode": "host_reasoned_greenfield_proposal",\n'
                    '  "backlog": [],\n'
                    '  "components": [],\n'
                    '  "diagrams": []\n'
                    '}\n'
                )
            elif "compile-transaction" in command:
                stdout = (
                    '{\n'
                    '  "mode": "product_create_transaction",\n'
                    '  "product_create_transaction": {"transaction_hash": "unit-transaction-hash"}\n'
                    '}\n'
                )
            elif "create" in command:
                stdout = (
                    '{\n'
                    '  "mode": "applied",\n'
                    '  "validation_gate": {"passed": true},\n'
                    '  "dashboard_refresh": {"status": "passed"}\n'
                    '}\n'
                )
            else:
                stdout = "dashboard refresh completed\n- outcome: passed\n"

        return Result()

    monkeypatch.setattr(module, "_run", fake_run)

    module._greenfield_propose_apply_smoke(repo_root=repo_root, odylith=odylith, env={"ODYLITH_VERSION": "0.1.15"})

    assert commands == [
        (str(odylith), "show", "--repo-root", "."),
        (
            str(odylith),
            "greenfield",
            "propose",
            "--repo-root",
            ".",
            "--prompt",
            "warehouse dispatch planning app",
            "--format",
            "json",
        ),
        (
            str(odylith),
            "greenfield",
            "propose",
            "--repo-root",
            ".",
            "--prompt",
            "warehouse dispatch planning app",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--confirm-intent",
            "--format",
            "json",
        ),
        (
            str(odylith),
            "greenfield",
            "compile-transaction",
            "--repo-root",
            ".",
            "--prompt",
            "warehouse dispatch planning app",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--output",
            ".odylith/runtime/greenfield/product-create-transaction.v1.json",
            "--release",
            "0.0.1",
            "--format",
            "json",
        ),
        (
            str(odylith),
            "greenfield",
            "create",
            "--repo-root",
            ".",
            "--transaction-file",
            ".odylith/runtime/greenfield/product-create-transaction.v1.json",
            "--transaction-hash",
            "unit-transaction-hash",
            "--confirm",
            "--json",
        ),
    ]


def _write_greenfield_guidance(repo_root: Path, text: str) -> None:
    module = _module()
    for relative_path in module._GREENFIELD_GUIDANCE_FILES:
        path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def test_release_smoke_requires_installed_greenfield_guidance_uses_confirmed_create(tmp_path: Path) -> None:
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_greenfield_guidance(
        repo_root,
        "Use project-first Product Intent Confirmation before confirmed create. Include a sectioned Product story, State object, First complete path, Proof boundary, and never collapse it into a wall of prose. Write the same visible accepted Product Intent Confirmation to .odylith/runtime/greenfield/confirmed-intent.md. Run odylith greenfield compile-transaction --repo-root . --prompt '<request>' --intent-file .odylith/runtime/greenfield/confirmed-intent.md --output .odylith/runtime/greenfield/product-create-transaction.v1.json --release 0.0.1 from the same confirmation. Odylith may normalize that confirmation into .odylith/runtime/greenfield/confirmed-intent.json, builds and quality-gates the ProductCreateTransaction, and waits for hash confirmation. Run odylith greenfield create --repo-root . --transaction-file .odylith/runtime/greenfield/product-create-transaction.v1.json --transaction-hash <hash> --confirm to commit; confirmed create verifies the compiler receipt, hash, and repo preconditions, writes only sealed bytes under rollback guard, and validates readback. Do not inspect Odylith source after confirmation. Do not narrate parser/schema retries or intermediate transaction-compile failures. Do not ask the operator to inspect proposal JSON.\n",
    )

    module._require_greenfield_guidance_uses_confirmed_create(repo_root=repo_root, label="unit")

    (repo_root / "AGENTS.md").write_text(
        "Use Product Intent Confirmation before proposal expansion. Include the product story. The host authors an internal proposal payload and uses odylith greenfield apply from the same confirmation. Do not inspect Odylith source after confirmation. Do not ask the operator to inspect proposal JSON. host model drafts\n",
        encoding="utf-8",
    )
    try:
        module._require_greenfield_guidance_uses_confirmed_create(repo_root=repo_root, label="unit")
    except RuntimeError as exc:
        assert "stale greenfield schema-repair flow" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("stale installed guidance should fail release smoke")


def test_release_smoke_rejects_maintainer_restrictions_in_consumer_guidance(tmp_path: Path) -> None:
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    for relative_path in module._CONSUMER_GUIDANCE_FILES:
        path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Consumer guidance follows this repo's own Git identity.\n", encoding="utf-8")
    for relative_dir in module._CONSUMER_GUIDANCE_DIRECTORIES:
        path = repo_root / relative_dir / "README.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Consumer guidance follows this repo's own Git policy and native validation.\n", encoding="utf-8")

    module._require_no_maintainer_restrictions_in_consumer_guidance(repo_root=repo_root, label="unit")

    (repo_root / "CLAUDE.md").write_text(
        "Commit messages must use only the `freedom-research` contributor identity and must not include coding-assistant trailers.\n",
        encoding="utf-8",
    )
    try:
        module._require_no_maintainer_restrictions_in_consumer_guidance(repo_root=repo_root, label="unit")
    except RuntimeError as exc:
        assert "consumer surface leaks maintainer-only restriction" in str(exc)
        assert "CLAUDE.md" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("consumer guidance with maintainer identity should fail release smoke")

    (repo_root / "CLAUDE.md").write_text("Consumer guidance follows this repo's own Git identity.\n", encoding="utf-8")
    leak = repo_root / "odylith" / "agents-guidelines" / "VALIDATION_AND_TESTING.md"
    leak.write_text("In this repo, never work directly on `main`; run make release-preflight before release.\n", encoding="utf-8")
    try:
        module._require_no_maintainer_restrictions_in_consumer_guidance(repo_root=repo_root, label="unit")
    except RuntimeError as exc:
        assert "consumer surface leaks maintainer-only restriction" in str(exc)
        assert "odylith/agents-guidelines/VALIDATION_AND_TESTING.md" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("consumer guidance with maintainer branch or release rule should fail release smoke")

    leak.write_text("Consumer guidance follows this repo's own Git policy and native validation.\n", encoding="utf-8")
    (repo_root / "odylith" / "runtime" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "runtime" / "source" / "release-metadata.v1.json").write_text(
        '{"owner": "freedom-research"}\n',
        encoding="utf-8",
    )
    try:
        module._require_no_maintainer_restrictions_in_consumer_guidance(repo_root=repo_root, label="unit")
    except RuntimeError as exc:
        assert "consumer surface leaks maintainer-only restriction" in str(exc)
        assert "odylith/runtime/source/release-metadata.v1.json" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("consumer runtime source with maintainer identity should fail release smoke")


def test_bundled_consumer_guidance_has_no_maintainer_restrictions(tmp_path: Path) -> None:
    module = _module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    shutil.copytree(REPO_ROOT / "src" / "odylith" / "bundle" / "assets" / "project-root", repo_root, dirs_exist_ok=True)
    bundled_odylith = REPO_ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith"
    shutil.copytree(bundled_odylith, repo_root / "odylith", dirs_exist_ok=True)

    module._require_no_maintainer_restrictions_in_consumer_guidance(repo_root=repo_root, label="bundle")


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
    monkeypatch.setattr(module, "_stale_uninstall_residue_cycle", lambda **kwargs: events.append("stale-residue"))
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
    monkeypatch.setattr(module, "_stale_uninstall_residue_cycle", lambda **kwargs: events.append("stale-residue"))
    monkeypatch.setattr(module, "_previous_release_is_published", lambda **kwargs: True)

    rc = module.main(["--version", "0.1.6", "--dist-dir", str(dist_dir)])

    assert rc == 0
    assert events == ["install", "upgrade", "stale-residue", "shutdown", "server_close"]


def test_main_runs_all_explicit_previous_versions(monkeypatch, tmp_path: Path) -> None:
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
    monkeypatch.setattr(module, "_upgrade_cycle", lambda **kwargs: events.append(f"upgrade:{kwargs['previous_version']}"))
    monkeypatch.setattr(
        module,
        "_stale_uninstall_residue_cycle",
        lambda **kwargs: events.append(f"stale-residue:{kwargs['previous_version']}"),
    )
    monkeypatch.setattr(module, "_previous_release_is_published", lambda **kwargs: True)

    rc = module.main(
        [
            "--version",
            "0.1.15",
            "--dist-dir",
            str(dist_dir),
            "--previous-version",
            "0.1.10",
            "--previous-version",
            "0.1.14",
        ]
    )

    assert rc == 0
    assert events == [
        "install",
        "upgrade:0.1.10",
        "stale-residue:0.1.10",
        "upgrade:0.1.14",
        "stale-residue:0.1.14",
        "shutdown",
        "server_close",
    ]


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
