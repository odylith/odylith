import json
from pathlib import Path
from types import SimpleNamespace

from odylith import cli


class _TTYStream:
    def isatty(self) -> bool:
        return True


def _seed_first_run_surfaces(repo_root: Path) -> None:
    for relative_path in (
        Path("odylith/index.html"),
        Path("odylith/radar/radar.html"),
        Path("odylith/atlas/atlas.html"),
        Path("odylith/compass/compass.html"),
        Path("odylith/registry/registry.html"),
        Path("odylith/casebook/casebook.html"),
    ):
        output_path = repo_root / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("<!doctype html>\n", encoding="utf-8")


def _seed_first_run_surfaces_without_shell(repo_root: Path) -> None:
    for relative_path in (
        Path("odylith/radar/radar.html"),
        Path("odylith/atlas/atlas.html"),
        Path("odylith/compass/compass.html"),
        Path("odylith/registry/registry.html"),
        Path("odylith/casebook/casebook.html"),
    ):
        output_path = repo_root / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("<!doctype html>\n", encoding="utf-8")


def test_install_bootstraps_first_run_surfaces_and_reports_agent_workflow(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    refresh_capture: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
            gitignore_updated=True,
        ),
    )

    def fake_refresh_dashboard_surfaces(**kwargs) -> int:  # noqa: ANN003
        refresh_capture.update(kwargs)
        _seed_first_run_surfaces_without_shell(tmp_path)
        (tmp_path / "odylith" / "index.html").write_text("<!doctype html>\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", fake_refresh_dashboard_surfaces)

    rc = cli.main(["install", "--repo-root", str(tmp_path)])
    output = capsys.readouterr()

    assert rc == 0
    assert refresh_capture["repo_root"] == tmp_path.resolve()
    assert refresh_capture["surfaces"] == ("tooling_shell",)
    assert refresh_capture["runtime_mode"] == "auto"
    assert refresh_capture["atlas_sync"] is False
    assert refresh_capture["compass_refresh_profile"] == "shell-safe"
    assert "Odylith 1.2.3 is ready" in output.out
    assert "Rendering first-run Odylith surfaces" in output.out
    assert "Dashboard:" in output.out
    assert "Added `/.odylith/` to the root `.gitignore`" in output.out
    assert "Repo-root AGENTS now activates Odylith guidance, skills, and the Codex-native spawn path for most grounded work." in output.out
    assert "Full Odylith is installed by default." in output.out
    assert "later repairs and upgrades" in output.out
    assert "Odylith is used through an AI coding agent" in output.out
    assert "paste this starter prompt" in output.out
    assert "Starter prompt:" in output.out
    assert cli.shell_onboarding.STARTER_PROMPT in output.out
    assert "use `odylith/index.html` as the first-run Odylith launchpad" in output.out
    assert "doctor --repo-root . --repair" in output.out


def test_install_opens_dashboard_browser_on_successful_first_install(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    opened: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
        ),
    )
    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        lambda **kwargs: (_seed_first_run_surfaces_without_shell(tmp_path), (tmp_path / "odylith" / "index.html").write_text("<!doctype html>\n", encoding="utf-8"), 0)[2],
    )
    monkeypatch.setattr(cli, "_interactive_browser_launch_possible", lambda: True)
    monkeypatch.setattr(
        cli.webbrowser,
        "open",
        lambda url, new=0: opened.update({"url": url, "new": new}) or True,
    )

    rc = cli.main(["install", "--repo-root", str(tmp_path)])
    output = capsys.readouterr()

    assert rc == 0
    assert opened["url"] == (tmp_path / "odylith" / "index.html").resolve().as_uri()
    assert opened["new"] == 2
    assert "Opened `odylith/index.html` in your browser." in output.out


def test_install_no_open_flag_suppresses_browser_launch(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
        ),
    )
    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        lambda **kwargs: (_seed_first_run_surfaces_without_shell(tmp_path), (tmp_path / "odylith" / "index.html").write_text("<!doctype html>\n", encoding="utf-8"), 0)[2],
    )
    monkeypatch.setattr(cli, "_interactive_browser_launch_possible", lambda: True)

    def fail_open(url: str, new: int = 0) -> bool:
        raise AssertionError(f"browser should not open when --no-open is set: {url=} {new=}")

    monkeypatch.setattr(cli.webbrowser, "open", fail_open)

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--no-open"])
    output = capsys.readouterr()

    assert rc == 0
    assert "Opened `odylith/index.html` in your browser." not in output.out


def test_install_does_not_open_browser_when_not_first_install(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    install_state = tmp_path / ".odylith" / "install.json"
    install_state.parent.mkdir(parents=True, exist_ok=True)
    install_state.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
        ),
    )
    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        lambda **kwargs: (_seed_first_run_surfaces_without_shell(tmp_path), (tmp_path / "odylith" / "index.html").write_text("<!doctype html>\n", encoding="utf-8"), 0)[2],
    )
    monkeypatch.setattr(cli, "_interactive_browser_launch_possible", lambda: True)

    def fail_open(url: str, new: int = 0) -> bool:
        raise AssertionError(f"browser should not open on reinstall: {url=} {new=}")

    monkeypatch.setattr(cli.webbrowser, "open", fail_open)

    rc = cli.main(["install", "--repo-root", str(tmp_path)])
    output = capsys.readouterr()

    assert rc == 0
    assert "Odylith is already installed here on 1.2.3." in output.out
    assert "Opened `odylith/index.html` in your browser." not in output.out


