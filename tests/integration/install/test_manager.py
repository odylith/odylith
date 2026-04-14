from __future__ import annotations

import json
import subprocess
import shutil
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from odylith import cli
from odylith.install import manager as install_manager_module
from odylith.install import runtime
from odylith.install.runtime import runtime_verification_path
from odylith.runtime.common import codex_cli_capabilities
from odylith.install.manager import (
    doctor_bundle,
    evaluate_start_preflight,
    install_bundle,
    load_install_state,
    migrate_legacy_install,
    reinstall_install,
    rollback_install,
    set_agents_integration,
    uninstall_bundle,
    upgrade_install,
    version_status,
)
from odylith.install.state import write_install_state, write_version_pin
from odylith.install.state import load_version_pin

REPO_ROOT = Path(__file__).resolve().parents[3]
BUNDLE_ROOT = REPO_ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith"


def _test_runtime_python_wrapper() -> str:
    source_root = (REPO_ROOT / "src").resolve()
    host_python = Path(sys.executable).resolve()
    return (
        "#!/usr/bin/env bash\n"
        'if [ "${1:-}" = "-I" ]; then\n'
        "  shift\n"
        "fi\n"
        f'export PYTHONPATH="{source_root}${{PYTHONPATH:+:$PYTHONPATH}}"\n'
        f'exec "{host_python}" "$@"\n'
    )


def _write_repo_root(repo_root: Path) -> None:
    (repo_root / "AGENTS.md").write_text("# Repo Root\n\nBody\n", encoding="utf-8")


