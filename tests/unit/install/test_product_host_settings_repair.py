"""Product-repo repair refreshes host settings without replacing authored truth."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.install import bootstrap_assets
from odylith.install import manager
from odylith.runtime.common import codex_cli_capabilities


@pytest.fixture
def product_repo(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "product"
    root.mkdir()
    (root / "AGENTS.md").write_text("# Maintainer-owned guidance\n")
    (root / "pyproject.toml").write_text("[project]\nname='odylith'\nversion='1.2.3'\n")
    (root / "src/odylith").mkdir(parents=True)
    (root / "src/odylith/__init__.py").write_text("__version__ = '1.2.3'\n")
    (root / "src/odylith/cli.py").write_text("raise SystemExit(0)\n")
    for relative in ("odylith/maintainer", "odylith/registry/source", "odylith/radar/source"):
        (root / relative).mkdir(parents=True)
    (root / "odylith/AGENTS.md").write_text("# Authored product guidance\n")
    (root / "odylith/maintainer/AGENTS.md").write_text("# Release instructions\n")
    (root / "odylith/registry/source/component_registry.v1.json").write_text(
        '{"version":"v1","components":[]}\n'
    )
    (root / "odylith/radar/source/INDEX.md").write_text("# Backlog\n")
    monkeypatch.setattr(codex_cli_capabilities, "_run_codex_command", lambda **_kwargs: None)
    monkeypatch.setattr(
        manager, "install_release_runtime",
        lambda **_kwargs: pytest.fail("Product host repair must not download another runtime"),
    )
    manager.install_bundle(repo_root=root, bundle_root=tmp_path / "unused", version="1.2.3")
    return root


def test_product_doctor_repairs_flat_hooks_without_replacing_custom_settings(product_repo: Path) -> None:
    root = product_repo
    hooks = root / ".codex/hooks.json"
    custom = {"hooks": [{"type": "command", "command": "echo retained-custom-hook"}]}
    flat = {"description": "Custom hook metadata", "UserPromptSubmit": [custom]}
    original_hooks = json.dumps(flat).encode()
    hooks.write_bytes(original_hooks)
    config = root / ".codex/config.toml"
    config.write_text('[features]\nhooks = true\n[agents]\nmax_threads = 3\n')
    settings = root / ".claude/settings.json"
    settings.write_text('{"permissions":{"deny":["Read(./private/*)"]}}\n')
    owned = [root / name for name in (
        "AGENTS.md", "odylith/AGENTS.md", "odylith/maintainer/AGENTS.md",
        "odylith/registry/source/component_registry.v1.json", ".codex/config.toml",
    )]
    before = {path: path.read_bytes() for path in owned}

    healthy, _message = manager.doctor_bundle(repo_root=root, bundle_root=root / "unused", repair=True)

    assert healthy
    document = json.loads(hooks.read_text())
    assert set(document) == {"description", "hooks"}
    assert document["description"] == flat["description"]
    assert document["hooks"]["UserPromptSubmit"][0] == custom
    assert len(document["hooks"]) == 5
    assert hooks.with_name("hooks.json.odylith-preimage.bak").read_bytes() == original_hooks
    assert {path: path.read_bytes() for path in owned} == before
    claude = json.loads(settings.read_text())
    assert claude["permissions"]["deny"] == ["Read(./private/*)"]
    assert "UserPromptSubmit" in claude["hooks"]
    repaired = (hooks.read_bytes(), settings.read_bytes())

    assert manager.doctor_bundle(repo_root=root, bundle_root=root / "unused", repair=True)[0]
    assert (hooks.read_bytes(), settings.read_bytes()) == repaired
    assert hooks.with_name("hooks.json.odylith-preimage.bak").read_bytes() == original_hooks


def test_product_refresh_without_activation_preserves_flat_hooks(product_repo: Path) -> None:
    hooks = product_repo / ".codex/hooks.json"
    hooks.write_text('{"UserPromptSubmit":[]}\n')
    before = hooks.read_bytes()
    bootstrap_assets.refresh_consumer_managed_guidance(
        repo_root=product_repo, repo_role="product_repo", include_brand=False,
        activate_host_settings=False,
    )
    assert hooks.read_bytes() == before


@pytest.mark.parametrize("operation", ["doctor", "install", "source_upgrade"])
def test_product_lifecycle_preserves_disabled_host_registration(product_repo: Path, operation: str) -> None:
    manager.set_agents_integration(repo_root=product_repo, enabled=False)
    hooks = product_repo / ".codex/hooks.json"
    hooks.write_text('{"UserPromptSubmit":[]}\n')
    before = hooks.read_bytes() if hooks.exists() else None
    if operation == "doctor":
        assert manager.doctor_bundle(repo_root=product_repo, bundle_root=product_repo / "unused", repair=True)[0]
    elif operation == "install":
        manager.install_bundle(repo_root=product_repo, bundle_root=product_repo / "unused", version="1.2.3")
    else:
        manager.upgrade_install(repo_root=product_repo, release_repo="unused", source_repo=product_repo)
    assert (hooks.read_bytes() if hooks.exists() else None) == before
    assert not manager.install_integration_enabled(manager.load_install_state(repo_root=product_repo))