def test_install_adopt_latest_reinstalls_and_updates_repo_pin(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    install_state = tmp_path / ".odylith" / "install.json"
    install_state.parent.mkdir(parents=True, exist_ok=True)
    install_state.write_text("{}\n", encoding="utf-8")
    _seed_first_run_surfaces(tmp_path)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
            gitignore_updated=True,
        ),
    )

    def fake_upgrade_install(
        *,
        repo_root: str,
        release_repo: str,
        version: str,
        source_repo: str | None = None,
        write_pin: bool,
    ) -> SimpleNamespace:
        captured["repo_root"] = repo_root
        captured["release_repo"] = release_repo
        captured["version"] = version
        captured["source_repo"] = source_repo
        captured["write_pin"] = write_pin
        return SimpleNamespace(
            active_version="1.2.4",
            previous_version="1.2.3",
            pinned_version="1.2.4",
            pin_changed=True,
            launcher_path=launcher_path,
            repo_role="consumer_repo",
            followed_latest=True,
            release_tag="v1.2.4",
            release_body="Sharper install messaging.\n\nCleaner shell onboarding.",
            release_highlights=("Sharper install messaging.", "Cleaner shell onboarding."),
            release_published_at="2026-03-30T14:00:00Z",
            release_url="https://example.com/releases/v1.2.4",
        )

    monkeypatch.setattr(cli, "upgrade_install", fake_upgrade_install)
    monkeypatch.setattr(cli, "_refresh_dashboard_after_upgrade", lambda **kwargs: (True, "Dashboard refreshed."))

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--adopt-latest"])
    output = capsys.readouterr()
    spotlight_payload = json.loads(
        (tmp_path / ".odylith" / "runtime" / "release-upgrade-spotlight.v1.json").read_text(encoding="utf-8")
    )

    assert rc == 0
    assert captured["repo_root"] == str(tmp_path)
    assert captured["release_repo"] == "odylith/odylith"
    assert captured["version"] == ""
    assert captured["source_repo"] is None
    assert captured["write_pin"] is True
    assert spotlight_payload["from_version"] == "1.2.3"
    assert spotlight_payload["to_version"] == "1.2.4"
    assert spotlight_payload["release_tag"] == "v1.2.4"
    assert spotlight_payload["highlights"] == ["Sharper install messaging.", "Cleaner shell onboarding."]
    assert "Odylith was reinstalled on the latest verified release: 1.2.4. Repo pin updated to match." in output.out
    assert "This reinstall flow keeps the managed runtime and the tracked repo pin aligned in one step." in output.out
    assert "Dashboard refreshed." in output.out
    assert "odylith-bootstrap doctor --repo-root . --repair" in output.out


def test_install_adopt_latest_keeps_first_install_free_of_upgrade_spotlight(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    _seed_first_run_surfaces(tmp_path)
    cli.write_upgrade_spotlight(
        repo_root=tmp_path,
        from_version="1.2.2",
        to_version="1.2.3",
        release_tag="v1.2.3",
        release_body="Stale spotlight payload.",
        highlights=("Should be cleared.",),
    )

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.2",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
            gitignore_updated=False,
        ),
    )
    monkeypatch.setattr(
        cli,
        "upgrade_install",
        lambda **kwargs: SimpleNamespace(
            active_version="1.2.3",
            previous_version="1.2.2",
            pinned_version="1.2.3",
            pin_changed=True,
            launcher_path=launcher_path,
            repo_role="consumer_repo",
            followed_latest=True,
            release_tag="v1.2.3",
            release_body="Upgrade body.",
            release_highlights=("Upgrade highlight.",),
            release_published_at="2026-03-30T14:00:00Z",
            release_url="https://example.com/releases/v1.2.3",
        ),
    )
    monkeypatch.setattr(cli, "_refresh_dashboard_after_upgrade", lambda **kwargs: (True, "Dashboard refreshed."))

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--adopt-latest", "--no-open"])
    output = capsys.readouterr().out

    assert rc == 0
    assert not (tmp_path / ".odylith" / "runtime" / "release-upgrade-spotlight.v1.json").exists()
    assert f"Odylith 1.2.3 is ready in {tmp_path / 'odylith'}." in output
    assert "Dashboard refreshed." in output


def test_install_adopt_latest_clears_stale_upgrade_spotlight_when_no_version_change(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    install_state = tmp_path / ".odylith" / "install.json"
    install_state.parent.mkdir(parents=True, exist_ok=True)
    install_state.write_text("{}\n", encoding="utf-8")
    _seed_first_run_surfaces(tmp_path)
    cli.write_upgrade_spotlight(
        repo_root=tmp_path,
        from_version="1.2.2",
        to_version="1.2.3",
        release_tag="v1.2.3",
        release_body="Old spotlight payload.",
        highlights=("Old highlight.",),
    )

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
            gitignore_updated=False,
        ),
    )
    monkeypatch.setattr(
        cli,
        "upgrade_install",
        lambda **kwargs: SimpleNamespace(
            active_version="1.2.3",
            previous_version="1.2.3",
            pinned_version="1.2.3",
            pin_changed=False,
            launcher_path=launcher_path,
            repo_role="consumer_repo",
            followed_latest=True,
            release_tag="",
            release_body="",
            release_highlights=(),
            release_published_at="",
            release_url="",
        ),
    )
    monkeypatch.setattr(cli, "_refresh_dashboard_after_upgrade", lambda **kwargs: (True, "Dashboard refreshed."))

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--adopt-latest", "--no-open"])
    output = capsys.readouterr().out

    assert rc == 0
    assert not (tmp_path / ".odylith" / "runtime" / "release-upgrade-spotlight.v1.json").exists()
    assert "Odylith was reinstalled on the latest verified release: 1.2.3. Repo pin updated to match." in output
    assert "Dashboard refreshed." in output


def test_reinstall_defaults_to_latest_verified_release(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    install_state = tmp_path / ".odylith" / "install.json"
    install_state.parent.mkdir(parents=True, exist_ok=True)
    install_state.write_text("{}\n", encoding="utf-8")
    _seed_first_run_surfaces(tmp_path)
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        cli,
        "reinstall_install",
        lambda **kwargs: captured.update(kwargs) or SimpleNamespace(
            active_version="1.2.4",
            previous_version="1.2.3",
            pinned_version="1.2.4",
            pin_changed=True,
            launcher_path=launcher_path,
            repaired=False,
            release_body="",
            release_highlights=(),
            release_published_at="",
            release_url="",
        ),
    )
    monkeypatch.setattr(cli, "_refresh_dashboard_after_upgrade", lambda **kwargs: (True, "Dashboard refreshed."))

    rc = cli.main(["reinstall", "--repo-root", str(tmp_path), "--latest", "--no-open"])
    output = capsys.readouterr().out

    assert rc == 0
    assert captured["version"] == ""
    assert captured["release_repo"] == "odylith/odylith"
    assert "Reinstalled Odylith from 1.2.3 to 1.2.4 and adopted the verified repo pin." in output
    assert "Repo pin updated to 1.2.4." in output
    assert "Dashboard refreshed." in output
    assert "odylith-bootstrap doctor --repo-root . --repair" in output


def test_install_dry_run_skips_install_bundle(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "plan_install_lifecycle",
        lambda **kwargs: SimpleNamespace(command="install", headline="preview", steps=(), dirty_overlap=(), notes=()),
    )
    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("install_bundle should not run during --dry-run")),
    )

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--dry-run"])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "install dry-run" in captured