def _write_casebook_bug(
    path: Path,
    *,
    status: str,
    created: str,
    severity: str,
    components: str,
    bug_id: str = "",
) -> None:
    lines: list[str] = []
    if bug_id:
        lines.extend([f"- Bug ID: {bug_id}", ""])
    lines.extend(
        [
            f"- Status: {status}",
            f"- Created: {created}",
            f"- Severity: {severity}",
            f"- Components Affected: {components}",
            "",
            "- Description: Example bug.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _seed_legacy_casebook_bug_pair(repo_root: Path) -> tuple[Path, Path]:
    bug_root = repo_root / "odylith" / "casebook" / "bugs"
    bug_root.mkdir(parents=True, exist_ok=True)
    retained = bug_root / "2026-03-25-existing-bug.md"
    missing = bug_root / "2026-03-26-missing-bug.md"
    _write_casebook_bug(
        retained,
        bug_id="CB-007",
        status="Closed",
        created="2026-03-25",
        severity="P2",
        components="dashboard",
    )
    _write_casebook_bug(
        missing,
        status="Open",
        created="2026-03-26",
        severity="P1",
        components="tooling",
    )
    return retained, missing


def _load_bundle_js_assignment(relative_path: str) -> dict[str, object]:
    payload_js = (BUNDLE_ROOT / relative_path).read_text(encoding="utf-8")
    return json.loads(payload_js.split(" = ", 1)[1].rsplit(";", 1)[0])


def _write_fake_source_checkout(root: Path) -> Path:
    source_root = root / "odylith-source"
    (source_root / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    (source_root / "pyproject.toml").write_text("[project]\nname='odylith'\nversion='0.0.0'\n", encoding="utf-8")
    return source_root


def _write_product_repo_shape(repo_root: Path, *, version: str = "1.2.3") -> None:
    (repo_root / "pyproject.toml").write_text(f"[project]\nname='odylith'\nversion='{version}'\n", encoding="utf-8")
    (repo_root / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "registry" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "radar" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "maintainer").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text(
        '{"version":"v1","components":[]}\n',
        encoding="utf-8",
    )
    (repo_root / "odylith" / "radar" / "source" / "INDEX.md").write_text("# Backlog Index\n", encoding="utf-8")
    shutil.copy2(REPO_ROOT / "odylith" / "AGENTS.md", repo_root / "odylith" / "AGENTS.md")
    shutil.copy2(REPO_ROOT / "odylith" / "maintainer" / "AGENTS.md", repo_root / "odylith" / "maintainer" / "AGENTS.md")


def _seed_runtime_with_verification(repo_root: Path, *, version: str, verification: dict[str, object]) -> Path:
    version_root = repo_root / ".odylith" / "runtime" / "versions" / version
    python = version_root / "bin" / "python"
    python.parent.mkdir(parents=True, exist_ok=True)
    wrapper_script = _test_runtime_python_wrapper()
    python.write_text(wrapper_script, encoding="utf-8")
    python.chmod(0o755)
    python3 = version_root / "bin" / "python3"
    python3.write_text(wrapper_script, encoding="utf-8")
    python3.chmod(0o755)
    odylith_bin = version_root / "bin" / "odylith"
    odylith_bin.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    odylith_bin.chmod(0o755)
    (version_root / "pyvenv.cfg").write_text("version = 3.13.12\n", encoding="utf-8")
    (version_root / "runtime-metadata.json").write_text(
        json.dumps(
            {
                "schema_version": "odylith-runtime-bundle.v1",
                "version": version,
                "platform": "darwin-arm64",
                "python_version": "3.13.12",
                "source_wheel": f"odylith-{version}-py3-none-any.whl",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    runtime_verification_path(version_root).write_text(
        json.dumps(
            {
                "schema_version": "odylith-runtime-verification.v1",
                "version": version,
                "verification": verification,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    runtime.write_managed_runtime_trust(
        repo_root=repo_root,
        version_root=version_root,
        verification=verification,
    )
    current = repo_root / ".odylith" / "runtime" / "current"
    current.parent.mkdir(parents=True, exist_ok=True)
    if current.exists() or current.is_symlink():
        current.unlink()
    current.symlink_to(version_root)
    return version_root


def _seed_repairable_launcher_layer(repo_root: Path, *, version: str = "1.2.3") -> Path:
    version_root = repo_root / ".odylith" / "runtime" / "versions" / version
    python = version_root / "bin" / "python"
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    python.chmod(0o755)
    runtime.switch_runtime(repo_root=repo_root, target=version_root)
    runtime.ensure_launcher(repo_root=repo_root, fallback_python=python)
    return version_root


def _seed_verified_release_runtime(
    repo_root: Path,
    *,
    version: str,
    verification: dict[str, object] | None = None,
) -> tuple[Path, Path]:
    version_root = repo_root / ".odylith" / "runtime" / "versions" / version
    bin_dir = version_root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper_script = _test_runtime_python_wrapper()
    for name in ("python", "python3", "odylith"):
        executable = bin_dir / name
        if name == "odylith":
            executable.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        else:
            executable.write_text(wrapper_script, encoding="utf-8")
        executable.chmod(0o755)
    (version_root / "pyvenv.cfg").write_text("version = 3.13.12\n", encoding="utf-8")
    (version_root / "runtime-metadata.json").write_text(
        json.dumps(
            {
                "schema_version": "odylith-runtime-bundle.v1",
                "version": version,
                "platform": "darwin-arm64",
                "python_version": "3.13.12",
                "source_wheel": f"odylith-{version}-py3-none-any.whl",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    verification_payload = verification or {
        "runtime_bundle_sha256": f"runtime-{version}",
        "wheel_sha256": f"wheel-{version}",
    }
    runtime_verification_path(version_root).write_text(
        json.dumps(
            {
                "schema_version": "odylith-runtime-verification.v1",
                "version": version,
                "verification": verification_payload,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    runtime.write_managed_runtime_trust(
        repo_root=repo_root,
        version_root=version_root,
        verification=verification_payload,
    )
    return version_root, bin_dir / "python"


def _seed_legacy_runtime(repo_root: Path, *, version: str = "1.2.3") -> Path:
    version_root = repo_root / ".odyssey" / "runtime" / "versions" / version
    bin_dir = version_root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper_script = _test_runtime_python_wrapper()
    for name in ("python", "python3", "odyssey"):
        executable = bin_dir / name
        executable.write_text("#!/usr/bin/env bash\nexit 0\n" if name == "odyssey" else wrapper_script, encoding="utf-8")
        executable.chmod(0o755)
    (version_root / "pyvenv.cfg").write_text("version = 3.13.12\n", encoding="utf-8")
    (version_root / "runtime-metadata.json").write_text(
        json.dumps(
            {
                "schema_version": "odyssey-runtime-bundle.v1",
                "version": version,
                "platform": "darwin-arm64",
                "python_version": "3.13.12",
                "source_wheel": f"odyssey-{version}-py3-none-any.whl",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    current = repo_root / ".odyssey" / "runtime" / "current"
    current.parent.mkdir(parents=True, exist_ok=True)
    if current.exists() or current.is_symlink():
        current.unlink()
    current.symlink_to(Path("versions") / version)
    return version_root


def test_migrate_legacy_install_rewrites_roots_and_purges_volatile_state(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    (repo_root / ".gitignore").write_text("/.odyssey/\n", encoding="utf-8")
    (repo_root / "odyssey" / "runtime" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odyssey" / "runtime" / "source" / "product-version.v1.json").write_text(
        json.dumps({"schema_version": "odyssey-product.v1", "odyssey_version": "1.2.3"}, indent=2) + "\n",
        encoding="utf-8",
    )
    (repo_root / "odyssey" / "radar" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odyssey" / "radar" / "source" / "INDEX.md").write_text(
        "# Odyssey Backlog\n\nUse odyssey/index.html.\n",
        encoding="utf-8",
    )
    (repo_root / "docs").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs" / "platform-maintainer-guide.md").write_text(
        "Legacy operator note: see odyssey/index.html after migration.\n",
        encoding="utf-8",
    )
    (repo_root / ".odyssey" / "cache" / "odyssey-context-engine").mkdir(parents=True, exist_ok=True)
    (repo_root / ".odyssey" / "locks" / "odyssey-context-engine").mkdir(parents=True, exist_ok=True)
    (repo_root / ".odyssey" / "runtime" / "odyssey-memory" / "lance").mkdir(parents=True, exist_ok=True)
    (repo_root / ".odyssey" / "runtime" / "odyssey-benchmarks").mkdir(parents=True, exist_ok=True)
    (repo_root / ".odyssey" / "runtime" / "odyssey-context-engine-state.v1.json").write_text("{}\n", encoding="utf-8")
    (repo_root / ".odyssey" / "runtime" / "release-upgrade-spotlight.v1.json").write_text(
        json.dumps({"from_version": "1.2.2", "to_version": "1.2.3"}, indent=2) + "\n",
        encoding="utf-8",
    )
    (repo_root / ".odyssey" / "bin").mkdir(parents=True, exist_ok=True)
    (repo_root / ".odyssey" / "bin" / "odyssey").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (repo_root / ".odyssey" / "bin" / "odyssey-bootstrap").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (repo_root / ".odyssey" / "consumer-profile.json").write_text(
        json.dumps({"consumer_id": "demo", "surface_roots": {"dashboard": "odyssey/index.html"}}, indent=2) + "\n",
        encoding="utf-8",
    )
    (repo_root / ".odyssey" / "install.json").write_text(
        json.dumps({"launcher_path": ".odyssey/bin/odyssey", "consumer_profile_path": ".odyssey/consumer-profile.json"}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    (repo_root / ".odyssey" / "install-ledger.v1.jsonl").write_text(
        json.dumps({"operation": "install", "path": ".odyssey/bin/odyssey"}) + "\n",
        encoding="utf-8",
    )
    _seed_legacy_runtime(repo_root)

    summary = migrate_legacy_install(repo_root=repo_root)

    assert summary.state_root == repo_root / ".odylith"
    assert not (repo_root / ".odyssey").exists()
    assert not (repo_root / "odyssey").exists()
    assert (repo_root / "odylith" / "runtime" / "source" / "product-version.v1.json").is_file()
    assert (repo_root / ".odylith" / "bin" / "odylith").is_file()
    assert (repo_root / ".odylith" / "bin" / "odylith-bootstrap").is_file()
    assert not (repo_root / ".odylith" / "runtime" / "odylith-memory").exists()
    assert not (repo_root / ".odylith" / "runtime" / "odylith-benchmarks").exists()
    assert not (repo_root / ".odylith" / "runtime" / "release-upgrade-spotlight.v1.json").exists()
    assert not (repo_root / ".odylith" / "cache" / "odylith-context-engine").exists()
    assert not (repo_root / ".odylith" / "locks" / "odylith-context-engine").exists()
    assert "/.odylith/" in (repo_root / ".gitignore").read_text(encoding="utf-8")
    assert "/.odyssey/" not in (repo_root / ".gitignore").read_text(encoding="utf-8")
    assert ".odylith/runtime/release-upgrade-spotlight.v1.json" in summary.removed_paths

    install_payload = json.loads((repo_root / ".odylith" / "install.json").read_text(encoding="utf-8"))
    version_pin = json.loads((repo_root / "odylith" / "runtime" / "source" / "product-version.v1.json").read_text(encoding="utf-8"))
    consumer_profile = json.loads((repo_root / ".odylith" / "consumer-profile.json").read_text(encoding="utf-8"))

    assert install_payload["launcher_path"].endswith(".odylith/bin/odylith")
    assert install_payload["consumer_profile_path"].endswith(".odylith/consumer-profile.json")
    assert version_pin["schema_version"] == "odylith-product.v1"
    assert version_pin["odylith_version"] == "1.2.3"
    assert consumer_profile["surface_roots"]["dashboard"] == "odylith/index.html"
    assert (repo_root / "odylith" / "radar" / "source" / "INDEX.md").read_text(encoding="utf-8") == (
        "# Odylith Backlog\n\nUse odylith/index.html.\n"
    )
    assert (repo_root / "docs" / "platform-maintainer-guide.md").read_text(encoding="utf-8") == (
        "Legacy operator note: see odyssey/index.html after migration.\n"
    )
    assert summary.stale_reference_audit is not None
    assert summary.stale_reference_audit.hit_count >= 1
    assert summary.stale_reference_audit.report_path.is_file()
    assert "docs/platform-maintainer-guide.md" in summary.stale_reference_audit.report_path.read_text(encoding="utf-8")


def test_migrate_legacy_install_merges_into_existing_odylith_roots(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    (repo_root / "odylith" / "AGENTS.md").parent.mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "AGENTS.md").write_text("# Odylith\n", encoding="utf-8")
    (repo_root / ".odylith" / "bin").mkdir(parents=True, exist_ok=True)
    (repo_root / ".odylith" / "bin" / "odylith").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")

    (repo_root / "odyssey" / "technical-plans").mkdir(parents=True, exist_ok=True)
    (repo_root / "odyssey" / "technical-plans" / "INDEX.md").write_text(
        "# Odyssey Plans\n\nSee odyssey/index.html.\n",
        encoding="utf-8",
    )
    (repo_root / ".odyssey" / "install.json").parent.mkdir(parents=True, exist_ok=True)
    (repo_root / ".odyssey" / "install.json").write_text(
        json.dumps({"launcher_path": ".odyssey/bin/odyssey"}, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = migrate_legacy_install(repo_root=repo_root)

    assert not (repo_root / "odyssey").exists()
    assert not (repo_root / ".odyssey").exists()
    assert "odyssey/ -> odylith/" in summary.moved_paths
    assert ".odyssey/ -> .odylith/" in summary.moved_paths
    assert (repo_root / "odylith" / "technical-plans" / "INDEX.md").read_text(encoding="utf-8") == (
        "# Odylith Plans\n\nSee odylith/index.html.\n"
    )
    install_payload = json.loads((repo_root / ".odylith" / "install.json").read_text(encoding="utf-8"))
    assert str(install_payload["launcher_path"]).endswith(".odylith/bin/odylith")


def test_migrate_legacy_install_rewrites_absolute_current_runtime_symlink(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _seed_legacy_runtime(repo_root, version="source-local")

    legacy_current = repo_root / ".odyssey" / "runtime" / "current"
    if legacy_current.exists() or legacy_current.is_symlink():
        legacy_current.unlink()
    legacy_current.symlink_to((repo_root / ".odyssey" / "runtime" / "versions" / "source-local").resolve())

    summary = migrate_legacy_install(repo_root=repo_root)

    migrated_current = repo_root / ".odylith" / "runtime" / "current"
    assert summary.state_root == repo_root / ".odylith"
    assert migrated_current.is_symlink()
    assert migrated_current.resolve() == repo_root / ".odylith" / "runtime" / "versions" / "source-local"
    assert ".odyssey/ -> .odylith/" in summary.moved_paths
    assert ".odyssey" not in str(migrated_current.resolve())


def _write_fake_context_engine_pack(
    repo_root: Path,
    *,
    target_root: Path,
    version: str,
    pack_id: str = "odylith-context-engine-memory",
    asset_name: str | None = None,
    feature_pack_sha256: str | None = None,
    payload_relative_path: str = "lib/python3.13/site-packages/watchdog/__init__.py",
    payload_text: str | None = None,
) -> Path:
    relative_path = str(payload_relative_path).strip()
    pack_asset_name = str(asset_name or f"{pack_id}-darwin-arm64.tar.gz").strip()
    feature_pack_digest = str(feature_pack_sha256 or f"feature-pack-{version}").strip()
    payload_path = target_root / relative_path
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(payload_text or f"watchdog-from-{version}\n", encoding="utf-8")
    metadata_path = target_root / "runtime-feature-packs.v1.json"
    metadata_path.write_text(
        json.dumps(
            {
                "schema_version": "odylith-runtime-feature-packs.v1",
                "version": str(version),
                "packs": {
                    pack_id: {
                        "asset_name": pack_asset_name,
                        "display_name": "Odylith Context Engine memory pack",
                        "installed_utc": "2026-03-27T00:00:00+00:00",
                        "paths": [relative_path],
                        "platform": "darwin-arm64",
                        "verification": {
                            "feature_pack_id": pack_id,
                            "feature_pack_sha256": feature_pack_digest,
                        },
                    }
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    runtime.write_managed_runtime_trust(
        repo_root=repo_root,
        version_root=target_root,
        verification=runtime.runtime_verification_evidence(target_root),
    )
    return metadata_path


@pytest.fixture(autouse=True)
def _stub_release_install_for_consumer_bootstrap(monkeypatch):
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    def _fake_install_release_runtime(*, repo_root, repo, version="latest", activate=True):  # noqa: ANN001
        assert repo == "odylith/odylith"
        resolved_version = "1.2.3" if version == "latest" else str(version)
        runtime_root, python = _seed_verified_release_runtime(
            Path(repo_root),
            version=resolved_version,
        )
        if activate:
            current = Path(repo_root) / ".odylith" / "runtime" / "current"
            current.parent.mkdir(parents=True, exist_ok=True)
            if current.exists() or current.is_symlink():
                current.unlink()
            current.symlink_to(runtime_root)
        return SimpleNamespace(
            version=resolved_version,
            manifest={"repo_schema_version": 1, "migration_required": False},
            python=python,
            root=runtime_root,
            verification={
                "runtime_bundle_sha256": f"runtime-{resolved_version}",
                "wheel_sha256": f"wheel-{resolved_version}",
            },
        )

    monkeypatch.setattr(install_manager_module, "install_release_runtime", _fake_install_release_runtime)

    def _fake_install_release_feature_pack(*, repo_root, repo, version, runtime_root=None, pack_id="odylith-context-engine-memory"):  # noqa: ANN001
        assert repo == "odylith/odylith"
        assert pack_id == "odylith-context-engine-memory"
        target_root = Path(runtime_root) if runtime_root is not None else Path(repo_root) / ".odylith" / "runtime" / "versions" / str(version)
        _write_fake_context_engine_pack(
            Path(repo_root),
            target_root=target_root,
            version=str(version),
            pack_id=pack_id,
            feature_pack_sha256=f"feature-pack-{version}",
        )
        return SimpleNamespace(
            asset_name=f"{pack_id}-darwin-arm64.tar.gz",
            manifest={"repo_schema_version": 1, "migration_required": False},
            pack_id=pack_id,
            root=target_root,
            verification={
                "feature_pack_id": pack_id,
                "feature_pack_sha256": f"feature-pack-{version}",
            },
            version=str(version),
        )

    monkeypatch.setattr(install_manager_module, "install_release_feature_pack", _fake_install_release_feature_pack)


@pytest.fixture(autouse=True)
def _stub_release_version_resolution(monkeypatch):
    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3" if str(kwargs.get("version") or "").strip() in {"", "latest"} else str(kwargs["version"])
        ),
    )


def test_install_bundle_bootstraps_customer_owned_tree_without_copying_product_bundle(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)

    summary = install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    guidance_path = repo_root / "odylith" / "AGENTS.md"
    claude_guidance_path = repo_root / "odylith" / "CLAUDE.md"
    assert guidance_path.is_file()
    assert claude_guidance_path.is_file()
    assert (repo_root / ".claude" / "CLAUDE.md").is_file()
    assert (repo_root / ".claude" / "settings.json").is_file()
    assert (repo_root / ".claude" / "commands" / "odylith-start.md").is_file()
    assert (repo_root / ".claude" / "commands" / "odylith-context.md").is_file()
    assert (repo_root / ".claude" / "commands" / "odylith-query.md").is_file()
    assert (repo_root / ".claude" / "commands" / "odylith-sync-governance.md").is_file()
    assert (repo_root / ".claude" / "agents" / "odylith-compass-narrator.md").is_file()
    assert (repo_root / ".claude" / "agents" / "odylith-reviewer.md").is_file()
    assert (repo_root / ".claude" / "agents" / "odylith-workstream.md").is_file()
    assert (repo_root / ".claude" / "hooks" / "odylith_claude_support.py").is_file()
    assert (repo_root / ".claude" / "hooks" / "subagent-start-ground.py").is_file()
    assert (repo_root / ".claude" / "hooks" / "refresh-governance-after-edit.py").is_file()
    assert (repo_root / ".claude" / "hooks" / "log-stop-summary.py").is_file()
    assert (repo_root / ".claude" / "rules" / "odylith-governance.md").is_file()
    assert (repo_root / ".claude" / "output-styles" / "odylith-grounded.md").is_file()
    assert (repo_root / ".codex" / "config.toml").is_file()
    assert (repo_root / ".codex" / "hooks.json").is_file()
    assert (repo_root / ".codex" / "agents" / "odylith-workstream.toml").is_file()
    codex_hooks = json.loads((repo_root / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    assert codex_hooks["SessionStart"][0]["hooks"][0]["command"] == "./.odylith/bin/odylith codex session-start-ground --repo-root ."
    assert (repo_root / ".agents" / "skills" / "odylith-start" / "SKILL.md").is_file()
    assert not (repo_root / ".agents" / "skills" / "odylith-subagent-router" / "SKILL.md").exists()
    assert (repo_root / "odylith" / "runtime" / "source" / "product-version.v1.json").is_file()
    assert (repo_root / "odylith" / "runtime" / "source" / "tooling_shell.v1.json").is_file()
    assert (repo_root / "odylith" / "index.html").is_file()
    assert (repo_root / "odylith" / "agents-guidelines" / "UPGRADE_AND_RECOVERY.md").is_file()
    assert (repo_root / "odylith" / "agents-guidelines" / "CODEX_HOST_CONTRACT.md").is_file()
    assert (repo_root / "odylith" / "skills" / "odylith-subagent-router" / "SKILL.md").is_file()
    assert (repo_root / "odylith" / "skills" / "odylith-subagent-orchestrator" / "SKILL.md").is_file()
    assert (repo_root / "odylith" / "surfaces" / "brand" / "manifest.json").is_file()
    assert (repo_root / "odylith" / "radar" / "source").is_dir()
    assert (repo_root / "odylith" / "radar" / "source" / "ideas").is_dir()
    assert (repo_root / "odylith" / "radar" / "source" / "INDEX.md").is_file()
    assert (repo_root / "odylith" / "technical-plans").is_dir()
    assert (repo_root / "odylith" / "technical-plans" / "in-progress").is_dir()
    assert (repo_root / "odylith" / "technical-plans" / "done").is_dir()
    assert (repo_root / "odylith" / "technical-plans" / "parked").is_dir()
    assert (repo_root / "odylith" / "technical-plans" / "INDEX.md").is_file()
    assert (repo_root / "odylith" / "casebook" / "bugs").is_dir()
    assert (repo_root / "odylith" / "registry" / "source" / "components").is_dir()
    assert (repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json").is_file()
    assert (repo_root / "odylith" / "atlas" / "source").is_dir()
    assert (repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json").is_file()
    assert not (repo_root / "odylith" / "atlas" / "README.md").exists()
    bundled_claude_relpaths = sorted(path.relative_to(BUNDLE_ROOT) for path in BUNDLE_ROOT.rglob("CLAUDE.md"))
    assert bundled_claude_relpaths
    for relative_path in bundled_claude_relpaths:
        installed_path = repo_root / "odylith" / relative_path
        assert installed_path.is_file(), f"missing consumer CLAUDE companion: {installed_path}"

    consumer_profile = repo_root / ".odylith" / "consumer-profile.json"
    assert consumer_profile.is_file()
    profile_payload = json.loads(consumer_profile.read_text(encoding="utf-8"))
    assert profile_payload["truth_roots"]["radar_source"] == "odylith/radar/source"
    assert profile_payload["surface_roots"]["product_root"] == "odylith"
    assert profile_payload["odylith_write_policy"] == {
        "allow_odylith_mutations": False,
        "odylith_fix_mode": "feedback_only",
        "protected_roots": ["odylith", ".odylith"],
    }

    shell_payload = json.loads((repo_root / "odylith" / "runtime" / "source" / "tooling_shell.v1.json").read_text(encoding="utf-8"))
    assert shell_payload["shell_repo_label"] == "Repo · repo"
    assert shell_payload["maintainer_notes"] == []
    shell_index_html = (repo_root / "odylith" / "index.html").read_text(encoding="utf-8")
    assert "The local shell is getting ready." in shell_index_html
    assert "./.odylith/bin/odylith sync --repo-root . --force --impact-mode full" in shell_index_html
    guidance_text = guidance_path.read_text(encoding="utf-8")
    assert "local repo truth, not a copy of the Odylith product repo" in guidance_text
    assert "`.claude/`, `.codex/`, `.agents/skills/`, `odylith/AGENTS.md`, `odylith/CLAUDE.md`, the shipped scoped guidance companions under `odylith/**/AGENTS.md` and `odylith/**/CLAUDE.md`, `odylith/agents-guidelines/`, and `odylith/skills/` are Odylith-managed guidance assets" in guidance_text
    assert "Before any substantive repo scan or code change outside trivial fixes, the agent must start from the repo-local Odylith entrypoint" in guidance_text
    assert "keep the active workstream, component, or packet in scope" in guidance_text
    assert "Direct repo scan before that start step is a policy violation unless the task is trivial or Odylith is unavailable." in guidance_text
    assert "keep startup, fallback, routing, and packet-selection internals implicit" in guidance_text
    assert "the exact file/workstream, the bug under test, or the validation in flight" in guidance_text
    assert "If an earlier repo-local start attempt degraded but work can continue safely, do not narrate that history." in guidance_text
    assert "Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates" in guidance_text
    assert "never prefix commentary with control-plane receipt labels" in guidance_text
    assert "Mention Odylith during the work only when the user explicitly asks for the command, a real blocker requires it, or a consumer-versus-maintainer lane distinction matters." in guidance_text
    assert "literal commands" not in guidance_text
    assert "Keep normal commentary task-first and human." in guidance_text
    assert "reserve explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels" in guidance_text
    assert "At closeout, you may add at most one short `Odylith Assist:` line" in guidance_text
    assert "Prefer `**Odylith Assist:**` when Markdown formatting is available" in guidance_text
    assert "Lead with the user win" in guidance_text
    assert "link updated governance ids inline when they were actually changed" in guidance_text
    assert "frame the edge against `odylith_off` or the broader unguided path" in guidance_text
    assert "Keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual." in guidance_text
    assert "Ground the line in concrete observed counts, measured deltas, or validation outcomes" in guidance_text
    assert "Silence is better than filler." in guidance_text
    assert "follow this workflow check in order: read the nearest `AGENTS.md`; run the repo-local `odylith start`/`odylith context` step" in guidance_text
    assert "grounding Odylith is diagnosis authority, not blanket write authority" in guidance_text
    assert "stop at diagnosis and maintainer-ready feedback" in guidance_text
    assert "Treat `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh` as writes" in guidance_text
    assert "Treat the managed guidance files under `.claude/`, `.codex/`, the curated `.agents/skills/` command shims, `odylith/AGENTS.md`, `odylith/CLAUDE.md`, the shipped scoped `odylith/**/AGENTS.md` and `odylith/**/CLAUDE.md` companions, `odylith/agents-guidelines/`, and the specialist references under `odylith/skills/` as the Odylith operating layer" in guidance_text
    assert "Treat backlog/workstream, plan, Registry, Atlas, Casebook, Compass, and session upkeep as part of the same grounded Odylith workflow" in guidance_text
    assert "Queued backlog items" in guidance_text
    assert "do not pick it up automatically" in guidance_text
    assert "Search existing workstream, plan, bug, component, diagram, and recent session/Compass context first" in guidance_text
    assert "If the slice is genuinely new and it is repo-owned non-product work, create the missing workstream and bound plan before non-trivial implementation" in guidance_text
    assert "Default to the nearest `AGENTS.md`, the repo-local launcher, and truthful `odylith ... --help` for routine backlog, plan, bug, spec, component, and diagram upkeep." in guidance_text
    assert "When a routine governance task already maps to a first-class CLI family such as `odylith bug capture`, `odylith backlog create`, `odylith component register`, `odylith atlas scaffold`, or `odylith compass log`" in guidance_text
    assert "rerender only the owned surface" in guidance_text
    assert "Codex and Claude Code share the same default Odylith lane" in guidance_text
    assert "On Codex, the managed `.codex/` project assets and curated `.agents/skills/` command shims are best-effort enhancements" in guidance_text
    assert "Treat the managed guidance files under `.claude/`, `.codex/`, the curated `.agents/skills/` command shims" in guidance_text
    assert "## Common Fast Paths" in guidance_text
    assert "./.odylith/bin/odylith bug capture --help" in guidance_text
    assert "./.odylith/bin/odylith radar refresh --repo-root ." in guidance_text
    assert "./.odylith/bin/odylith registry refresh --repo-root ." in guidance_text
    assert "./.odylith/bin/odylith casebook refresh --repo-root ." in guidance_text
    assert "./.odylith/bin/odylith atlas refresh --repo-root . --atlas-sync" in guidance_text
    assert "./.odylith/bin/odylith compass refresh --repo-root . --wait" in guidance_text
    assert "./.odylith/bin/odylith codex compatibility --repo-root ." in guidance_text
    assert "Keep `.agents/skills` lookup, missing-shim, and fallback-source details implicit" in guidance_text
    assert "## Specialist Skills" in guidance_text
    assert "keep Odylith grounding mostly in the background. Do not require a fixed visible prefix" not in guidance_text
    root_claude = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "@AGENTS.md" in root_claude
    assert ".claude/CLAUDE.md" in root_claude
    assert "<!-- odylith-scope:start -->" in root_claude
    root_agents = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
    assert "Before any substantive repo scan or code change outside trivial fixes, the agent must start from the repo-local Odylith entrypoint" in root_agents
    assert "keep the active workstream, component, or packet in scope" in root_agents
    assert "Direct repo scan before that start step is a policy violation unless the task is trivial or Odylith is unavailable." in root_agents
    assert "keep startup, fallback, routing, and packet-selection internals implicit" in root_agents
    assert "the exact file/workstream, the bug under test, or the validation in flight" in root_agents
    assert "If an earlier repo-local start attempt degraded but work can continue safely, do not narrate that history." in root_agents
    assert "Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates" in root_agents
    assert "never prefix commentary with control-plane receipt labels" in root_agents
    assert "Mention Odylith during the work only when the user explicitly asks for the command, a real blocker requires it, or a consumer-versus-maintainer lane distinction matters." in root_agents
    assert "literal commands" not in root_agents
    assert "Keep normal commentary task-first and human." in root_agents
    assert "reserve explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels" in root_agents
    assert "At closeout, you may add at most one short `Odylith Assist:` line" in root_agents
    assert "Prefer `**Odylith Assist:**` when Markdown formatting is available" in root_agents
    assert "Lead with the user win" in root_agents
    assert "link updated governance ids inline when they were actually changed" in root_agents
    assert "frame the edge against `odylith_off` or the broader unguided path" in root_agents
    assert "Keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual." in root_agents
    assert "Ground the line in concrete observed counts, measured deltas, or validation outcomes" in root_agents
    assert "Silence is better than filler." in root_agents
    assert "follow this workflow check in order: read the nearest `AGENTS.md`; run the repo-local `odylith start`/`odylith context` step" in root_agents
    assert "grounding Odylith is diagnosis authority, not blanket write authority" in root_agents
    assert "stop at diagnosis and maintainer-ready feedback" in root_agents
    assert "Treat `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh` as writes" in root_agents
    assert "search existing workstream, plan, bug, component, diagram, and recent session/Compass context first" in root_agents
    assert "Default to the nearest `AGENTS.md`, the repo-local launcher, and truthful `odylith ... --help` for routine backlog, plan, bug, spec, component, and diagram upkeep." in root_agents
    assert "When a routine governance task already maps to a first-class CLI family such as `odylith bug capture`, `odylith backlog create`, `odylith component register`, `odylith atlas scaffold`, or `odylith compass log`" in root_agents
    assert "rerender only the owned surface" in root_agents
    assert "odylith radar refresh" in root_agents
    assert "odylith registry refresh" in root_agents
    assert "odylith casebook refresh" in root_agents
    assert "odylith atlas refresh" in root_agents
    assert "odylith compass refresh --wait" in root_agents
    assert "Queued backlog items" in root_agents
    assert "do not pick it up automatically" in root_agents
    assert "If the slice expands beyond one truthful record, use child workstreams or execution waves" in root_agents
    assert "substantive grounded consumer-lane work" in root_agents
    assert "keep Odylith grounding mostly in the background. Do not require a fixed visible prefix" not in root_agents
    assert "Odylith grounding:" not in guidance_text
    assert "Odylith didn't return immediately" not in guidance_text
    assert "Odylith grounding:" not in root_agents
    assert "Odylith didn't return immediately" not in root_agents
    assert "odylith/maintainer/AGENTS.md" not in root_agents
    assert summary.created_guidance_files == ("CLAUDE.md",)
    assert summary.version == "1.2.3"


def test_install_bundle_derives_effective_codex_config_from_local_capabilities(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    codex_cli_capabilities.clear_codex_cli_capability_cache()

    monkeypatch.setattr(
        install_manager_module.codex_cli_capabilities,
        "inspect_codex_cli_capabilities",
        lambda **_: codex_cli_capabilities.CodexCliCapabilitySnapshot(
            repo_root=str(repo_root),
            codex_bin="codex",
            codex_available=False,
            codex_version_raw="",
            codex_version="",
            baseline_contract="AGENTS.md + ./.odylith/bin/odylith",
            baseline_ready=True,
            launcher_present=True,
            repo_agents_present=True,
            codex_project_assets_present=True,
            codex_skill_shims_present=True,
            project_assets_mode="best_effort_enhancements",
            trusted_project_required=True,
            hooks_feature_known=False,
            hooks_feature_enabled=None,
            prompt_input_probe_supported=False,
            prompt_input_probe_passed=False,
            repo_guidance_detected=False,
            future_version_policy="capability_based_no_max_pin",
            overall_posture="baseline_safe",
        ),
    )

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    payload = tomllib.loads((repo_root / ".codex" / "config.toml").read_text(encoding="utf-8"))
    assert "features" not in payload

    state = load_install_state(repo_root=repo_root)
    assert state["active_version"] == "1.2.3"
    assert (repo_root / ".odylith" / "bin" / "odylith").is_file()
    assert (repo_root / ".odylith" / "runtime" / "current").is_symlink()


def test_bundle_surfaces_ship_stable_product_bundle_assets() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")).get("project", {})
    current_version = str(project.get("version", "")).strip()
    registry_source = json.loads((BUNDLE_ROOT / "registry" / "source" / "component_registry.v1.json").read_text(encoding="utf-8"))
    atlas_source = json.loads(
        (BUNDLE_ROOT / "atlas" / "source" / "catalog" / "diagrams.v1.json").read_text(encoding="utf-8")
    )
    bundle_shell_source = json.loads(
        (BUNDLE_ROOT / "runtime" / "source" / "tooling_shell.v1.json").read_text(encoding="utf-8")
    )
    radar_payload = _load_bundle_js_assignment("radar/backlog-payload.v1.js")
    registry_payload = _load_bundle_js_assignment("registry/registry-payload.v1.js")
    casebook_payload = _load_bundle_js_assignment("casebook/casebook-payload.v1.js")
    compass_payload = _load_bundle_js_assignment("compass/compass-payload.v1.js")
    atlas_payload = _load_bundle_js_assignment("atlas/mermaid-payload.v1.js")
    tooling_payload = _load_bundle_js_assignment("tooling-payload.v1.js")
    tooling_payload_text = (BUNDLE_ROOT / "tooling-payload.v1.js").read_text(encoding="utf-8")
    registry_payload_text = (BUNDLE_ROOT / "registry" / "registry-payload.v1.js").read_text(encoding="utf-8")
    shell_index_text = (BUNDLE_ROOT / "index.html").read_text(encoding="utf-8")

    assert registry_source["version"] == "v1"
    assert isinstance(registry_source["components"], list)
    assert atlas_source["version"] == "v1"
    assert isinstance(atlas_source["diagrams"], list)
    assert bundle_shell_source == {"maintainer_notes": [], "shell_repo_label": "Repo · repo"}
    assert current_version
    bundled_release_note_path = BUNDLE_ROOT / "runtime" / "source" / "release-notes" / f"v{current_version}.md"
    assert bundled_release_note_path.is_file()
    assert f"version: {current_version}" in bundled_release_note_path.read_text(encoding="utf-8")
    assert isinstance(radar_payload["entries"], list)
    assert isinstance(radar_payload["detail_manifest"], dict)
    assert isinstance(registry_payload["components"], list)
    assert isinstance(registry_payload["diagnostics"], list)
    assert isinstance(registry_payload["delivery_intelligence"], dict)
    assert isinstance(registry_payload["detail_manifest"], dict)
    assert isinstance(casebook_payload["bugs"], list)
    assert isinstance(casebook_payload["detail_manifest"], dict)
    assert isinstance(atlas_payload["diagrams"], list)
    assert isinstance(tooling_payload["case_queue"], list)
    assert isinstance(tooling_payload["components"], dict)
    assert isinstance(tooling_payload["diagrams"], dict)
    assert isinstance(tooling_payload["maintainer_notes"], list)
    assert isinstance(tooling_payload["odylith_drawer"], dict)
    assert str(tooling_payload["shell_repo_label"]).strip()
    assert isinstance(tooling_payload["shell_version_label"], str)
    assert isinstance(tooling_payload["welcome_state"], dict)
    assert "show" in tooling_payload["welcome_state"]
    assert isinstance(tooling_payload["workstreams"], dict)
    assert str(compass_payload["runtime_json_href"]).startswith("runtime/current.v1.json")
    assert (BUNDLE_ROOT / "registry" / "source" / "components" / "README.md").is_file()
    assert list((BUNDLE_ROOT / "registry" / "source" / "components").glob("*/CURRENT_SPEC.md"))
    assert list((BUNDLE_ROOT / "atlas" / "source").glob("*.mmd"))
    assert not (BUNDLE_ROOT / "runtime" / "delivery_intelligence.v4.json").exists()
    assert "/private/var/folders/" not in tooling_payload_text
    assert "/private/var/folders/" not in registry_payload_text
    assert "tmp." not in tooling_payload_text
    assert "tmp." not in registry_payload_text
    assert "v0.0.0-test" not in tooling_payload_text
    assert "v0.0.0-test" not in shell_index_text


def test_install_bundle_syncs_authored_release_notes_into_consumer_repo(tmp_path: Path) -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")).get("project", {})
    current_version = str(project.get("version", "")).strip()
    assert current_version
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    notes_root = repo_root / "odylith" / "runtime" / "source" / "release-notes"
    notes_root.mkdir(parents=True, exist_ok=True)
    (notes_root / "v0.0.1.md").write_text("stale\n", encoding="utf-8")

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version=current_version)

    bundled_note = BUNDLE_ROOT / "runtime" / "source" / "release-notes" / f"v{current_version}.md"
    installed_note = notes_root / f"v{current_version}.md"
    assert bundled_note.is_file()
    assert installed_note.is_file()
    assert installed_note.read_text(encoding="utf-8") == bundled_note.read_text(encoding="utf-8")
    assert sorted(path.name for path in notes_root.glob("*.md")) == [f"v{current_version}.md"]


def test_upgrade_install_prunes_previous_consumer_release_notes_and_keeps_current_one(tmp_path: Path, monkeypatch) -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")).get("project", {})
    current_version = str(project.get("version", "")).strip()
    assert current_version
    target_version = "1.2.4"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version=current_version)

    notes_root = repo_root / "odylith" / "runtime" / "source" / "release-notes"
    (notes_root / "v0.0.1.md").write_text("stale\n", encoding="utf-8")

    custom_bundle_root = tmp_path / "bundle"
    custom_notes_root = custom_bundle_root / "runtime" / "source" / "release-notes"
    custom_notes_root.mkdir(parents=True, exist_ok=True)
    (custom_notes_root / f"v{target_version}.md").write_text(
        (
            "---\n"
            f"version: {target_version}\n"
            "published_at: 2026-04-01T17:30:00Z\n"
            "summary: Target upgrade note.\n"
            "---\n\n"
            "Target upgrade note.\n"
        ),
        encoding="utf-8",
    )

    staged_root, staged_python = _seed_verified_release_runtime(repo_root, version=target_version)
    monkeypatch.setattr(install_manager_module, "bundled_product_root", lambda: custom_bundle_root)
    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        lambda **kwargs: SimpleNamespace(version=target_version),
    )
    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: SimpleNamespace(
            version=target_version,
            manifest={"repo_schema_version": 1, "migration_required": False},
            python=staged_python,
            root=staged_root,
            verification={"wheel_sha256": "abc123"},
        ),
    )
    monkeypatch.setattr(
        install_manager_module,
        "_ensure_managed_context_engine_pack",
        lambda **kwargs: {},
    )
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    summary = upgrade_install(
        repo_root=repo_root,
        release_repo="odylith/odylith",
        version=target_version,
        write_pin=True,
    )

    assert summary.active_version == target_version
    assert sorted(path.name for path in notes_root.glob("*.md")) == [f"v{target_version}.md"]
    assert "Target upgrade note." in (notes_root / f"v{target_version}.md").read_text(encoding="utf-8")


def test_upgrade_install_migrates_legacy_compass_history_archive_layout(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="0.1.10")

    runtime_dir = repo_root / "odylith" / "compass" / "runtime"
    history_dir = runtime_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    archive_dir = history_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    stale_active_day = "2020-01-01"
    archived_day = "2020-01-02"
    live_payload = {
        "version": "v1",
        "generated_utc": "2026-04-14T20:20:00Z",
        "history": {
            "retention_days": 15,
            "dates": [stale_active_day],
            "restored_dates": [],
            "archive": {
                "compressed": True,
                "path": "archive",
                "count": 1,
                "dates": [archived_day],
                "newest_date": archived_day,
                "oldest_date": archived_day,
            },
        },
    }
    (runtime_dir / "current.v1.json").write_text(json.dumps(live_payload, indent=2) + "\n", encoding="utf-8")
    (runtime_dir / "current.v1.js").write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(live_payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    (history_dir / f"{stale_active_day}.v1.json").write_text(json.dumps(live_payload, indent=2) + "\n", encoding="utf-8")
    (archive_dir / f"{archived_day}.v1.json.gz").write_text("legacy-archive", encoding="utf-8")
    (history_dir / "restore-pins.v1.json").write_text(
        json.dumps({"version": "v1", "generated_utc": "2026-04-14T20:20:00Z", "dates": [archived_day]}, indent=2) + "\n",
        encoding="utf-8",
    )
    (history_dir / "index.v1.json").write_text(
        json.dumps(
            {
                "version": "v1",
                "generated_utc": "2026-04-14T20:20:00Z",
                "retention_days": 15,
                "dates": [stale_active_day],
                "restored_dates": [],
                "archive": live_payload["history"]["archive"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (history_dir / "embedded.v1.js").write_text(
        "window.__ODYLITH_COMPASS_HISTORY__ = "
        + json.dumps(
            {
                "version": "v1",
                "generated_utc": "2026-04-14T20:20:00Z",
                "retention_days": 15,
                "dates": [stale_active_day],
                "restored_dates": [],
                "archive": live_payload["history"]["archive"],
                "snapshots": {
                    archived_day: live_payload,
                },
            },
            separators=(",", ":"),
        )
        + ";\n",
        encoding="utf-8",
    )

    staged_root, staged_python = _seed_verified_release_runtime(repo_root, version="0.1.11")
    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        lambda **kwargs: SimpleNamespace(version="0.1.11"),
    )
    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: SimpleNamespace(
            version="0.1.11",
            manifest={"repo_schema_version": 1, "migration_required": False},
            python=staged_python,
            root=staged_root,
            verification={"wheel_sha256": "abc123"},
        ),
    )
    monkeypatch.setattr(
        install_manager_module,
        "_ensure_managed_context_engine_pack",
        lambda **kwargs: {},
    )
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    summary = upgrade_install(
        repo_root=repo_root,
        release_repo="odylith/odylith",
        version="0.1.11",
        write_pin=True,
    )

    assert summary.active_version == "0.1.11"
    assert not archive_dir.exists()
    assert not (history_dir / "restore-pins.v1.json").exists()
    assert not (history_dir / f"{stale_active_day}.v1.json").exists()

    current_payload = json.loads((runtime_dir / "current.v1.json").read_text(encoding="utf-8"))
    assert current_payload["history"]["archive"]["count"] == 0
    index_payload = json.loads((history_dir / "index.v1.json").read_text(encoding="utf-8"))
    assert index_payload["archive"]["count"] == 0
    embedded_payload = json.loads(
        (history_dir / "embedded.v1.js").read_text(encoding="utf-8").removeprefix("window.__ODYLITH_COMPASS_HISTORY__ = ").removesuffix(";\n")
    )
    assert embedded_payload["archive"]["count"] == 0
    assert archived_day not in embedded_payload["snapshots"]


def test_install_bundle_creates_root_guidance_files_when_missing(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    summary = install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    root_guidance = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
    root_claude = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "# Repo Guidance" in root_guidance
    assert "<!-- odylith-scope:start -->" in root_guidance
    assert "If this folder is not backed by Git yet" in root_guidance
    assert "# CLAUDE.md" in root_claude
    assert "<!-- odylith-scope:start -->" in root_claude
    assert "@AGENTS.md" in root_claude
    assert ".claude/CLAUDE.md" in root_claude
    assert (repo_root / ".claude" / "CLAUDE.md").is_file()
    assert summary.repo_guidance_created is True
    assert summary.created_guidance_files == ("AGENTS.md", "CLAUDE.md")
    assert summary.git_repo_present is False
    assert summary.gitignore_updated is True
    assert (repo_root / ".gitignore").read_text(encoding="utf-8") == (
        "/.odylith/\n"
        "/odylith/compass/runtime/refresh-state.v1.json\n"
    )
    assert summary.version == "1.2.3"


def test_install_bundle_accepts_claude_only_root_guidance(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "CLAUDE.md").write_text("# Repo Root\n\nBody\n", encoding="utf-8")

    summary = install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    assert (repo_root / "AGENTS.md").is_file()
    assert "<!-- odylith-scope:start -->" in (repo_root / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- odylith-scope:start -->" in (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
    assert summary.repo_guidance_created is True
    assert summary.created_guidance_files == ("AGENTS.md",)


def test_install_bundle_adds_odylith_state_root_to_gitignore_for_git_repo(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    (repo_root / ".git").mkdir()

    summary = install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    assert summary.git_repo_present is True
    assert summary.gitignore_updated is True
    assert (repo_root / ".gitignore").read_text(encoding="utf-8") == (
        "/.odylith/\n"
        "/odylith/compass/runtime/refresh-state.v1.json\n"
    )


def test_install_bundle_does_not_duplicate_existing_odylith_gitignore_entry(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    (repo_root / ".git").mkdir()
    gitignore_path = repo_root / ".gitignore"
    gitignore_path.write_text("node_modules/\n.odylith/\n", encoding="utf-8")

    summary = install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    assert summary.git_repo_present is True
    assert summary.gitignore_updated is True
    assert gitignore_path.read_text(encoding="utf-8") == (
        "node_modules/\n"
        ".odylith/\n"
        "/odylith/compass/runtime/refresh-state.v1.json\n"
    )


def test_install_bundle_updates_existing_gitignore_without_git_repo(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    gitignore_path = repo_root / ".gitignore"
    gitignore_path.write_text("node_modules/\n", encoding="utf-8")

    summary = install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    assert summary.git_repo_present is False
    assert summary.gitignore_updated is True
    assert gitignore_path.read_text(encoding="utf-8") == (
        "node_modules/\n"
        "/.odylith/\n"
        "/odylith/compass/runtime/refresh-state.v1.json\n"
    )


def test_install_bundle_bootstrap_supports_first_consumer_sync(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    assert (repo_root / "odylith" / "index.html").is_file()
    assert cli.main(["sync", "--repo-root", str(repo_root), "--force"]) == 0


def test_install_bundle_align_pin_advances_existing_repo_pin_to_active_runtime(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    staged_root, staged_python = _seed_verified_release_runtime(repo_root, version="1.2.4")
    runtime.switch_runtime(repo_root=repo_root, target=staged_root)
    runtime.ensure_launcher(repo_root=repo_root, fallback_python=staged_python)
    monkeypatch.setattr(install_manager_module, "_ensure_managed_context_engine_pack", lambda **kwargs: {})

    summary = install_bundle(
        repo_root=repo_root,
        bundle_root=tmp_path / "unused-bundle",
        version="1.2.4",
        align_pin=True,
    )

    pin = load_version_pin(repo_root=repo_root)
    state = load_install_state(repo_root=repo_root)

    assert summary.version == "1.2.4"
    assert summary.pin_changed is True
    assert summary.pinned_version == "1.2.4"
    assert pin is not None
    assert pin.odylith_version == "1.2.4"
    assert state["active_version"] == "1.2.4"
    assert (repo_root / ".odylith" / "runtime" / "current").resolve().name == "1.2.4"


def test_start_preflight_uses_hosted_installer_when_odylith_is_not_installed(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    preflight = evaluate_start_preflight(repo_root=repo_root)

    assert preflight.lane == "install"
    assert preflight.next_command == "curl -fsSL https://odylith.ai/install.sh | bash"


def test_start_preflight_prefers_repo_local_bootstrap_repair_when_available(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "odylith").mkdir()
    _seed_repairable_launcher_layer(repo_root)
    (repo_root / ".odylith" / "bin" / "odylith").unlink()

    preflight = evaluate_start_preflight(repo_root=repo_root)

    assert preflight.lane == "repair"
    assert preflight.next_command == "./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair"


def test_start_preflight_prefers_main_launcher_repair_when_bootstrap_is_missing(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "odylith").mkdir()
    (repo_root / "odylith" / "AGENTS.md").write_text("managed guidance\n", encoding="utf-8")
    _seed_repairable_launcher_layer(repo_root)
    (repo_root / ".odylith" / "bin" / "odylith-bootstrap").unlink()

    preflight = evaluate_start_preflight(repo_root=repo_root)

    assert preflight.lane == "repair"
    assert preflight.next_command == "./.odylith/bin/odylith doctor --repo-root . --repair"


def test_start_preflight_prefers_healthy_bootstrap_repair_when_main_launcher_is_unhealthy(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    (repo_root / ".odylith" / "bin" / "odylith").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (repo_root / ".odylith" / "bin" / "odylith").chmod(0o755)

    preflight = evaluate_start_preflight(repo_root=repo_root)

    assert preflight.lane == "repair"
    assert preflight.next_command == "./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair"


def test_start_preflight_accepts_product_repo_source_fallback_when_recorded_fallbacks_are_stale(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root, version="1.2.3")

    _seed_runtime_with_verification(
        repo_root,
        version="1.2.3",
        verification={"wheel_sha256": "wheel-1.2.3"},
    )
    launcher = repo_root / ".odylith" / "bin" / "odylith"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(
        runtime._launcher_script(  # noqa: SLF001
            fallback_python=tmp_path / "missing" / "python",
            fallback_source_root=repo_root,
        ),
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    bootstrap = repo_root / ".odylith" / "bin" / "odylith-bootstrap"
    bootstrap.write_text(
        runtime._bootstrap_launcher_script(  # noqa: SLF001
            fallback_python=tmp_path / "missing" / "python",
            fallback_source_root=repo_root,
        ),
        encoding="utf-8",
    )
    bootstrap.chmod(0o755)

    write_install_state(repo_root=repo_root, payload={"active_version": "source-local", "detached": True})
    write_version_pin(repo_root=repo_root, version="1.2.3", repo_schema_version=1)
    (repo_root / ".odylith" / "consumer-profile.json").write_text("{}\n", encoding="utf-8")

    preflight = evaluate_start_preflight(repo_root=repo_root)

    assert preflight.lane == "bootstrap"
    assert preflight.healthy is True
    assert preflight.next_command == "./.odylith/bin/odylith start --repo-root ."


def test_start_preflight_rejects_consumer_source_local_lane(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    source_root = _write_fake_source_checkout(tmp_path)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    runtime.ensure_wrapped_runtime(
        repo_root=repo_root,
        version="source-local",
        fallback_python=repo_root / ".odylith" / "runtime" / "versions" / "1.2.3" / "bin" / "python",
        source_root=source_root,
        allow_host_python_fallback=False,
    )
    state = load_install_state(repo_root=repo_root)
    state["active_version"] = "source-local"
    state["detached"] = True
    state["last_known_good_version"] = "1.2.3"
    write_install_state(repo_root=repo_root, payload=state)

    preflight = evaluate_start_preflight(repo_root=repo_root)

    assert preflight.lane == "repair"
    assert preflight.healthy is False
    assert "Consumer repos cannot activate the detached source-local maintainer lane" in preflight.reason
    assert preflight.next_command == "./.odylith/bin/odylith doctor --repo-root . --repair"


def test_start_preflight_treats_partial_install_shape_as_repair_when_launcher_exists(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _seed_repairable_launcher_layer(repo_root)
    (repo_root / ".odylith" / "bin" / "odylith-bootstrap").unlink()

    preflight = evaluate_start_preflight(repo_root=repo_root)

    assert preflight.lane == "repair"
    assert preflight.install_shape_present is False
    assert preflight.next_command == "./.odylith/bin/odylith doctor --repo-root . --repair"


def test_start_preflight_treats_missing_first_turn_readiness_artifacts_as_repair(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    (repo_root / ".odylith" / "install.json").unlink()
    (repo_root / "odylith" / "runtime" / "source" / "product-version.v1.json").unlink()

    preflight = evaluate_start_preflight(repo_root=repo_root)

    assert preflight.lane == "repair"
    assert "install state missing" in preflight.reason
    assert "product version pin missing" in preflight.reason
    assert preflight.next_command == "./.odylith/bin/odylith doctor --repo-root . --repair"


def test_install_bundle_preserves_existing_customer_truth_and_shell_source(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)

    (repo_root / "odylith" / "radar" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "radar" / "source" / "INDEX.md").write_text("# Radar Index\n", encoding="utf-8")
    (repo_root / "odylith" / "runtime" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "runtime" / "source" / "tooling_shell.v1.json").write_text(
        json.dumps({"shell_repo_label": "Repo · Orion", "maintainer_notes": [{"note_id": "N-1"}]}, indent=2) + "\n",
        encoding="utf-8",
    )

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    assert (repo_root / "odylith" / "radar" / "source" / "INDEX.md").read_text(encoding="utf-8") == "# Radar Index\n"
    shell_payload = json.loads((repo_root / "odylith" / "runtime" / "source" / "tooling_shell.v1.json").read_text(encoding="utf-8"))
    assert shell_payload["shell_repo_label"] == "Repo · Orion"
    assert shell_payload["maintainer_notes"] == [{"note_id": "N-1"}]


def test_upgrade_install_resyncs_consumer_guidance_and_skills(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    (repo_root / "odylith" / "AGENTS.md").write_text("stale consumer guidance\n", encoding="utf-8")
    (repo_root / "odylith" / "radar" / "source" / "CLAUDE.md").unlink()
    (repo_root / "odylith" / "skills" / "odylith-subagent-router" / "SKILL.md").unlink()
    (repo_root / ".codex" / "config.toml").unlink()
    (repo_root / ".agents" / "skills" / "odylith-start" / "SKILL.md").unlink()
    stale_codex_skill = repo_root / ".agents" / "skills" / "odylith-subagent-router" / "SKILL.md"
    stale_codex_skill.parent.mkdir(parents=True, exist_ok=True)
    stale_codex_skill.write_text("# stale shim\n", encoding="utf-8")

    upgrade_install(repo_root=repo_root, release_repo="odylith/odylith")

    guidance_text = (repo_root / "odylith" / "AGENTS.md").read_text(encoding="utf-8")
    assert "Before any substantive repo scan or code change outside trivial fixes, the agent must start from the repo-local Odylith entrypoint" in guidance_text
    assert "keep startup, fallback, routing, and packet-selection internals implicit" in guidance_text
    assert "the exact file/workstream, the bug under test, or the validation in flight" in guidance_text
    assert "If an earlier repo-local start attempt degraded but work can continue safely, do not narrate that history." in guidance_text
    assert "Keep normal commentary task-first and human." in guidance_text
    assert "reserve explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels" in guidance_text
    assert "At closeout, you may add at most one short `Odylith Assist:` line" in guidance_text
    assert "Prefer `**Odylith Assist:**` when Markdown formatting is available" in guidance_text
    assert "Lead with the user win" in guidance_text
    assert "link updated governance ids inline when they were actually changed" in guidance_text
    assert "frame the edge against `odylith_off` or the broader unguided path" in guidance_text
    assert "Ground the line in concrete observed counts, measured deltas, or validation outcomes" in guidance_text
    assert "Silence is better than filler." in guidance_text
    assert "keep Odylith grounding mostly in the background. Do not require a fixed visible prefix" not in guidance_text
    assert "Odylith grounding:" not in guidance_text
    assert "Odylith didn't return immediately" not in guidance_text
    assert "grounding Odylith is diagnosis authority, not blanket write authority" in guidance_text
    assert "Treat `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh` as writes" in guidance_text
    assert "If the slice is genuinely new and it is repo-owned non-product work, create the missing workstream and bound plan before non-trivial implementation" in guidance_text
    assert "Default to the nearest `AGENTS.md`, the repo-local launcher, and truthful `odylith ... --help` for routine backlog, plan, bug, spec, component, and diagram upkeep." in guidance_text
    assert "When a routine governance task already maps to a first-class CLI family such as `odylith bug capture`, `odylith backlog create`, `odylith component register`, `odylith atlas scaffold`, or `odylith compass log`" in guidance_text
    assert "rerender only the owned surface" in guidance_text
    assert "Codex and Claude Code share the same default Odylith lane" in guidance_text
    assert "## Common Fast Paths" in guidance_text
    assert "./.odylith/bin/odylith radar refresh --repo-root ." in guidance_text
    assert "./.odylith/bin/odylith registry refresh --repo-root ." in guidance_text
    assert "./.odylith/bin/odylith casebook refresh --repo-root ." in guidance_text
    assert "./.odylith/bin/odylith atlas refresh --repo-root . --atlas-sync" in guidance_text
    assert "./.odylith/bin/odylith compass refresh --repo-root . --wait" in guidance_text
    assert "./.odylith/bin/odylith codex compatibility --repo-root ." in guidance_text
    assert "## Specialist Skills" in guidance_text
    assert (repo_root / "odylith" / "radar" / "source" / "CLAUDE.md").is_file()
    assert (repo_root / "odylith" / "skills" / "odylith-subagent-router" / "SKILL.md").is_file()
    assert (repo_root / ".codex" / "config.toml").is_file()
    assert (repo_root / ".agents" / "skills" / "odylith-start" / "SKILL.md").is_file()
    assert not (repo_root / ".agents" / "skills" / "odylith-subagent-router" / "SKILL.md").exists()


def test_install_bundle_product_repo_preserves_source_owned_odylith_guidance_and_activates_maintainer_overlay(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root)
    original_guidance = (repo_root / "odylith" / "AGENTS.md").read_text(encoding="utf-8")

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    assert (repo_root / "odylith" / "AGENTS.md").read_text(encoding="utf-8") == original_guidance
    root_agents = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
    assert "odylith/maintainer/AGENTS.md" in root_agents
    assert "Before any substantive repo scan or code change outside trivial fixes, the agent must start from the repo-local Odylith entrypoint" in root_agents
    assert "keep startup, fallback, routing, and packet-selection internals implicit" in root_agents
    assert "the exact file/workstream, the bug under test, or the validation in flight" in root_agents
    assert "If an earlier repo-local start attempt degraded but work can continue safely, do not narrate that history." in root_agents
    assert "Keep normal commentary task-first and human." in root_agents
    assert "reserve explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels" in root_agents
    assert "At closeout, you may add at most one short `Odylith Assist:` line" in root_agents
    assert "Prefer `**Odylith Assist:**` when Markdown formatting is available" in root_agents
    assert "Lead with the user win" in root_agents
    assert "link updated governance ids inline when they were actually changed" in root_agents
    assert "frame the edge against `odylith_off` or the broader unguided path" in root_agents
    assert "Ground the line in concrete observed counts, measured deltas, or validation outcomes" in root_agents
    assert "Silence is better than filler." in root_agents
    assert "keep Odylith grounding mostly in the background. Do not require a fixed visible prefix" not in root_agents
    assert "Odylith grounding:" not in root_agents
    assert "Odylith didn't return immediately" not in root_agents
    assert "search existing workstream, plan, bug, component, diagram, and recent session/Compass context first" in root_agents


def test_upgrade_backfills_odylith_state_root_in_gitignore(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    (repo_root / ".git").mkdir()

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    (repo_root / ".gitignore").unlink()

    upgrade_install(repo_root=repo_root, release_repo="odylith/odylith")

    assert (repo_root / ".gitignore").read_text(encoding="utf-8") == (
        "/.odylith/\n"
        "/odylith/compass/runtime/refresh-state.v1.json\n"
    )


def test_install_bundle_persists_existing_runtime_verification_marker(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    verification = {
        "runtime_bundle_sha256": "runtime",
        "wheel_sha256": "wheel",
    }
    _seed_runtime_with_verification(repo_root, version="1.2.3", verification=verification)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    state = load_install_state(repo_root=repo_root)
    assert state["installed_versions"]["1.2.3"]["verification"] == verification


def test_upgrade_leaves_customer_truth_untouched_and_only_refreshes_managed_guidelines(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    truth_path = repo_root / "odylith" / "radar" / "source" / "INDEX.md"
    truth_path.parent.mkdir(parents=True, exist_ok=True)
    truth_path.write_text("# Customer Radar\n", encoding="utf-8")
    shell_source_path = repo_root / "odylith" / "runtime" / "source" / "tooling_shell.v1.json"
    shell_source_path.unlink()
    guidance_path = repo_root / "odylith" / "agents-guidelines" / "UPGRADE_AND_RECOVERY.md"
    guidance_path.write_text("stale guidance\n", encoding="utf-8")
    brand_manifest_path = repo_root / "odylith" / "surfaces" / "brand" / "manifest.json"
    brand_manifest_path.write_text('{"custom": true}\n', encoding="utf-8")

    staged_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.4"
    staged_python = staged_root / "bin" / "python"
    staged_python.parent.mkdir(parents=True, exist_ok=True)
    staged_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    staged_python.chmod(0o755)

    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: SimpleNamespace(
            version="1.2.4",
            manifest={"repo_schema_version": 1, "migration_required": False},
            python=staged_python,
            root=staged_root,
            verification={"wheel_sha256": "abc123"},
        ),
    )
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        lambda **kwargs: SimpleNamespace(version="1.2.4"),
    )

    summary = upgrade_install(
        repo_root=repo_root,
        release_repo="odylith/odylith",
        version="1.2.4",
        write_pin=True,
    )

    assert summary.active_version == "1.2.4"
    assert truth_path.read_text(encoding="utf-8") == "# Customer Radar\n"
    assert not shell_source_path.exists()
    assert brand_manifest_path.read_text(encoding="utf-8") == '{"custom": true}\n'
    assert guidance_path.read_text(encoding="utf-8") == (
        (REPO_ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "agents-guidelines" / "UPGRADE_AND_RECOVERY.md")
        .read_text(encoding="utf-8")
    )


def test_upgrade_rejects_missing_repo_pin_without_explicit_write_pin(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    (repo_root / "odylith" / "runtime" / "source" / "product-version.v1.json").unlink()

    try:
        upgrade_install(repo_root=repo_root, release_repo="odylith/odylith")
    except ValueError as exc:
        assert "repo pin missing" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected missing repo pin to fail closed")


def test_install_bundle_replaces_source_local_override_with_real_version(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root)
    source_root = _write_fake_source_checkout(tmp_path)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    upgrade_install(repo_root=repo_root, release_repo="odylith/odylith", source_repo=source_root)

    summary = install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    state = load_install_state(repo_root=repo_root)
    assert summary.version == "1.2.3"
    assert state["active_version"] == "1.2.3"
    assert state["detached"] is False
    assert (repo_root / ".odylith" / "runtime" / "current").resolve().name == "1.2.3"


def test_source_repo_upgrade_is_detached_override_and_preserves_last_known_good(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root)
    source_root = _write_fake_source_checkout(tmp_path)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    summary = upgrade_install(repo_root=repo_root, release_repo="odylith/odylith", source_repo=source_root)

    state = load_install_state(repo_root=repo_root)
    status = version_status(repo_root=repo_root)
    assert summary.active_version == "source-local"
    assert summary.pin_changed is False
    assert state["active_version"] == "source-local"
    assert state["detached"] is True
    assert state["last_known_good_version"] == "1.2.3"
    assert status.detached is True
    assert status.last_known_good_version == "1.2.3"
    assert status.diverged_from_pin is True


def test_source_repo_upgrade_normalizes_current_runtime_symlink_fallback(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root)
    source_root = _write_fake_source_checkout(tmp_path)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    current_python = repo_root / ".odylith" / "runtime" / "current" / "bin" / "python"
    monkeypatch.setattr(install_manager_module.sys, "executable", str(current_python))

    summary = upgrade_install(repo_root=repo_root, release_repo="odylith/odylith", source_repo=source_root)

    assert summary.active_version == "source-local"
    wrapper_text = (repo_root / ".odylith" / "runtime" / "versions" / "source-local" / "bin" / "python").read_text(
        encoding="utf-8"
    )
    launcher_text = (repo_root / ".odylith" / "bin" / "odylith").read_text(encoding="utf-8")

    assert str(repo_root / ".odylith" / "runtime" / "versions" / "1.2.3" / "bin" / "python") in wrapper_text
    assert "runtime/current/bin/python" not in wrapper_text
    assert f'fallback_source_root="{source_root / "src"}"' in launcher_text
    assert f'fallback_python="{repo_root / ".odylith" / "runtime" / "versions" / "source-local" / "bin" / "python"}"' not in launcher_text


def test_version_status_prefers_live_runtime_over_stale_install_state(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root)
    source_root = _write_fake_source_checkout(tmp_path)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    upgrade_install(repo_root=repo_root, release_repo="odylith/odylith", source_repo=source_root)

    stale_state = load_install_state(repo_root=repo_root)
    stale_state["active_version"] = "1.2.3"
    stale_state["detached"] = False
    write_install_state(repo_root=repo_root, payload=stale_state)

    status = version_status(repo_root=repo_root)

    assert (repo_root / ".odylith" / "runtime" / "current").resolve().name == "source-local"
    assert status.active_version == "source-local"
    assert status.detached is True
    assert status.diverged_from_pin is True
    assert status.last_known_good_version == "1.2.3"
    assert status.posture == "detached_source_local"
    assert status.runtime_source == "source_checkout"
    assert status.release_eligible is False


def test_doctor_bundle_reports_detached_override_from_live_runtime_when_install_state_is_stale(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root)
    source_root = _write_fake_source_checkout(tmp_path)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    upgrade_install(repo_root=repo_root, release_repo="odylith/odylith", source_repo=source_root)

    stale_state = load_install_state(repo_root=repo_root)
    stale_state["active_version"] = "1.2.3"
    stale_state["detached"] = False
    write_install_state(repo_root=repo_root, payload=stale_state)

    healthy, message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=False)

    assert healthy is True
    assert "detached local override" in message.lower()
    assert "source-local" in str((repo_root / ".odylith" / "runtime" / "current").resolve())


def test_doctor_bundle_reports_unverified_wrapped_runtime_for_product_repo(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    healthy, message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=False)
    status = version_status(repo_root=repo_root)

    assert healthy is True
    assert status.repo_role == "product_repo"
    assert status.runtime_source == "wrapped_runtime"
    assert "local wrapper" in status.runtime_source_detail.lower()
    assert status.runtime_trust_degraded is False
    assert status.release_eligible is False
    assert "wrapped runtime" in message.lower()
    assert "not release-eligible" in message.lower()


def test_doctor_bundle_reports_trust_degraded_wrapped_runtime_consistently_with_version(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    staged_root, staged_python = _seed_verified_release_runtime(repo_root, version="1.2.3")
    runtime.switch_runtime(repo_root=repo_root, target=staged_root)
    runtime.ensure_launcher(repo_root=repo_root, fallback_python=staged_python)

    state = load_install_state(repo_root=repo_root)
    state["active_version"] = "1.2.3"
    state["detached"] = False
    state["installed_versions"]["1.2.3"] = {
        "runtime_root": str(staged_root),
        "verification": {
            "runtime_bundle_sha256": "runtime-1.2.3",
            "wheel_sha256": "wheel-1.2.3",
        },
    }
    write_install_state(repo_root=repo_root, payload=state)

    (staged_root / "rogue.txt").write_text("oops\n", encoding="utf-8")

    healthy, message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=False)
    status = version_status(repo_root=repo_root)

    assert status.runtime_source == "wrapped_runtime"
    assert status.runtime_trust_degraded is True
    assert "managed runtime trust is degraded" in status.runtime_source_detail.lower()
    assert healthy is True
    assert "healthy but trust-degraded" in message.lower()
    assert "not release-eligible" in message.lower()
    assert status.runtime_source_detail in message
    assert "repo launcher managed runtime tree entry unexpected" not in message
    assert "bootstrap launcher managed runtime tree entry unexpected" not in message


def test_source_repo_upgrade_rejects_explicit_target_version(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root)
    source_root = _write_fake_source_checkout(tmp_path)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    try:
        upgrade_install(
            repo_root=repo_root,
            release_repo="odylith/odylith",
            version="1.2.4",
            source_repo=source_root,
        )
    except ValueError as exc:
        assert "--to is not supported with --source-repo" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected explicit target to fail for source-local upgrade")


def test_source_repo_upgrade_is_rejected_for_consumer_repos(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    source_root = _write_fake_source_checkout(tmp_path)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    try:
        upgrade_install(
            repo_root=repo_root,
            release_repo="odylith/odylith",
            source_repo=source_root,
        )
    except ValueError as exc:
        assert "--source-repo is only supported for the Odylith product repo" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected consumer repo source-local activation to fail")


def test_doctor_bundle_repairs_consumer_source_local_lane_back_to_pinned_release(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    source_root = _write_fake_source_checkout(tmp_path)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    runtime.ensure_wrapped_runtime(
        repo_root=repo_root,
        version="source-local",
        fallback_python=repo_root / ".odylith" / "runtime" / "versions" / "1.2.3" / "bin" / "python",
        source_root=source_root,
        allow_host_python_fallback=False,
    )
    state = load_install_state(repo_root=repo_root)
    state["active_version"] = "source-local"
    state["detached"] = True
    state["last_known_good_version"] = "1.2.3"
    write_install_state(repo_root=repo_root, payload=state)

    healthy, message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=False)

    assert healthy is False
    assert "Consumer repos cannot activate the detached source-local maintainer lane" in message

    repaired, repaired_message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=True)

    status = version_status(repo_root=repo_root)
    repaired_state = load_install_state(repo_root=repo_root)
    launcher_text = (repo_root / ".odylith" / "bin" / "odylith").read_text(encoding="utf-8")
    assert repaired is True
    assert "repair completed" in repaired_message.lower()
    assert status.active_version == "1.2.3"
    assert status.runtime_source == "pinned_runtime"
    assert status.posture == "pinned_release"
    assert status.detached is False
    assert repaired_state["active_version"] == "1.2.3"
    assert repaired_state["detached"] is False
    assert (repo_root / ".odylith" / "runtime" / "current").resolve().name == "1.2.3"
    assert "source-local" not in launcher_text


def test_doctor_bundle_repairs_missing_bootstrap_paths_without_copying_product_payload(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    (repo_root / "odylith" / "runtime" / "source" / "tooling_shell.v1.json").unlink()
    (repo_root / "odylith" / "atlas").rename(repo_root / "odylith" / "atlas.moved")
    (repo_root / "odylith" / "surfaces" / "brand" / "manifest.json").unlink()

    healthy, message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=True)

    assert healthy is True
    assert "repair completed" in message.lower()
    assert (repo_root / "odylith" / "runtime" / "source" / "tooling_shell.v1.json").is_file()
    assert (repo_root / "odylith" / "atlas" / "source").is_dir()
    assert (repo_root / "odylith" / "surfaces" / "brand" / "manifest.json").is_file()
    assert not (repo_root / "odylith" / "atlas" / "README.md").exists()


def test_doctor_bundle_detects_partial_starter_tree_and_repairs_it(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    (repo_root / "odylith" / "AGENTS.md").unlink()
    (repo_root / "odylith" / "CLAUDE.md").unlink()

    healthy, message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=False)
    assert healthy is False
    assert "starter tree missing" in message.lower()

    repaired, repaired_message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=True)
    assert repaired is True
    assert "repair completed" in repaired_message.lower()
    assert (repo_root / "odylith" / "AGENTS.md").is_file()
    assert (repo_root / "odylith" / "CLAUDE.md").is_file()


def test_doctor_bundle_recreates_real_repo_pin_after_source_local_override(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root)
    source_root = _write_fake_source_checkout(tmp_path)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    upgrade_install(repo_root=repo_root, release_repo="odylith/odylith", source_repo=source_root)
    (repo_root / "odylith" / "runtime" / "source" / "product-version.v1.json").unlink()

    healthy, message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=True)

    pin_payload = json.loads(
        (repo_root / "odylith" / "runtime" / "source" / "product-version.v1.json").read_text(encoding="utf-8")
    )
    assert healthy is True
    assert "detached local override" in message.lower()
    assert pin_payload["odylith_version"] == "1.2.3"


def test_doctor_bundle_clears_detached_mode_when_repair_falls_back_to_real_version(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root)
    source_root = _write_fake_source_checkout(tmp_path)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    upgrade_install(repo_root=repo_root, release_repo="odylith/odylith", source_repo=source_root)

    current_link = repo_root / ".odylith" / "runtime" / "current"
    source_runtime_root = current_link.resolve()
    current_link.unlink()
    shutil.rmtree(source_runtime_root)

    healthy, message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=True)

    status = version_status(repo_root=repo_root)
    state = load_install_state(repo_root=repo_root)
    assert healthy is True
    assert "detached local override" not in message.lower()
    assert status.detached is False
    assert status.active_version == "1.2.3"
    assert state["detached"] is False


def test_doctor_bundle_rehydrates_missing_trust_for_detached_product_repo_pin(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root)
    source_root = _write_fake_source_checkout(tmp_path)

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    _seed_runtime_with_verification(
        repo_root,
        version="1.2.3",
        verification={"runtime_bundle_sha256": "runtime-1.2.3", "wheel_sha256": "wheel-1.2.3"},
    )
    _write_fake_context_engine_pack(
        repo_root,
        target_root=(repo_root / ".odylith" / "runtime" / "current").resolve(),
        version="1.2.3",
        feature_pack_sha256="feature-pack-1.2.3",
    )
    managed_runtime_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    for name in ("python", "python3"):
        executable = managed_runtime_root / "bin" / name
        executable.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)
    runtime.write_managed_runtime_trust(
        repo_root=repo_root,
        version_root=managed_runtime_root,
        verification=runtime.runtime_verification_evidence(managed_runtime_root),
    )
    upgrade_install(repo_root=repo_root, release_repo="odylith/odylith", source_repo=source_root)
    runtime.ensure_wrapped_runtime(
        repo_root=repo_root,
        version="source-local",
        fallback_python=repo_root / ".odylith" / "runtime" / "versions" / "1.2.3" / "bin" / "python",
        source_root=source_root,
        allow_host_python_fallback=True,
    )

    trust_root = repo_root / ".odylith" / "trust" / "managed-runtime-trust"
    (trust_root / "1.2.3.env").unlink()
    (trust_root / "1.2.3.tree.v1.json").unlink()

    preflight_healthy, preflight_message = doctor_bundle(
        repo_root=repo_root,
        bundle_root=tmp_path / "unused-bundle",
        repair=False,
    )
    assert preflight_healthy is False
    assert "unverified managed runtime" in preflight_message.lower()

    healthy, message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=True)

    status = version_status(repo_root=repo_root)
    assert healthy is True
    assert "repair completed" in message.lower()
    assert status.active_version == "source-local"
    assert status.detached is True
    assert (trust_root / "1.2.3.env").is_file()
    assert (trust_root / "1.2.3.tree.v1.json").is_file()


def test_doctor_bundle_repairs_consumer_runtime_with_verified_release_not_host_python(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    current_link = repo_root / ".odylith" / "runtime" / "current"
    broken_root = current_link.resolve()
    current_link.unlink()
    shutil.rmtree(broken_root)

    healthy, message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=True)

    status = version_status(repo_root=repo_root)
    launcher_text = (repo_root / ".odylith" / "bin" / "odylith").read_text(encoding="utf-8")
    assert healthy is True
    assert "repair completed" in message.lower()
    assert status.active_version == "1.2.3"
    assert status.runtime_source == "pinned_runtime"
    assert "exec \"/usr/bin" not in launcher_text
    assert "source-local" not in launcher_text


def test_doctor_bundle_repair_backfills_legacy_casebook_bug_ids(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    retained, missing = _seed_legacy_casebook_bug_pair(repo_root)

    healthy, message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=True)
    index_text = (repo_root / "odylith" / "casebook" / "bugs" / "INDEX.md").read_text(encoding="utf-8")

    assert healthy is True
    assert "repair completed" in message.lower()
    assert "- Bug ID: CB-007" in retained.read_text(encoding="utf-8")
    assert "- Bug ID: CB-008" in missing.read_text(encoding="utf-8")
    assert "| CB-008 | 2026-03-26 | Missing bug | P1 | tooling | Open | [2026-03-26-missing-bug.md](2026-03-26-missing-bug.md) |" in index_text


def test_doctor_bundle_repairs_product_repo_with_source_aware_wrapped_runtime(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root)
    (repo_root / "src" / "odylith" / "__init__.py").write_text("__version__ = '1.2.3'\n", encoding="utf-8")
    (repo_root / "src" / "odylith" / "cli.py").write_text("raise SystemExit(0)\n", encoding="utf-8")

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    shutil.rmtree(repo_root / ".odylith")

    healthy, message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=True)

    launcher_path = repo_root / ".odylith" / "bin" / "odylith"
    launcher_text = (repo_root / ".odylith" / "bin" / "odylith").read_text(encoding="utf-8")
    runtime_python_text = (
        repo_root / ".odylith" / "runtime" / "versions" / "repaired-local" / "bin" / "python"
    ).read_text(encoding="utf-8")
    status = version_status(repo_root=repo_root)
    assert healthy is True
    assert "repair completed" in message.lower()
    assert status.repo_role == "product_repo"
    assert status.runtime_source == "wrapped_runtime"
    assert 'current_python="$state_root/runtime/current/bin/python"' in launcher_text
    assert str(Path(sys.executable)) in runtime_python_text
    assert 'export PYTHONPATH="' in runtime_python_text
    assert ' -I "$@"' not in runtime_python_text
    completed = subprocess.run(
        [str(launcher_path), "version", "--repo-root", "."],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0


def test_doctor_bundle_repeated_product_repo_repair_keeps_tracked_guidance_unchanged(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root)
    (repo_root / "src" / "odylith" / "__init__.py").write_text("__version__ = '1.2.3'\n", encoding="utf-8")
    (repo_root / "src" / "odylith" / "cli.py").write_text("raise SystemExit(0)\n", encoding="utf-8")

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    shutil.rmtree(repo_root / ".odylith")
    healthy, message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=True)

    tracked_paths = (
        repo_root / "AGENTS.md",
        repo_root / "odylith" / "AGENTS.md",
        repo_root / "odylith" / "maintainer" / "AGENTS.md",
        repo_root / "odylith" / "runtime" / "source" / "product-version.v1.json",
        repo_root / "odylith" / "runtime" / "source" / "tooling_shell.v1.json",
    )
    before = {path: path.read_text(encoding="utf-8") for path in tracked_paths}

    second_healthy, second_message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=True)
    after = {path: path.read_text(encoding="utf-8") for path in tracked_paths}

    assert healthy is True
    assert "repair completed" in message.lower()
    assert second_healthy is True
    assert "healthy" in second_message.lower() or "repair completed" in second_message.lower()
    assert after == before


def test_doctor_bundle_product_repo_repair_keeps_repo_root_agents_source_truth_unchanged(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    expected_agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    (repo_root / "AGENTS.md").write_text(expected_agents, encoding="utf-8")
    _write_product_repo_shape(repo_root)
    (repo_root / "src" / "odylith" / "__init__.py").write_text("__version__ = '1.2.3'\n", encoding="utf-8")
    (repo_root / "src" / "odylith" / "cli.py").write_text("raise SystemExit(0)\n", encoding="utf-8")

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    assert (repo_root / "AGENTS.md").read_text(encoding="utf-8") == expected_agents

    shutil.rmtree(repo_root / ".odylith")
    healthy, message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=True)

    assert healthy is True
    assert "repair completed" in message.lower()
    assert (repo_root / "AGENTS.md").read_text(encoding="utf-8") == expected_agents


def test_doctor_bundle_reset_local_state_clears_mutable_state(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    poisoned_cache = repo_root / ".odylith" / "cache" / "odylith-context-engine" / "guidance" / "compiled-catalog-v1.json"
    poisoned_cache.parent.mkdir(parents=True, exist_ok=True)
    poisoned_cache.write_text("{not-json", encoding="utf-8")

    poisoned_memory = repo_root / ".odylith" / "runtime" / "odylith-memory" / "tantivy" / "meta.json"
    poisoned_memory.parent.mkdir(parents=True, exist_ok=True)
    poisoned_memory.write_text("poisoned\n", encoding="utf-8")

    poisoned_router = repo_root / ".odylith" / "subagent_router" / "tuning.v1.json"
    poisoned_router.parent.mkdir(parents=True, exist_ok=True)
    poisoned_router.write_text('{"version":"v1","profile_bias":{"mini":999}}', encoding="utf-8")

    poisoned_brief_cache = repo_root / ".odylith" / "compass" / "standup-brief-cache.v8.json"
    poisoned_brief_cache.parent.mkdir(parents=True, exist_ok=True)
    poisoned_brief_cache.write_text("bad-cache\n", encoding="utf-8")

    healthy, message = doctor_bundle(
        repo_root=repo_root,
        bundle_root=tmp_path / "unused-bundle",
        repair=True,
        reset_local_state=True,
    )

    assert healthy is True
    assert "repair completed" in message.lower()
    assert "local mutable" in message.lower()
    assert not poisoned_cache.exists()
    assert not poisoned_memory.exists()
    assert not poisoned_router.exists()
    assert not poisoned_brief_cache.exists()
    assert (repo_root / ".odylith" / "install.json").is_file()
    assert (repo_root / ".odylith" / "runtime" / "current").is_symlink()


def test_uninstall_bundle_detaches_but_preserves_customer_truth_and_local_state(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    uninstall_bundle(repo_root=repo_root)

    assert (repo_root / "odylith").is_dir()
    assert (repo_root / "odylith" / "AGENTS.md").is_file()
    assert (repo_root / ".odylith").is_dir()
    state = load_install_state(repo_root=repo_root)
    assert state["detached"] is True
    assert state["integration_enabled"] is False
    assert "<!-- odylith-scope:start -->" not in (repo_root / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- odylith-scope:start -->" not in (repo_root / "CLAUDE.md").read_text(encoding="utf-8")


def test_rollback_install_returns_to_previous_verified_version(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    staged_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.4"
    staged_python = staged_root / "bin" / "python"
    staged_python.parent.mkdir(parents=True, exist_ok=True)
    staged_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    staged_python.chmod(0o755)

    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: SimpleNamespace(
            version="1.2.4",
            manifest={"repo_schema_version": 1, "migration_required": False},
            python=staged_python,
            root=staged_root,
            verification={"wheel_sha256": "abc123"},
        ),
    )
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    upgrade_install(
        repo_root=repo_root,
        release_repo="odylith/odylith",
        version="1.2.4",
        write_pin=True,
    )

    summary = rollback_install(repo_root=repo_root)

    state = load_install_state(repo_root=repo_root)
    assert summary.previous_version == "1.2.4"
    assert summary.active_version == "1.2.3"
    assert summary.diverged_from_pin is True
    assert summary.pinned_version == "1.2.4"
    assert state["active_version"] == "1.2.3"


def test_rollback_install_allows_legacy_repo_local_venv_runtime_paths(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    legacy_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    legacy_metadata = legacy_root / "runtime-metadata.json"
    if legacy_metadata.exists():
        legacy_metadata.unlink()
    host_python = tmp_path / "host-python" / "python3.13"
    host_python.parent.mkdir(parents=True, exist_ok=True)
    host_python.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    host_python.chmod(0o755)
    for name in ("python", "python3"):
        link_path = legacy_root / "bin" / name
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
        link_path.symlink_to("python3.13")
    python313 = legacy_root / "bin" / "python3.13"
    if python313.exists() or python313.is_symlink():
        python313.unlink()
    python313.symlink_to(host_python)
    (legacy_root / "pyvenv.cfg").write_text("version = 3.13.12\n", encoding="utf-8")

    staged_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.4"
    staged_python = staged_root / "bin" / "python"
    staged_python.parent.mkdir(parents=True, exist_ok=True)
    staged_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    staged_python.chmod(0o755)

    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: SimpleNamespace(
            version="1.2.4",
            manifest={"repo_schema_version": 1, "migration_required": False},
            python=staged_python,
            root=staged_root,
            verification={"wheel_sha256": "abc123"},
        ),
    )
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    upgrade_install(
        repo_root=repo_root,
        release_repo="odylith/odylith",
        version="1.2.4",
        write_pin=True,
    )

    summary = rollback_install(repo_root=repo_root)

    assert summary.active_version == "1.2.3"
    launcher_text = (repo_root / ".odylith" / "bin" / "odylith").read_text(encoding="utf-8")
    assert str(legacy_root / "bin" / "python") in launcher_text
    assert str(host_python) not in launcher_text


def test_upgrade_smoke_runs_with_scrubbed_python_environment(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    staged_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.4"
    staged_python = staged_root / "bin" / "python"
    staged_python.parent.mkdir(parents=True, exist_ok=True)
    staged_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    staged_python.chmod(0o755)

    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: SimpleNamespace(
            version="1.2.4",
            manifest={"repo_schema_version": 1, "migration_required": False},
            python=staged_python,
            root=staged_root,
            verification={"wheel_sha256": "abc123"},
        ),
    )

    captured: dict[str, object] = {}

    def _fake_run(*args, **kwargs):  # noqa: ANN001
        captured["env"] = kwargs.get("env")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(install_manager_module.subprocess, "run", _fake_run)
    monkeypatch.setenv("VIRTUAL_ENV", "/tmp/consumer-venv")
    monkeypatch.setenv("CONDA_PREFIX", "/tmp/conda")
    monkeypatch.setenv("CONDA_DEFAULT_ENV", "consumer")
    monkeypatch.setenv("PYTHONHOME", "/tmp/python-home")
    monkeypatch.setenv("__PYVENV_LAUNCHER__", "/tmp/launcher")
    monkeypatch.setenv("PYTHONPATH", "/tmp/consumer-src")

    upgrade_install(
        repo_root=repo_root,
        release_repo="odylith/odylith",
        version="1.2.4",
        write_pin=True,
    )

    env = captured["env"]
    assert isinstance(env, dict)
    assert env["PYTHONNOUSERSITE"] == "1"
    assert "VIRTUAL_ENV" not in env
    assert "CONDA_PREFIX" not in env
    assert "CONDA_DEFAULT_ENV" not in env
    assert "PYTHONHOME" not in env
    assert "__PYVENV_LAUNCHER__" not in env
    assert "PYTHONPATH" not in env


def test_install_smoke_runs_with_scrubbed_python_environment(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)

    captured: dict[str, object] = {}

    def _fake_run(*args, **kwargs):  # noqa: ANN001
        captured["env"] = kwargs.get("env")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(install_manager_module.subprocess, "run", _fake_run)
    monkeypatch.setenv("VIRTUAL_ENV", "/tmp/consumer-venv")
    monkeypatch.setenv("CONDA_PREFIX", "/tmp/conda")
    monkeypatch.setenv("CONDA_DEFAULT_ENV", "consumer")
    monkeypatch.setenv("PYTHONHOME", "/tmp/python-home")
    monkeypatch.setenv("__PYVENV_LAUNCHER__", "/tmp/launcher")
    monkeypatch.setenv("PYTHONPATH", "/tmp/consumer-src")

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    env = captured["env"]
    assert isinstance(env, dict)
    assert env["PYTHONNOUSERSITE"] == "1"
    assert "VIRTUAL_ENV" not in env
    assert "CONDA_PREFIX" not in env
    assert "CONDA_DEFAULT_ENV" not in env
    assert "PYTHONHOME" not in env
    assert "__PYVENV_LAUNCHER__" not in env
    assert "PYTHONPATH" not in env


def test_install_bundle_clears_partial_activation_when_first_install_smoke_fails(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)

    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="simulated install smoke failure"),
    )

    with pytest.raises(RuntimeError, match="post-activation smoke check failed"):
        install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    current = repo_root / ".odylith" / "runtime" / "current"
    launcher = repo_root / ".odylith" / "bin" / "odylith"
    version_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    state = load_install_state(repo_root=repo_root)

    assert not current.exists()
    assert not current.is_symlink()
    assert not launcher.exists()
    assert version_root.is_dir()
    assert state["active_version"] == ""


def test_rollback_smoke_runs_with_scrubbed_python_environment(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    staged_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.4"
    staged_python = staged_root / "bin" / "python"
    staged_python.parent.mkdir(parents=True, exist_ok=True)
    staged_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    staged_python.chmod(0o755)

    smoke_envs: list[dict[str, str]] = []

    def _fake_run(*args, **kwargs):  # noqa: ANN001
        env = kwargs.get("env")
        if isinstance(env, dict):
            smoke_envs.append(env)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: SimpleNamespace(
            version="1.2.4",
            manifest={"repo_schema_version": 1, "migration_required": False},
            python=staged_python,
            root=staged_root,
            verification={"wheel_sha256": "abc123"},
        ),
    )
    monkeypatch.setattr(install_manager_module.subprocess, "run", _fake_run)
    monkeypatch.setenv("VIRTUAL_ENV", "/tmp/consumer-venv")
    monkeypatch.setenv("PYTHONPATH", "/tmp/consumer-src")

    upgrade_install(
        repo_root=repo_root,
        release_repo="odylith/odylith",
        version="1.2.4",
        write_pin=True,
    )
    rollback_install(repo_root=repo_root)

    assert len(smoke_envs) >= 2
    rollback_env = smoke_envs[-1]
    assert rollback_env["PYTHONNOUSERSITE"] == "1"
    assert "VIRTUAL_ENV" not in rollback_env
    assert "PYTHONPATH" not in rollback_env


def test_upgrade_same_version_is_a_noop_for_verified_full_stack_runtime(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    prior_state = load_install_state(repo_root=repo_root)
    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        lambda **kwargs: SimpleNamespace(version="1.2.3"),
    )
    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("same-version upgrade should not restage the live runtime")),
    )
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    summary = upgrade_install(repo_root=repo_root, release_repo="odylith/odylith")
    state = load_install_state(repo_root=repo_root)

    assert summary.active_version == "1.2.3"
    assert summary.previous_version == "1.2.3"
    assert state["activation_history"] == prior_state["activation_history"] == ["1.2.3"]
    assert state["active_version"] == "1.2.3"


def test_upgrade_same_version_backfills_legacy_casebook_bug_ids(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    retained, missing = _seed_legacy_casebook_bug_pair(repo_root)

    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        lambda **kwargs: SimpleNamespace(version="1.2.3"),
    )
    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("same-version upgrade should not restage the live runtime")),
    )
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    summary = upgrade_install(repo_root=repo_root, release_repo="odylith/odylith")
    index_text = (repo_root / "odylith" / "casebook" / "bugs" / "INDEX.md").read_text(encoding="utf-8")

    assert summary.active_version == "1.2.3"
    assert "- Bug ID: CB-007" in retained.read_text(encoding="utf-8")
    assert "- Bug ID: CB-008" in missing.read_text(encoding="utf-8")
    assert "| CB-008 | 2026-03-26 | Missing bug | P1 | tooling | Open | [2026-03-26-missing-bug.md](2026-03-26-missing-bug.md) |" in index_text
    assert "| CB-007 | 2026-03-25 | Existing bug | P2 | dashboard | Closed | [2026-03-25-existing-bug.md](2026-03-25-existing-bug.md) |" in index_text


def test_consumer_upgrade_without_target_advances_to_latest_and_updates_pin(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    staged_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.4"
    staged_python = staged_root / "bin" / "python"
    staged_python.parent.mkdir(parents=True, exist_ok=True)
    staged_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    staged_python.chmod(0o755)

    captured: dict[str, object] = {}

    def _fake_fetch_release(**kwargs):  # noqa: ANN003
        captured["fetch_version"] = kwargs["version"]
        return SimpleNamespace(version="1.2.4")

    def _fake_install_release_runtime(**kwargs):  # noqa: ANN003
        captured["install_version"] = kwargs["version"]
        return SimpleNamespace(
            version="1.2.4",
            manifest={"repo_schema_version": 1, "migration_required": False},
            python=staged_python,
            root=staged_root,
            verification={"wheel_sha256": "abc123"},
        )

    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        _fake_fetch_release,
    )
    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        _fake_install_release_runtime,
    )
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    summary = upgrade_install(repo_root=repo_root, release_repo="odylith/odylith")

    pin = load_version_pin(repo_root=repo_root)
    assert captured["fetch_version"] == "latest"
    assert captured["install_version"] == "1.2.4"
    assert summary.active_version == "1.2.4"
    assert summary.pin_changed is True
    assert summary.pinned_version == "1.2.4"
    assert pin is not None
    assert pin.odylith_version == "1.2.4"


def test_consumer_upgrade_backfills_legacy_casebook_bug_ids_during_runtime_activation(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    retained, missing = _seed_legacy_casebook_bug_pair(repo_root)

    staged_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.4"
    staged_python = staged_root / "bin" / "python"
    staged_python.parent.mkdir(parents=True, exist_ok=True)
    staged_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    staged_python.chmod(0o755)

    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        lambda **kwargs: SimpleNamespace(version="1.2.4"),
    )
    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: SimpleNamespace(
            version="1.2.4",
            manifest={"repo_schema_version": 1, "migration_required": False},
            python=staged_python,
            root=staged_root,
            verification={"wheel_sha256": "abc123"},
        ),
    )
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    summary = upgrade_install(repo_root=repo_root, release_repo="odylith/odylith")
    index_text = (repo_root / "odylith" / "casebook" / "bugs" / "INDEX.md").read_text(encoding="utf-8")

    assert summary.active_version == "1.2.4"
    assert summary.previous_version == "1.2.3"
    assert "- Bug ID: CB-007" in retained.read_text(encoding="utf-8")
    assert "- Bug ID: CB-008" in missing.read_text(encoding="utf-8")
    assert "| CB-008 | 2026-03-26 | Missing bug | P1 | tooling | Open | [2026-03-26-missing-bug.md](2026-03-26-missing-bug.md) |" in index_text


def test_product_repo_upgrade_without_target_keeps_tracked_pin(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root, version="1.2.3")

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    _seed_runtime_with_verification(
        repo_root,
        version="1.2.3",
        verification={"runtime_bundle_sha256": "runtime-1.2.3", "wheel_sha256": "wheel-1.2.3"},
    )
    _write_fake_context_engine_pack(
        repo_root,
        target_root=(repo_root / ".odylith" / "runtime" / "current").resolve(),
        version="1.2.3",
        feature_pack_sha256="feature-pack-1.2.3",
    )

    captured: dict[str, object] = {}

    def _fake_fetch_release(**kwargs):  # noqa: ANN003
        captured["fetch_version"] = kwargs["version"]
        return SimpleNamespace(version="1.2.3")

    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        _fake_fetch_release,
    )
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    summary = upgrade_install(repo_root=repo_root, release_repo="odylith/odylith")

    assert captured["fetch_version"] == "1.2.3"
    assert summary.active_version == "1.2.3"
    assert summary.pin_changed is False
    assert summary.pinned_version == "1.2.3"


def test_upgrade_same_version_requires_doctor_repair_when_full_stack_pack_is_missing(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    current_runtime = (repo_root / ".odylith" / "runtime" / "current").resolve()
    (current_runtime / "runtime-feature-packs.v1.json").unlink()

    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        lambda **kwargs: SimpleNamespace(version="1.2.3"),
    )
    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("same-version upgrade should fail closed before restaging")),
    )

    with pytest.raises(ValueError, match="doctor --repo-root \\. --repair"):
        upgrade_install(repo_root=repo_root, release_repo="odylith/odylith")


def test_reinstall_install_repairs_same_version_runtime_when_upgrade_requires_doctor(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    current_runtime = (repo_root / ".odylith" / "runtime" / "current").resolve()
    (current_runtime / "runtime-feature-packs.v1.json").unlink()

    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            highlights=("Repair the pinned runtime safely.",),
            published_at="2026-03-30T18:00:00Z",
            tag="v1.2.3",
            html_url="https://example.com/releases/v1.2.3",
        ),
    )
    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            manifest={"repo_schema_version": 1, "migration_required": False},
            python=current_runtime / "bin" / "python",
            root=current_runtime,
            verification={"wheel_sha256": "abc123"},
        ),
    )

    def _fake_ensure_context_pack(**kwargs):  # noqa: ANN003
        _write_fake_context_engine_pack(
            repo_root,
            target_root=current_runtime,
            version="1.2.3",
            pack_id="odylith-context-engine",
            asset_name="odylith-context-engine.tar.gz",
            feature_pack_sha256="pack-1.2.3",
            payload_relative_path="lib/python3.13/site-packages/odylith_context_engine/__init__.py",
            payload_text="context-engine-pack\n",
        )
        return {"sha256": "pack-1.2.3"}

    monkeypatch.setattr(install_manager_module, "_ensure_managed_context_engine_pack", _fake_ensure_context_pack)
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    summary = reinstall_install(repo_root=repo_root, release_repo="odylith/odylith")

    pin = load_version_pin(repo_root=repo_root)
    assert summary.active_version == "1.2.3"
    assert summary.pinned_version == "1.2.3"
    assert summary.repaired is True
    assert summary.followed_latest is True
    assert pin is not None
    assert pin.odylith_version == "1.2.3"
    assert (current_runtime / "runtime-feature-packs.v1.json").is_file()


def test_reinstall_install_converges_repeatedly_with_stale_target_residue(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    current_runtime = (repo_root / ".odylith" / "runtime" / "current").resolve()
    (current_runtime / "runtime-feature-packs.v1.json").unlink()
    versions_dir = repo_root / ".odylith" / "runtime" / "versions"
    stale_backup = versions_dir / ".1.2.3.backup-stale"
    stale_backup.mkdir(parents=True, exist_ok=True)
    stale_stage = versions_dir / ".1.2.3.stage-stale"
    stale_stage.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            highlights=("Repair the pinned runtime safely.",),
            published_at="2026-03-30T18:00:00Z",
            tag="v1.2.3",
            html_url="https://example.com/releases/v1.2.3",
        ),
    )
    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            manifest={"repo_schema_version": 1, "migration_required": False},
            python=current_runtime / "bin" / "python",
            root=current_runtime,
            verification={"wheel_sha256": "abc123"},
        ),
    )

    def _fake_ensure_context_pack(**kwargs):  # noqa: ANN003
        _write_fake_context_engine_pack(
            repo_root,
            target_root=current_runtime,
            version="1.2.3",
            pack_id="odylith-context-engine",
            asset_name="odylith-context-engine.tar.gz",
            feature_pack_sha256="pack-1.2.3",
            payload_relative_path="lib/python3.13/site-packages/odylith_context_engine/__init__.py",
            payload_text="context-engine-pack\n",
        )
        return {"sha256": "pack-1.2.3"}

    monkeypatch.setattr(install_manager_module, "_ensure_managed_context_engine_pack", _fake_ensure_context_pack)
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    first = reinstall_install(repo_root=repo_root, release_repo="odylith/odylith")
    second = reinstall_install(repo_root=repo_root, release_repo="odylith/odylith")

    assert first.repaired is True
    assert second.repaired is True
    assert stale_backup.exists() is False
    assert stale_stage.exists() is False
    assert (current_runtime / "runtime-feature-packs.v1.json").is_file()


def test_reinstall_install_rejects_product_repo(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    _write_product_repo_shape(repo_root, version="1.2.3")

    with pytest.raises(ValueError, match="only supported for consumer repos"):
        reinstall_install(repo_root=repo_root, release_repo="odylith/odylith")


def test_upgrade_rejects_migration_required_release(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    staged_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.4"
    staged_python = staged_root / "bin" / "python"
    staged_python.parent.mkdir(parents=True, exist_ok=True)
    staged_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    staged_python.chmod(0o755)

    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: SimpleNamespace(
            version="1.2.4",
            manifest={"repo_schema_version": 1, "migration_required": True},
            python=staged_python,
            root=staged_root,
            verification={"wheel_sha256": "abc123"},
        ),
    )
    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        lambda **kwargs: SimpleNamespace(version="1.2.4"),
    )

    try:
        upgrade_install(
            repo_root=repo_root,
            release_repo="odylith/odylith",
            version="1.2.4",
            write_pin=True,
        )
    except ValueError as exc:
        assert "migration_required" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected migration-marked release to fail closed")


def test_upgrade_rejects_downgrade_even_when_write_pin_is_requested(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.4")

    staged_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    staged_python = staged_root / "bin" / "python"
    staged_python.parent.mkdir(parents=True, exist_ok=True)
    staged_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    staged_python.chmod(0o755)

    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            manifest={"repo_schema_version": 1, "migration_required": False},
            python=staged_python,
            root=staged_root,
            verification={"wheel_sha256": "abc123"},
        ),
    )

    try:
        upgrade_install(
            repo_root=repo_root,
            release_repo="odylith/odylith",
            version="1.2.3",
            write_pin=True,
        )
    except ValueError as exc:
        assert "refusing to downgrade" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected downgrade attempt to be rejected")


def test_upgrade_realigns_to_existing_lower_repo_pin_and_discards_newer_versions(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    upgrade_install(
        repo_root=repo_root,
        release_repo="odylith/odylith",
        version="1.2.4",
        write_pin=True,
    )

    releases_cache_root = repo_root / ".odylith" / "cache" / "releases"
    for version in ("1.2.3", "1.2.4"):
        cache_dir = releases_cache_root / version
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "marker.txt").write_text(f"{version}\n", encoding="utf-8")

    write_version_pin(repo_root=repo_root, version="1.2.3")

    summary = upgrade_install(repo_root=repo_root, release_repo="odylith/odylith", version="1.2.3")
    updated_state = load_install_state(repo_root=repo_root)
    retained_runtime_versions = sorted(path.name for path in (repo_root / ".odylith" / "runtime" / "versions").iterdir())
    retained_cache_versions = sorted(path.name for path in releases_cache_root.iterdir())
    status = version_status(repo_root=repo_root)

    assert summary.active_version == "1.2.3"
    assert summary.previous_version == "1.2.4"
    assert summary.pin_changed is False
    assert summary.pinned_version == "1.2.3"
    assert retained_runtime_versions == ["1.2.3"]
    assert retained_cache_versions == ["1.2.3"]
    assert sorted(updated_state["installed_versions"]) == ["1.2.3"]
    assert updated_state["activation_history"] == ["1.2.3"]
    assert updated_state["active_version"] == "1.2.3"
    assert updated_state["last_known_good_version"] == "1.2.3"
    assert status.active_version == "1.2.3"
    assert status.available_versions == ["1.2.3"]
    assert status.diverged_from_pin is False


def test_upgrade_reuses_matching_context_engine_pack_from_previous_runtime(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    current_runtime = (repo_root / ".odylith" / "runtime" / "current").resolve()
    previous_pack_file = current_runtime / "lib" / "python3.13" / "site-packages" / "watchdog" / "__init__.py"
    previous_pack_file.parent.mkdir(parents=True, exist_ok=True)
    previous_pack_file.write_text("watchdog-from-1.2.3\n", encoding="utf-8")
    runtime.write_managed_runtime_trust(
        repo_root=repo_root,
        version_root=current_runtime,
        verification=runtime.runtime_verification_evidence(current_runtime),
    )

    staged_root, staged_python = _seed_verified_release_runtime(repo_root, version="1.2.4")

    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: SimpleNamespace(
            version="1.2.4",
            manifest={
                "repo_schema_version": 1,
                "migration_required": False,
                "assets": {
                    "odylith-context-engine-memory-darwin-arm64.tar.gz": {
                        "sha256": "feature-pack-1.2.3",
                    }
                },
                "feature_packs": {
                    "odylith-context-engine-memory": {
                        "assets": {
                            "darwin-arm64": "odylith-context-engine-memory-darwin-arm64.tar.gz",
                        }
                    }
                },
            },
            python=staged_python,
            root=staged_root,
            verification={"runtime_bundle_sha256": "runtime-1.2.4", "wheel_sha256": "wheel-1.2.4"},
        ),
    )
    monkeypatch.setattr(
        install_manager_module,
        "install_release_feature_pack",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("feature pack should be reused, not redownloaded")),
    )
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        lambda **kwargs: SimpleNamespace(version="1.2.4"),
    )

    summary = upgrade_install(
        repo_root=repo_root,
        release_repo="odylith/odylith",
        version="1.2.4",
        write_pin=True,
    )

    reused_pack_file = staged_root / "lib" / "python3.13" / "site-packages" / "watchdog" / "__init__.py"
    runtime_feature_packs = json.loads((staged_root / "runtime-feature-packs.v1.json").read_text(encoding="utf-8"))
    state = load_install_state(repo_root=repo_root)
    status = version_status(repo_root=repo_root)

    assert summary.active_version == "1.2.4"
    assert reused_pack_file.read_text(encoding="utf-8") == "watchdog-from-1.2.3\n"
    assert runtime_feature_packs["packs"]["odylith-context-engine-memory"]["asset_name"] == (
        "odylith-context-engine-memory-darwin-arm64.tar.gz"
    )
    assert (
        runtime_feature_packs["packs"]["odylith-context-engine-memory"]["verification"]["feature_pack_sha256"]
        == "feature-pack-1.2.3"
    )
    assert state["installed_versions"]["1.2.4"]["feature_packs"]["odylith-context-engine-memory"]["asset_name"] == (
        "odylith-context-engine-memory-darwin-arm64.tar.gz"
    )
    assert status.context_engine_pack_installed is True


def test_upgrade_redownloads_context_engine_pack_when_previous_paths_are_untrusted(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    current_runtime = (repo_root / ".odylith" / "runtime" / "current").resolve()
    feature_pack_metadata_path = current_runtime / "runtime-feature-packs.v1.json"
    feature_pack_metadata = json.loads(feature_pack_metadata_path.read_text(encoding="utf-8"))
    feature_pack_metadata["packs"]["odylith-context-engine-memory"]["paths"] = ["../escape"]
    feature_pack_metadata_path.write_text(json.dumps(feature_pack_metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    staged_root, staged_python = _seed_verified_release_runtime(repo_root, version="1.2.4")

    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: SimpleNamespace(
            version="1.2.4",
            manifest={
                "repo_schema_version": 1,
                "migration_required": False,
                "assets": {
                    "odylith-context-engine-memory-darwin-arm64.tar.gz": {
                        "sha256": "feature-pack-1.2.4",
                    }
                },
                "feature_packs": {
                    "odylith-context-engine-memory": {
                        "assets": {
                            "darwin-arm64": "odylith-context-engine-memory-darwin-arm64.tar.gz",
                        }
                    }
                },
            },
            python=staged_python,
            root=staged_root,
            verification={"runtime_bundle_sha256": "runtime-1.2.4", "wheel_sha256": "wheel-1.2.4"},
        ),
    )

    invoked: dict[str, bool] = {}

    def _fake_install_release_feature_pack(*, repo_root, repo, version, runtime_root=None, pack_id="odylith-context-engine-memory"):  # noqa: ANN001
        del repo
        invoked["called"] = True
        target_root = Path(runtime_root) if runtime_root is not None else staged_root
        _write_fake_context_engine_pack(
            Path(repo_root),
            target_root=target_root,
            version=str(version),
            pack_id=pack_id,
            feature_pack_sha256="feature-pack-1.2.4",
        )
        return SimpleNamespace(
            asset_name=f"{pack_id}-darwin-arm64.tar.gz",
            manifest={"repo_schema_version": 1, "migration_required": False},
            pack_id=pack_id,
            root=target_root,
            verification={
                "feature_pack_id": pack_id,
                "feature_pack_sha256": "feature-pack-1.2.4",
            },
            version=str(version),
        )

    monkeypatch.setattr(install_manager_module, "install_release_feature_pack", _fake_install_release_feature_pack)
    monkeypatch.setattr(install_manager_module, "fetch_release", lambda **kwargs: SimpleNamespace(version="1.2.4"))
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    upgrade_install(
        repo_root=repo_root,
        release_repo="odylith/odylith",
        version="1.2.4",
        write_pin=True,
    )

    assert invoked["called"] is True


def test_upgrade_prunes_runtime_and_release_cache_retention(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.2")

    legacy_runtime, _ = _seed_verified_release_runtime(repo_root, version="1.2.1")
    releases_cache_root = repo_root / ".odylith" / "cache" / "releases"
    for version in ("1.2.1", "1.2.2", "1.2.3"):
        cache_dir = releases_cache_root / version
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "marker.txt").write_text(f"{version}\n", encoding="utf-8")

    state = load_install_state(repo_root=repo_root)
    state["installed_versions"]["1.2.1"] = {
        "installed_utc": "2026-03-27T00:00:00+00:00",
        "runtime_root": str(legacy_runtime),
        "verification": {"wheel_sha256": "wheel-1.2.1"},
        "feature_packs": {},
    }
    state["activation_history"] = ["1.2.1", "1.2.2"]
    write_install_state(repo_root=repo_root, payload=state)

    staged_root, staged_python = _seed_verified_release_runtime(repo_root, version="1.2.3")
    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            manifest={"repo_schema_version": 1, "migration_required": False},
            python=staged_python,
            root=staged_root,
            verification={"runtime_bundle_sha256": "runtime-1.2.3", "wheel_sha256": "wheel-1.2.3"},
        ),
    )
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        lambda **kwargs: SimpleNamespace(version="1.2.3"),
    )

    summary = upgrade_install(
        repo_root=repo_root,
        release_repo="odylith/odylith",
        version="1.2.3",
        write_pin=True,
    )

    retained_runtime_versions = sorted(path.name for path in (repo_root / ".odylith" / "runtime" / "versions").iterdir())
    retained_cache_versions = sorted(path.name for path in releases_cache_root.iterdir())
    updated_state = load_install_state(repo_root=repo_root)
    status = version_status(repo_root=repo_root)

    assert summary.active_version == "1.2.3"
    assert retained_runtime_versions == ["1.2.2", "1.2.3"]
    assert retained_cache_versions == ["1.2.2", "1.2.3"]
    assert sorted(updated_state["installed_versions"]) == ["1.2.2", "1.2.3"]
    assert updated_state["activation_history"] == ["1.2.2", "1.2.3"]
    assert status.available_versions == ["1.2.2", "1.2.3"]


def test_upgrade_warns_and_continues_when_retention_prune_stays_permission_denied(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.2")

    legacy_runtime, _ = _seed_verified_release_runtime(repo_root, version="1.2.1")
    releases_cache_root = repo_root / ".odylith" / "cache" / "releases"
    for version in ("1.2.1", "1.2.2", "1.2.3"):
        cache_dir = releases_cache_root / version
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "marker.txt").write_text(f"{version}\n", encoding="utf-8")

    state = load_install_state(repo_root=repo_root)
    state["installed_versions"]["1.2.1"] = {
        "installed_utc": "2026-03-27T00:00:00+00:00",
        "runtime_root": str(legacy_runtime),
        "verification": {"wheel_sha256": "wheel-1.2.1"},
        "feature_packs": {},
    }
    state["activation_history"] = ["1.2.1", "1.2.2"]
    write_install_state(repo_root=repo_root, payload=state)

    staged_root, staged_python = _seed_verified_release_runtime(repo_root, version="1.2.3")
    monkeypatch.setattr(
        install_manager_module,
        "install_release_runtime",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            manifest={"repo_schema_version": 1, "migration_required": False},
            python=staged_python,
            root=staged_root,
            verification={"runtime_bundle_sha256": "runtime-1.2.3", "wheel_sha256": "wheel-1.2.3"},
        ),
    )
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        lambda **kwargs: SimpleNamespace(version="1.2.3"),
    )

    original_rmtree = shutil.rmtree

    def _fake_rmtree(path, *args, **kwargs):  # noqa: ANN001, ANN003
        target = Path(path)
        if target.name == "1.2.1":
            raise PermissionError("read-only directory")
        return original_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(install_manager_module.shutil, "rmtree", _fake_rmtree)

    summary = upgrade_install(
        repo_root=repo_root,
        release_repo="odylith/odylith",
        version="1.2.3",
        write_pin=True,
    )

    updated_state = load_install_state(repo_root=repo_root)

    assert summary.active_version == "1.2.3"
    assert legacy_runtime.exists()
    assert (releases_cache_root / "1.2.1").exists()
    assert summary.retention_warnings
    assert "could not prune retained path" in summary.retention_warnings[0]
    assert "Active runtime stayed healthy." in summary.retention_warnings[0]
    assert "chmod -R u+w" in summary.retention_warnings[0]
    assert sorted(updated_state["installed_versions"]) == ["1.2.2", "1.2.3"]


def test_install_and_uninstall_preserve_existing_customer_truth(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    (repo_root / "odylith" / "radar" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "radar" / "source" / "INDEX.md").write_text("# Radar Index\n", encoding="utf-8")
    (repo_root / "odylith" / "casebook" / "bugs").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "casebook" / "bugs" / "INDEX.md").write_text("# Bugs Index\n", encoding="utf-8")
    (repo_root / "odylith" / "technical-plans").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "technical-plans" / "INDEX.md").write_text("# Plans Index\n", encoding="utf-8")

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")
    uninstall_bundle(repo_root=repo_root)

    assert (repo_root / "odylith" / "radar" / "source" / "INDEX.md").read_text(encoding="utf-8") == "# Radar Index\n"
    assert (repo_root / "odylith" / "casebook" / "bugs" / "INDEX.md").read_text(encoding="utf-8") == "# Bugs Index\n"
    assert (repo_root / "odylith" / "technical-plans" / "INDEX.md").read_text(encoding="utf-8") == "# Plans Index\n"


def test_install_bundle_preserves_legacy_odylith_created_truth_in_customer_tree(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)

    legacy_radar = (
        repo_root
        / "odylith"
        / "radar"
        / "source"
        / "ideas"
        / "2026-03"
        / "2026-03-26-odylith-product-self-governance-and-repo-boundary.md"
    )
    legacy_radar.parent.mkdir(parents=True, exist_ok=True)
    legacy_radar.write_text("legacy product workstream\n", encoding="utf-8")

    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.4")

    assert legacy_radar.is_file()


def test_set_agents_integration_toggles_root_guidance_without_removing_runtime(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_repo_root(repo_root)
    install_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", version="1.2.3")

    disabled, disable_message = set_agents_integration(repo_root=repo_root, enabled=False)
    assert disabled is True
    assert "now off" in disable_message.lower()
    assert "fall back" in disable_message.lower()
    assert "<!-- odylith-scope:start -->" not in (repo_root / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- odylith-scope:start -->" not in (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
    assert load_install_state(repo_root=repo_root)["integration_enabled"] is False
    assert (repo_root / ".odylith" / "bin" / "odylith").is_file()

    healthy, message = doctor_bundle(repo_root=repo_root, bundle_root=tmp_path / "unused-bundle", repair=False)
    assert healthy is True
    assert "healthy" in message.lower()

    enabled, enable_message = set_agents_integration(repo_root=repo_root, enabled=True)
    assert enabled is True
    assert "now on" in enable_message.lower()
    assert "default first path" in enable_message.lower()
    assert "<!-- odylith-scope:start -->" in (repo_root / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- odylith-scope:start -->" in (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
    assert load_install_state(repo_root=repo_root)["integration_enabled"] is True