def test_reinstall_dry_run_skips_reinstall_install(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "plan_reinstall_lifecycle",
        lambda **kwargs: SimpleNamespace(command="reinstall", headline="preview", steps=(), dirty_overlap=(), notes=()),
    )
    monkeypatch.setattr(
        cli,
        "reinstall_install",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("reinstall_install should not run during --dry-run")),
    )

    rc = cli.main(["reinstall", "--repo-root", str(tmp_path), "--dry-run"])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "reinstall dry-run" in captured


def test_upgrade_dry_run_skips_upgrade_install(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "plan_upgrade_lifecycle",
        lambda **kwargs: SimpleNamespace(command="upgrade", headline="preview", steps=(), dirty_overlap=(), notes=()),
    )
    monkeypatch.setattr(
        cli,
        "upgrade_install",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("upgrade_install should not run during --dry-run")),
    )

    rc = cli.main(["upgrade", "--repo-root", str(tmp_path), "--dry-run"])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "upgrade dry-run" in captured


def test_dashboard_refresh_dispatches_selected_surfaces(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "normalize_dashboard_surfaces",
        lambda values: ["tooling_shell", "radar", "atlas"],
    )

    def fake_refresh_dashboard_surfaces(**kwargs) -> int:  # noqa: ANN003
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        fake_refresh_dashboard_surfaces,
    )

    rc = cli.main(
        [
            "dashboard",
            "refresh",
            "--repo-root",
            str(tmp_path),
            "--surfaces",
            "shell,radar,atlas",
            "--atlas-sync",
            "--dry-run",
            "--runtime-mode",
            "standalone",
        ]
    )

    assert rc == 0
    assert captured["repo_root"] == tmp_path.resolve()
    assert captured["surfaces"] == ["tooling_shell", "radar", "atlas"]
    assert captured["runtime_mode"] == "standalone"
    assert captured["atlas_sync"] is True
    assert captured["dry_run"] is True


def test_dashboard_refresh_defaults_to_tooling_shell_radar_and_compass(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_refresh_dashboard_surfaces(**kwargs) -> int:  # noqa: ANN003
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        fake_refresh_dashboard_surfaces,
    )

    rc = cli.main(
        [
            "dashboard",
            "refresh",
            "--repo-root",
            str(tmp_path),
            "--dry-run",
        ]
    )

    assert rc == 0
    assert captured["repo_root"] == tmp_path.resolve()
    assert captured["surfaces"] == ["tooling_shell", "radar", "compass"]
    assert captured["runtime_mode"] == "auto"
    assert captured["atlas_sync"] is False
    assert captured["dry_run"] is True


def test_backlog_create_dispatches_to_backlog_authoring(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_backlog_main(argv: list[str]) -> int:
        captured["argv"] = list(argv)
        return 0

    monkeypatch.setattr(cli.backlog_authoring, "main", fake_backlog_main)

    rc = cli.main(
        [
            "backlog",
            "create",
            "--repo-root",
            str(tmp_path),
            "--title",
            "Fix backlog authoring",
            "--dry-run",
        ]
    )

    assert rc == 0
    assert captured["argv"] == [
        "--repo-root",
        str(tmp_path),
        "--title",
        "Fix backlog authoring",
        "--dry-run",
    ]


def test_validate_guidance_portability_dispatches_fast_path(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_validate_main(argv: list[str]) -> int:
        captured["argv"] = list(argv)
        return 0

    monkeypatch.setattr(cli.validate_guidance_portability, "main", fake_validate_main)

    rc = cli.main(["validate", "guidance-portability", "--repo-root", str(tmp_path)])

    assert rc == 0
    assert captured["argv"] == ["--repo-root", str(tmp_path)]


def test_validate_version_truth_dispatches_check_mode(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_validate_main(argv: list[str]) -> int:
        captured["argv"] = list(argv)
        return 0

    monkeypatch.setattr(cli.version_truth, "main", fake_validate_main)

    rc = cli.main(["validate", "version-truth", "--repo-root", str(tmp_path)])

    assert rc == 0
    assert captured["argv"] == ["--repo-root", str(tmp_path), "check"]


def test_interactive_browser_launch_possible_respects_env_opt_out(monkeypatch) -> None:
    monkeypatch.setattr(cli.sys, "stdout", _TTYStream())
    monkeypatch.setattr(cli.sys, "stderr", _TTYStream())
    monkeypatch.setattr(cli.sys, "platform", "darwin")
    monkeypatch.setenv("ODYLITH_NO_BROWSER", "1")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("BUILD_BUILDID", raising=False)
    monkeypatch.delenv("SSH_CONNECTION", raising=False)
    monkeypatch.delenv("SSH_CLIENT", raising=False)
    monkeypatch.delenv("SSH_TTY", raising=False)

    assert cli._interactive_browser_launch_possible() is False


def test_interactive_browser_launch_possible_blocks_headless_linux(monkeypatch) -> None:
    monkeypatch.setattr(cli.sys, "stdout", _TTYStream())
    monkeypatch.setattr(cli.sys, "stderr", _TTYStream())
    monkeypatch.setattr(cli.sys, "platform", "linux")
    monkeypatch.delenv("ODYLITH_NO_BROWSER", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("BUILD_BUILDID", raising=False)
    monkeypatch.delenv("SSH_CONNECTION", raising=False)
    monkeypatch.delenv("SSH_CLIENT", raising=False)
    monkeypatch.delenv("SSH_TTY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    assert cli._interactive_browser_launch_possible() is False


def test_format_bold_uses_ansi_in_tty(monkeypatch) -> None:
    monkeypatch.setattr(cli.sys, "stdout", _TTYStream())

    assert cli._format_bold("Starter prompt") == "\033[1mStarter prompt\033[0m"


def test_install_reports_created_guidance_and_non_git_caveat(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=True,
            git_repo_present=False,
            gitignore_updated=True,
        ),
    )
    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        lambda **kwargs: (_seed_first_run_surfaces_without_shell(tmp_path), (tmp_path / "odylith" / "index.html").write_text("<!doctype html>\n", encoding="utf-8"), 0)[2],
    )

    rc = cli.main(["install", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 0
    assert "Created root AGENTS.md" in captured.out
    assert "Added `/.odylith/` to the root `.gitignore`" in captured.out
    assert "This folder is not backed by Git yet." in captured.out
    assert "working-tree intelligence, background autospawn, and git-fsmonitor watcher help" in captured.out


def test_install_skips_surface_bootstrap_when_shell_already_exists(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    _seed_first_run_surfaces(tmp_path)

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
        ),
    )

    def fail_refresh_dashboard_surfaces(**kwargs) -> int:  # noqa: ANN003
        raise AssertionError(f"dashboard refresh should not run when first-run surfaces already exist: {kwargs}")

    monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", fail_refresh_dashboard_surfaces)

    rc = cli.main(["install", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 0
    assert "Rendering first-run Odylith surfaces" not in captured.out


def test_install_fails_when_first_run_shell_bootstrap_fails(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    sync_capture: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
        ),
    )

    def fail_refresh_dashboard_surfaces(**kwargs) -> int:  # noqa: ANN003
        return 17

    monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", fail_refresh_dashboard_surfaces)
    def fail_full_sync(argv: list[str]) -> int:
        sync_capture["argv"] = argv
        return 17

    monkeypatch.setattr(cli.sync_workstream_artifacts, "main", fail_full_sync)

    rc = cli.main(["install", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 17
    assert sync_capture["argv"] == [
        "--repo-root",
        str(tmp_path.resolve()),
        "--force",
        "--impact-mode",
        "full",
        "--compass-refresh-profile",
        "shell-safe",
    ]
    assert "Odylith runtime install succeeded, but the first-run Odylith shell is incomplete." in captured.err
    assert "odylith sync --repo-root . --force --impact-mode full" in captured.err


def test_sync_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 17

    monkeypatch.setattr(cli.sync_workstream_artifacts, "main", fake_main)
    rc = cli.main(["sync", "--repo-root", str(tmp_path), "--force", "--check-only"])
    assert rc == 17
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--force", "--check-only"]


def test_validate_backlog_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 19

    monkeypatch.setattr(cli.validate_backlog_contract, "main", fake_main)
    rc = cli.main(["validate", "backlog-contract", "--repo-root", str(tmp_path), "--check-only"])
    assert rc == 19
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--check-only"]


def test_validate_component_registry_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 21

    monkeypatch.setattr(cli.validate_component_registry_contract, "main", fake_main)
    rc = cli.main(["validate", "component-registry", "--repo-root", str(tmp_path), "--policy-mode", "advisory"])
    assert rc == 21
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--policy-mode", "advisory"]


def test_validate_component_registry_contract_alias_dispatch_accepts_plain_forwarded_flags(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 210

    monkeypatch.setattr(cli.validate_component_registry_contract, "main", fake_main)
    rc = cli.main(["validate", "component-registry-contract", "--repo-root", str(tmp_path), "--policy-mode", "advisory"])
    assert rc == 210
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--policy-mode", "advisory"]


def test_validate_plan_risk_mitigation_contract_alias_dispatch_accepts_plain_forwarded_flags(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 211

    monkeypatch.setattr(cli.validate_plan_risk_mitigation_contract, "main", fake_main)
    rc = cli.main(["validate", "plan-risk-mitigation-contract", "--repo-root", str(tmp_path), "--check-only"])
    assert rc == 211
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--check-only"]


def test_validate_self_host_posture_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 27

    monkeypatch.setattr(cli.validate_self_host_posture, "main", fake_main)
    rc = cli.main(
        [
            "validate",
            "self-host-posture",
            "--repo-root",
            str(tmp_path),
            "--mode",
            "release",
            "--expected-tag",
            "v0.1.0",
        ]
    )
    assert rc == 27
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--mode", "release", "--expected-tag", "v0.1.0"]


def test_governance_backfill_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 22

    monkeypatch.setattr(cli.backfill_workstream_traceability, "main", fake_main)
    rc = cli.main(
        [
            "governance",
            "backfill-workstream-traceability",
            "--repo-root",
            str(tmp_path),
            "--dry-run",
        ]
    )
    assert rc == 22
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--dry-run"]


def test_governance_reconcile_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 24

    monkeypatch.setattr(cli.reconcile_plan_workstream_binding, "main", fake_main)
    rc = cli.main(
        [
            "governance",
            "reconcile-plan-workstream-binding",
            "--repo-root",
            str(tmp_path),
            "odylith/technical-plans/in-progress/example.md",
        ]
    )
    assert rc == 24
    assert captured["argv"] == [
        "--repo-root",
        str(tmp_path),
        "odylith/technical-plans/in-progress/example.md",
    ]


def test_governance_sync_component_spec_requirements_dispatch_accepts_plain_forwarded_flags(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 25

    monkeypatch.setattr(cli.sync_component_spec_requirements, "main", fake_main)
    rc = cli.main(
        [
            "governance",
            "sync-component-spec-requirements",
            "--repo-root",
            str(tmp_path),
            "--component",
            "registry",
        ]
    )
    assert rc == 25
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--component", "registry"]


def test_governance_version_truth_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 251

    monkeypatch.setattr(cli.version_truth, "main", fake_main)
    rc = cli.main(["governance", "version-truth", "--repo-root", str(tmp_path)])
    assert rc == 251
    assert captured["argv"] == ["--repo-root", str(tmp_path), "check"]


def test_governance_validate_guidance_portability_dispatch_accepts_plain_forwarded_flags(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 252

    monkeypatch.setattr(cli.validate_guidance_portability, "main", fake_main)
    rc = cli.main(["governance", "validate-guidance-portability", "--repo-root", str(tmp_path), "--check-only"])
    assert rc == 252
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--check-only"]


def test_governance_validate_plan_traceability_dispatch_accepts_plain_forwarded_flags(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 253

    monkeypatch.setattr(cli.validate_plan_traceability_contract, "main", fake_main)
    rc = cli.main(["governance", "validate-plan-traceability", "--repo-root", str(tmp_path), "--check-only"])
    assert rc == 253
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--check-only"]


def test_benchmark_dispatch_preserves_argument_order(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 23

    monkeypatch.setattr(cli.odylith_context_engine, "main", fake_main)
    rc = cli.main(["benchmark", "--repo-root", str(tmp_path), "--output", "report.json"])
    assert rc == 23
    assert captured["argv"] == ["--repo-root", str(tmp_path), "benchmark", "--output", "report.json"]


def test_compass_update_dispatch_accepts_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 29

    monkeypatch.setattr(cli.update_compass, "main", fake_main)
    rc = cli.main(["compass", "update", "--repo-root", str(tmp_path), "--statement", "hello"])
    assert rc == 29
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--statement", "hello"]


def test_compass_restore_history_dispatch_accepts_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 31

    monkeypatch.setattr(cli.restore_compass_history, "main", fake_main)
    rc = cli.main(["compass", "restore-history", "--repo-root", str(tmp_path), "--date", "2026-03-01"])
    assert rc == 31
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--date", "2026-03-01"]


def test_compass_watch_transactions_dispatch_accepts_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 30

    monkeypatch.setattr(cli.watch_prompt_transactions, "main", fake_main)
    rc = cli.main(["compass", "watch-transactions", "--repo-root", str(tmp_path), "--once"])
    assert rc == 30
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--once"]


def test_doctor_uses_bundle_root(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_doctor_bundle(
        *,
        repo_root: str,
        bundle_root: Path,
        repair: bool,
        reset_local_state: bool,
    ) -> tuple[bool, str]:
        captured["repo_root"] = repo_root
        captured["bundle_root"] = bundle_root
        captured["repair"] = repair
        captured["reset_local_state"] = reset_local_state
        return True, "healthy"

    monkeypatch.setattr(cli, "doctor_bundle", fake_doctor_bundle)
    rc = cli.main(["doctor", "--repo-root", str(tmp_path)])
    assert rc == 0
    assert captured["repo_root"] == str(tmp_path)
    assert captured["repair"] is False
    assert captured["reset_local_state"] is False
    assert isinstance(captured["bundle_root"], Path)


def test_doctor_passes_reset_local_state(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_doctor_bundle(
        *,
        repo_root: str,
        bundle_root: Path,
        repair: bool,
        reset_local_state: bool,
    ) -> tuple[bool, str]:
        captured["repo_root"] = repo_root
        captured["repair"] = repair
        captured["reset_local_state"] = reset_local_state
        return True, "healthy"

    monkeypatch.setattr(cli, "doctor_bundle", fake_doctor_bundle)
    rc = cli.main(["doctor", "--repo-root", str(tmp_path), "--repair", "--reset-local-state"])
    assert rc == 0
    assert captured["repo_root"] == str(tmp_path)
    assert captured["repair"] is True
    assert captured["reset_local_state"] is True


def test_doctor_rejects_reset_without_repair(capsys, tmp_path: Path) -> None:
    rc = cli.main(["doctor", "--repo-root", str(tmp_path), "--reset-local-state"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "--reset-local-state requires --repair." in captured.err


def test_on_uses_set_agents_integration(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_set_agents_integration(*, repo_root: str, enabled: bool) -> tuple[bool, str]:
        captured["repo_root"] = repo_root
        captured["enabled"] = enabled
        return True, "on"

    monkeypatch.setattr(cli, "set_agents_integration", fake_set_agents_integration)
    rc = cli.main(["on", "--repo-root", str(tmp_path)])
    assert rc == 0
    assert captured["repo_root"] == str(tmp_path)
    assert captured["enabled"] is True


def test_off_uses_set_agents_integration(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_set_agents_integration(*, repo_root: str, enabled: bool) -> tuple[bool, str]:
        captured["repo_root"] = repo_root
        captured["enabled"] = enabled
        return True, "off"

    monkeypatch.setattr(cli, "set_agents_integration", fake_set_agents_integration)
    rc = cli.main(["off", "--repo-root", str(tmp_path)])
    assert rc == 0
    assert captured["repo_root"] == str(tmp_path)
    assert captured["enabled"] is False


def test_on_prints_bootstrap_guidance(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(cli, "set_agents_integration", lambda **kwargs: (True, "on"))

    rc = cli.main(["on", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 0
    assert "Repo guidance is active again. Start from the repo-local Odylith entrypoint before default repo-scan behavior." in captured.out
    assert "./.odylith/bin/odylith start --repo-root ." in captured.out
    assert "./.odylith/bin/odylith context --repo-root . <ref>" in captured.out


def test_start_bootstrap_lane_emits_payload(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "evaluate_start_preflight",
        lambda **kwargs: SimpleNamespace(
            lane="bootstrap",
            reason="healthy",
            next_command="./.odylith/bin/odylith start --repo-root .",
            healthy=True,
            launcher_exists=True,
            bootstrap_launcher_exists=True,
            install_shape_present=True,
            status=None,
        ),
    )
    monkeypatch.setattr(
        cli,
        "_start_bootstrap_payload",
        lambda args: {
            "packet_kind": "bootstrap_session",
            "narrowing_guidance": {"required": False, "reason": "grounded"},
        },
    )

    rc = cli.main(["start", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "- lane: bootstrap" in captured
    assert '"packet_kind": "bootstrap_session"' in captured


def test_start_fallback_lane_prints_exact_next_command(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "evaluate_start_preflight",
        lambda **kwargs: SimpleNamespace(
            lane="bootstrap",
            reason="healthy",
            next_command="./.odylith/bin/odylith start --repo-root .",
            healthy=True,
            launcher_exists=True,
            bootstrap_launcher_exists=True,
            install_shape_present=True,
            status=None,
        ),
    )
    monkeypatch.setattr(
        cli,
        "_start_bootstrap_payload",
        lambda args: {
            "packet_kind": "bootstrap_session",
            "narrowing_guidance": {
                "required": True,
                "reason": "Need one code path.",
                "next_fallback_command": "rg --files | rg 'src/odylith/cli.py'",
                "next_fallback_followup": "sed -n '1,200p' src/odylith/cli.py",
            },
        },
    )

    rc = cli.main(["start", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 1
    assert "- lane: fallback" in captured
    assert "- next: rg --files | rg 'src/odylith/cli.py'" in captured
    assert "- followup: sed -n '1,200p' src/odylith/cli.py" in captured
    assert "- lane: bootstrap" not in captured


def test_start_status_only_routes_to_version(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "evaluate_start_preflight",
        lambda **kwargs: SimpleNamespace(
            lane="status",
            reason="status only",
            next_command="./.odylith/bin/odylith version --repo-root .",
            healthy=True,
            launcher_exists=True,
            bootstrap_launcher_exists=True,
            install_shape_present=True,
            status=None,
        ),
    )
    monkeypatch.setattr(
        cli,
        "version_status",
        lambda **kwargs: SimpleNamespace(
            repo_root=tmp_path,
            repo_role="consumer_repo",
            posture="pinned_release",
            runtime_source="pinned_runtime",
            release_eligible=True,
            context_engine_mode="local",
            context_engine_pack_installed=True,
            pinned_version="1.2.3",
            active_version="1.2.3",
            last_known_good_version="1.2.3",
            detached=False,
            diverged_from_pin=False,
            available_versions=["1.2.3"],
        ),
    )

    rc = cli.main(["start", "--repo-root", str(tmp_path), "--status-only"])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "- lane: status" in captured
    assert "Runtime interpreter: Odylith is using the managed Odylith Python runtime." in captured


def test_start_install_lane_prints_hosted_installer(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "evaluate_start_preflight",
        lambda **kwargs: SimpleNamespace(
            lane="install",
            reason="not installed",
            next_command="curl -fsSL https://github.com/odylith/odylith/releases/latest/download/install.sh | bash",
            healthy=False,
            launcher_exists=False,
            bootstrap_launcher_exists=False,
            install_shape_present=False,
            status=None,
        ),
    )

    rc = cli.main(["start", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 1
    assert "- lane: install" in captured
    assert "curl -fsSL https://github.com/odylith/odylith/releases/latest/download/install.sh | bash" in captured


def test_start_bootstrap_exception_prints_repair_guidance(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "evaluate_start_preflight",
        lambda **kwargs: SimpleNamespace(
            lane="bootstrap",
            reason="healthy",
            next_command="./.odylith/bin/odylith start --repo-root .",
            healthy=True,
            launcher_exists=True,
            bootstrap_launcher_exists=True,
            install_shape_present=True,
            status=None,
        ),
    )
    monkeypatch.setattr(cli, "_start_bootstrap_payload", lambda args: (_ for _ in ()).throw(RuntimeError("projection cache corrupted")))
    monkeypatch.setattr(cli, "preferred_repair_entrypoint", lambda **kwargs: "./.odylith/bin/odylith doctor --repo-root . --repair")

    rc = cli.main(["start", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 1
    assert "- lane: fallback" in captured
    assert "projection cache corrupted" in captured
    assert "- next: ./.odylith/bin/odylith doctor --repo-root . --repair" in captured
    assert "- followup: ./.odylith/bin/odylith bootstrap --repo-root . --no-working-tree" in captured


def test_bootstrap_shortcut_exception_prints_repair_guidance(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "_dispatch_context_engine_shortcut",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("context engine daemon unavailable")),
    )
    monkeypatch.setattr(cli, "preferred_repair_entrypoint", lambda **kwargs: "./.odylith/bin/odylith doctor --repo-root . --repair")

    rc = cli.main(["bootstrap", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 1
    assert "odylith bootstrap" in captured
    assert "context engine daemon unavailable" in captured
    assert "- next: ./.odylith/bin/odylith doctor --repo-root . --repair" in captured
    assert "- followup: ./.odylith/bin/odylith bootstrap --repo-root . --no-working-tree" in captured


def test_version_reports_runtime_toolchain_boundary(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "version_status",
        lambda **kwargs: SimpleNamespace(
            repo_root=tmp_path,
            repo_role="consumer_repo",
            posture="pinned_release",
            runtime_source="pinned_runtime",
            release_eligible=True,
            context_engine_mode="local",
            context_engine_pack_installed=True,
            pinned_version="1.2.3",
            active_version="1.2.3",
            last_known_good_version="1.2.3",
            detached=False,
            diverged_from_pin=False,
            available_versions=["1.2.3"],
        ),
    )

    rc = cli.main(["version", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "Runtime interpreter: Odylith is using the managed Odylith Python runtime." in captured
    assert "Repo-code validation: use the repo's own project toolchain for application tests, builds, and linting." in captured


def test_off_prints_default_behavior_guidance(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(cli, "set_agents_integration", lambda **kwargs: (True, "off"))

    rc = cli.main(["off", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 0
    assert "Codex falls back to the surrounding repo's default behavior" in captured.out
    assert "./.odylith/bin/odylith on --repo-root ." in captured.out
    assert "runtime and `odylith/` context stay installed" in captured.out


def test_bootstrap_shortcut_defaults_to_clean_first_turn_command(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli.odylith_context_engine,
        "main",
        lambda argv: captured.update({"argv": argv}) or 0,
    )

    rc = cli.main(["bootstrap", "--repo-root", str(tmp_path)])

    assert rc == 0
    assert captured["argv"] == ["--repo-root", str(tmp_path), "bootstrap-session", "--working-tree"]


def test_context_shortcut_dispatches_to_context_engine(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli.odylith_context_engine,
        "main",
        lambda argv: captured.update({"argv": argv}) or 0,
    )

    rc = cli.main(["context", "--repo-root", str(tmp_path), "odylith"])

    assert rc == 0
    assert captured["argv"] == ["--repo-root", str(tmp_path), "context", "odylith"]


def test_query_shortcut_dispatches_to_context_engine(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli.odylith_context_engine,
        "main",
        lambda argv: captured.update({"argv": argv}) or 0,
    )

    rc = cli.main(["query", "--repo-root", str(tmp_path), "launchpad"])

    assert rc == 0
    assert captured["argv"] == ["--repo-root", str(tmp_path), "query", "launchpad"]


def test_upgrade_dispatches_to_upgrade_install(monkeypatch, tmp_path: Path, capsys) -> None:
    captured: dict[str, object] = {}
    refresh_capture: dict[str, object] = {}

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")

    def fake_upgrade_install(
        *,
        repo_root: str,
        release_repo: str,
        version: str,
        source_repo: str | None,
        write_pin: bool,
    ) -> SimpleNamespace:
        captured["repo_root"] = repo_root
        captured["release_repo"] = release_repo
        captured["version"] = version
        captured["source_repo"] = source_repo
        captured["write_pin"] = write_pin
        return SimpleNamespace(
            active_version="1.2.3",
            launcher_path=Path(repo_root) / ".odylith" / "bin" / "odylith",
            pin_changed=False,
            pinned_version="1.2.3",
            previous_version="1.2.2",
            repo_role="consumer_repo",
            followed_latest=False,
            release_tag="v1.2.3",
            release_body="## Highlights\n\nSharper install messaging.\n\nCleaner shell onboarding.",
            release_highlights=("Sharper install messaging.", "Cleaner shell onboarding."),
            release_published_at="2026-03-28T12:30:00Z",
            release_url="https://example.com/releases/v1.2.3",
        )

    monkeypatch.setattr(cli, "upgrade_install", fake_upgrade_install)

    def fake_refresh_dashboard_after_upgrade(*, repo_root: Path) -> tuple[bool, str]:
        refresh_capture["repo_root"] = repo_root
        print("Refreshing Odylith dashboard surfaces so the local shell reflects the new release.")
        return True, "Dashboard refreshed. Open `odylith/index.html` to see what landed in this release."

    monkeypatch.setattr(
        cli,
        "_refresh_dashboard_after_upgrade",
        fake_refresh_dashboard_after_upgrade,
    )

    rc = cli.main(["upgrade", "--repo-root", str(repo_root), "--to", "1.2.3", "--write-pin"])
    output = capsys.readouterr().out
    spotlight_payload = json.loads((repo_root / ".odylith" / "runtime" / "release-upgrade-spotlight.v1.json").read_text(encoding="utf-8"))

    assert rc == 0
    assert captured["repo_root"] == str(repo_root)
    assert captured["release_repo"] == "odylith/odylith"
    assert captured["version"] == "1.2.3"
    assert captured["source_repo"] is None
    assert captured["write_pin"] is True
    assert refresh_capture["repo_root"] == repo_root
    assert spotlight_payload["from_version"] == "1.2.2"
    assert spotlight_payload["to_version"] == "1.2.3"
    assert spotlight_payload["release_tag"] == "v1.2.3"
    assert spotlight_payload["release_body"] == "## Highlights\n\nSharper install messaging.\n\nCleaner shell onboarding."
    assert spotlight_payload["highlights"] == ["Sharper install messaging.", "Cleaner shell onboarding."]
    assert "Upgraded Odylith from 1.2.2 to 1.2.3." in output
    assert "Repo pin remains 1.2.3." in output
    assert "Release: https://example.com/releases/v1.2.3" in output
    assert "Published: 2026-03-28 12:30 UTC" in output
    assert "What changed:" in output
    assert "- Sharper install messaging." in output
    assert "Refreshing Odylith dashboard surfaces so the local shell reflects the new release." in output
    assert "Dashboard refreshed. Open `odylith/index.html` to see what landed in this release." in output


def test_migrate_legacy_install_dispatches_to_install_migration(monkeypatch, tmp_path: Path, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_migrate_legacy_install(*, repo_root: str) -> SimpleNamespace:
        captured["repo_root"] = repo_root
        return SimpleNamespace(
            already_migrated=False,
            state_root=tmp_path / ".odylith",
            launcher_path=tmp_path / ".odylith" / "bin" / "odylith",
            moved_paths=("odyssey/ -> odylith/", ".odyssey/ -> .odylith/"),
            removed_paths=(".odylith/runtime/odylith-memory",),
        )

    monkeypatch.setattr(cli, "migrate_legacy_install", fake_migrate_legacy_install)

    rc = cli.main(["migrate-legacy-install", "--repo-root", str(tmp_path)])
    output = capsys.readouterr().out

    assert rc == 0
    assert captured["repo_root"] == str(tmp_path)
    assert "Migrated legacy install state into" in output
    assert "odyssey/ -> odylith/" in output
    assert ".odyssey/ -> .odylith/" in output
    assert ".odylith/runtime/odylith-memory" in output
    assert "./.odylith/bin/odylith start --repo-root ." in output


def test_upgrade_reports_already_latest_verified_release(monkeypatch, tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    refresh_capture: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "upgrade_install",
        lambda **kwargs: SimpleNamespace(
            active_version="1.2.3",
            launcher_path=repo_root / ".odylith" / "bin" / "odylith",
            pin_changed=False,
            pinned_version="1.2.3",
            previous_version="1.2.3",
            repo_role="consumer_repo",
            followed_latest=True,
            release_body="",
            release_highlights=(),
            release_published_at="",
            release_url="",
        ),
    )
    monkeypatch.setattr(
        cli,
        "_refresh_dashboard_after_upgrade",
        lambda **kwargs: refresh_capture.update(kwargs) or (True, "Dashboard refreshed."),
    )

    rc = cli.main(["upgrade", "--repo-root", str(repo_root)])
    output = capsys.readouterr().out

    assert rc == 0
    assert refresh_capture["repo_root"] == repo_root
    assert "Odylith is already on the latest verified release: 1.2.3." in output
    assert "Repo pin remains 1.2.3." in output
    assert "Dashboard refreshed." in output


def test_upgrade_reports_already_on_tracked_self_host_pin(monkeypatch, tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    refresh_capture: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "upgrade_install",
        lambda **kwargs: SimpleNamespace(
            active_version="1.2.3",
            launcher_path=repo_root / ".odylith" / "bin" / "odylith",
            pin_changed=False,
            pinned_version="1.2.3",
            previous_version="1.2.3",
            repo_role="product_repo",
            followed_latest=False,
            release_body="",
            release_highlights=(),
            release_published_at="",
            release_url="",
        ),
    )
    monkeypatch.setattr(
        cli,
        "_refresh_dashboard_after_upgrade",
        lambda **kwargs: refresh_capture.update(kwargs) or (True, "Dashboard refreshed."),
    )

    rc = cli.main(["upgrade", "--repo-root", str(repo_root)])
    output = capsys.readouterr().out

    assert rc == 0
    assert refresh_capture["repo_root"] == repo_root
    assert "Odylith is already on the tracked self-host pin: 1.2.3." in output
    assert "Repo pin remains 1.2.3." in output
    assert "Dashboard refreshed." in output


def test_upgrade_refreshes_dashboard_for_product_repo_version_change_without_consumer_popup(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    refresh_capture: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "upgrade_install",
        lambda **kwargs: SimpleNamespace(
            active_version="1.2.4",
            launcher_path=repo_root / ".odylith" / "bin" / "odylith",
            pin_changed=False,
            pinned_version="1.2.4",
            previous_version="1.2.3",
            repo_role="product_repo",
            followed_latest=False,
            release_tag="v1.2.4",
            release_body="",
            release_highlights=(),
            release_published_at="",
            release_url="",
        ),
    )
    monkeypatch.setattr(
        cli,
        "_refresh_dashboard_after_upgrade",
        lambda **kwargs: refresh_capture.update(kwargs) or (True, "Dashboard refreshed."),
    )

    rc = cli.main(["upgrade", "--repo-root", str(repo_root), "--to", "1.2.4"])
    output = capsys.readouterr().out

    assert rc == 0
    assert refresh_capture["repo_root"] == repo_root
    assert "Upgraded Odylith from 1.2.3 to 1.2.4." in output
    assert "Dashboard refreshed." in output


def test_rollback_dispatches_to_previous(monkeypatch, tmp_path: Path, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_rollback_install(*, repo_root: str) -> SimpleNamespace:
        captured["repo_root"] = repo_root
        return SimpleNamespace(
            active_version="1.2.2",
            diverged_from_pin=True,
            launcher_path=Path(repo_root) / ".odylith" / "bin" / "odylith",
            pinned_version="1.2.3",
            previous_version="1.2.3",
        )

    monkeypatch.setattr(cli, "rollback_install", fake_rollback_install)

    rc = cli.main(["rollback", "--repo-root", str(tmp_path), "--previous"])
    output = capsys.readouterr().out

    assert rc == 0
    assert captured["repo_root"] == str(tmp_path)
    assert "Odylith rolled back from 1.2.3 to 1.2.2." in output
    assert "diverges from repo pin 1.2.3" in output


def test_version_reports_pinned_and_available(monkeypatch, tmp_path: Path, capsys) -> None:
    def fake_version_status(*, repo_root: str) -> SimpleNamespace:
        return SimpleNamespace(
            repo_root=Path(repo_root),
            repo_role="product_repo",
            posture="pinned_release",
            runtime_source="pinned_runtime",
            release_eligible=True,
            context_engine_mode="full_local_memory",
            context_engine_pack_installed=True,
            pinned_version="1.2.3",
            active_version="1.2.2",
            last_known_good_version="1.2.2",
            detached=False,
            diverged_from_pin=True,
            available_versions=["1.2.2", "1.2.3"],
        )

    monkeypatch.setattr(cli, "version_status", fake_version_status)

    rc = cli.main(["version", "--repo-root", str(tmp_path)])
    output = capsys.readouterr().out

    assert rc == 0
    assert f"Repo root: {tmp_path}" in output
    assert "Repo role: product_repo" in output
    assert "Posture: pinned_release" in output
    assert "Runtime source: pinned_runtime" in output
    assert "Release eligible: yes" in output
    assert "Context engine mode: full_local_memory" in output
    assert "Context engine pack: installed" in output
    assert "Pinned: 1.2.3" in output
    assert "Active: 1.2.2" in output
    assert "Diverged from pin: yes" in output
    assert "Available: 1.2.2, 1.2.3" in output



def test_subagent_router_dispatch_accepts_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 31

    monkeypatch.setattr(cli.subagent_router, "main", fake_main)
    rc = cli.main(["subagent-router", "--repo-root", str(tmp_path), "show-tuning", "--json"])
    assert rc == 31
    assert captured["argv"] == ["show-tuning", "--repo-root", str(tmp_path), "--json"]


def test_subagent_orchestrator_dispatch_accepts_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 37

    monkeypatch.setattr(cli.subagent_orchestrator, "main", fake_main)
    rc = cli.main(["subagent-orchestrator", "--repo-root", str(tmp_path), "show-tuning", "--json"])
    assert rc == 37
    assert captured["argv"] == ["show-tuning", "--repo-root", str(tmp_path), "--json"]


def test_subagent_router_help_does_not_receive_injected_repo_root(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 0

    monkeypatch.setattr(cli.subagent_router, "main", fake_main)
    rc = cli.main(["subagent-router", "--repo-root", str(tmp_path), "--help"])

    assert rc == 0
    assert captured["argv"] == ["--help"]


def test_subagent_orchestrator_help_does_not_receive_injected_repo_root(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 0

    monkeypatch.setattr(cli.subagent_orchestrator, "main", fake_main)
    rc = cli.main(["subagent-orchestrator", "--repo-root", str(tmp_path), "--help"])

    assert rc == 0
    assert captured["argv"] == ["--help"]


def test_atlas_render_dispatch_accepts_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 41

    monkeypatch.setattr(cli.render_mermaid_catalog, "main", fake_main)
    rc = cli.main(["atlas", "render", "--repo-root", str(tmp_path), "--fail-on-stale"])
    assert rc == 41
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--fail-on-stale"]


def test_atlas_auto_update_dispatch_accepts_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 43

    monkeypatch.setattr(cli.auto_update_mermaid_diagrams, "main", fake_main)
    rc = cli.main(["atlas", "auto-update", "--repo-root", str(tmp_path), "--all-stale"])
    assert rc == 43
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--all-stale"]


def test_sync_help_uses_parser_without_running_sync(monkeypatch, tmp_path: Path, capsys) -> None:
    def fail(*args, **kwargs) -> int:  # noqa: ANN002, ANN003
        raise AssertionError("sync main should not run for --help")

    monkeypatch.setattr(cli.sync_workstream_artifacts, "main", fail)

    try:
        cli.main(["sync", "--repo-root", str(tmp_path), "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("expected argparse help exit")

    assert "usage: odylith sync" in capsys.readouterr().out


def test_governance_help_uses_parser_without_running_subcommand(monkeypatch, tmp_path: Path, capsys) -> None:
    def fail(argv: list[str]) -> int:
        raise AssertionError(f"governance subcommand should not run for --help: {argv}")

    monkeypatch.setattr(cli.version_truth, "main", fail)

    try:
        cli.main(["governance", "version-truth", "--repo-root", str(tmp_path), "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("expected argparse help exit")

    assert "usage: odylith governance version-truth" in capsys.readouterr().out


def test_validate_help_uses_parser_without_running_subcommand(monkeypatch, tmp_path: Path, capsys) -> None:
    def fail(argv: list[str]) -> int:
        raise AssertionError(f"validate subcommand should not run for --help: {argv}")

    monkeypatch.setattr(cli.validate_component_registry_contract, "main", fail)

    try:
        cli.main(["validate", "component-registry-contract", "--repo-root", str(tmp_path), "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("expected argparse help exit")

    assert "usage: odylith validate component-registry-contract" in capsys.readouterr().out


def test_lane_status_help_uses_parser_without_running_status(monkeypatch, tmp_path: Path, capsys) -> None:
    def fail(argv: list[str]) -> int:
        raise AssertionError(f"lane status should not run for --help: {argv}")

    monkeypatch.setattr(cli.maintainer_lane_status, "main", fail)

    try:
        cli.main(["lane", "status", "--repo-root", str(tmp_path), "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("expected argparse help exit")

    assert "usage: odylith lane status" in capsys.readouterr().out
