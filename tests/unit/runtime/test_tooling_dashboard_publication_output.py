"""Shell render/cache ownership preserves the sole sealed publication entry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.governance import sync_workstream_artifacts as sync
from odylith.runtime.surfaces import render_tooling_dashboard as renderer
from odylith.runtime.surfaces import source_bundle_mirror
from tests.unit.runtime.test_greenfield_publication_paths import _protect
from tests.unit.runtime.test_render_tooling_dashboard import (
    _load_externalized_payload_js,
    _seed_compass_runtime_snapshot,
    _seed_inputs,
)


@pytest.fixture
def shell_repo(tmp_path: Path, monkeypatch) -> Path:
    _seed_inputs(tmp_path)
    _seed_compass_runtime_snapshot(tmp_path, generated_utc="2026-04-07T17:06:12Z")
    monkeypatch.setattr(renderer.delivery_surface_payload_runtime, "load_delivery_surface_payload", lambda **kwargs: {})
    return tmp_path


def _cache_outputs(repo: Path) -> set[str]:
    cache_path = renderer.odylith_context_cache.cache_path(
        repo_root=repo, namespace="generated-refresh-guards", key="tooling-dashboard-render",
    )
    return set(json.loads(cache_path.read_text())["outputs"])


@pytest.mark.parametrize("explicit_output", (False, True))
def test_protected_render_preserves_entry_and_reports_physical_shell(shell_repo, capsys, explicit_output):
    root = shell_repo
    (root / "odylith/index.html").write_text("<html>Prior shell</html>\n")
    entry = _protect(root)
    args = ["--repo-root", str(root)]
    if explicit_output:
        args += ["--output", str(root / "odylith/index.html")]
    assert renderer.main(args) == 0
    shell = root / "odylith/tooling-shell.html"
    assert (root / "odylith/index.html").read_bytes() == entry
    assert "toolingDashboardData" in shell.read_text()
    assert f"- output: {shell}" in capsys.readouterr().out
    assert str(shell) in _cache_outputs(root)
    assert str(root / "odylith/index.html") not in _cache_outputs(root)
    payload = _load_externalized_payload_js(root / "odylith/tooling-payload.v1.js")
    assert payload["radar_href"].startswith("radar/radar.html")


def test_activation_invalidates_old_output_cache_and_reuses_protected_cache(shell_repo, monkeypatch):
    root = shell_repo
    assert renderer.main(["--repo-root", str(root)]) == 0
    assert str(root / "odylith/index.html") in _cache_outputs(root)
    entry = _protect(root)
    calls = []
    build = renderer.tooling_dashboard_runtime_builder.build_runtime_payload

    def record_build(**kwargs):
        calls.append(kwargs["surface_paths"].output_path)
        return build(**kwargs)

    monkeypatch.setattr(renderer.tooling_dashboard_runtime_builder, "build_runtime_payload", record_build)
    assert renderer.main(["--repo-root", str(root)]) == 0
    assert calls == [root / "odylith/tooling-shell.html"]
    calls.clear()
    assert renderer.main(["--repo-root", str(root)]) == 0
    assert calls == []
    assert (root / "odylith/index.html").read_bytes() == entry


def test_protected_shell_mirrors_as_ordinary_bundle_index(shell_repo):
    root = shell_repo
    bundle = source_bundle_mirror.source_bundle_root(repo_root=root)
    bundle.mkdir(parents=True)
    (root / "odylith/index.html").write_text("<html>Prior shell</html>\n")
    entry = _protect(root)
    assert renderer.main(["--repo-root", str(root)]) == 0
    assert (root / "odylith/index.html").read_bytes() == entry
    assert (bundle / "index.html").read_bytes() == (root / "odylith/tooling-shell.html").read_bytes()
    assert not (bundle / "tooling-shell.html").exists()
    assert str(bundle / "index.html") in _cache_outputs(root)
    assert str(bundle / "tooling-shell.html") not in _cache_outputs(root)
    assert not source_bundle_mirror.is_consumer_safe_bundle_relative_path("tooling-shell.html")


@pytest.mark.parametrize("folder", ("ordinary", "arbitrary-stage", "arbitrary-immutable"))
def test_unprotected_roots_keep_ordinary_index(tmp_path, monkeypatch, folder):
    root = tmp_path / folder
    _seed_inputs(root)
    monkeypatch.setattr(renderer.delivery_surface_payload_runtime, "load_delivery_surface_payload", lambda **kwargs: {})
    assert renderer.main(["--repo-root", str(root)]) == 0
    assert "toolingDashboardData" in (root / "odylith/index.html").read_text()
    assert not (root / "odylith/tooling-shell.html").exists()
    assert greenfield_generation_state.read_active_publication(root) is None


def test_invalid_protected_entry_fails_before_render_or_cache(shell_repo, monkeypatch):
    root = shell_repo
    (root / "odylith/index.html").write_text("<html>Prior shell</html>\n")
    _protect(root)
    (root / "odylith/index.html").write_text("<html>Unsealed replacement</html>\n")
    before = (root / "odylith/tooling-shell.html").read_bytes()

    def forbidden(**kwargs):
        raise AssertionError("cache/render path ran before publication validation")

    monkeypatch.setattr(renderer.generated_surface_refresh_guards, "should_skip_surface_rebuild", forbidden)
    with pytest.raises(RuntimeError, match="replaced"):
        renderer.main(["--repo-root", str(root)])
    assert (root / "odylith/tooling-shell.html").read_bytes() == before


def test_working_shell_symlink_cannot_overwrite_publication(shell_repo):
    root = shell_repo
    (root / "odylith/index.html").write_text("<html>Prior shell</html>\n")
    entry = _protect(root)
    working = root / "odylith/tooling-shell.html"
    working.unlink()
    working.symlink_to(root / "odylith/index.html")
    with pytest.raises(ValueError, match="unsafe symlink"):
        renderer.main(["--repo-root", str(root)])
    assert (root / "odylith/index.html").read_bytes() == entry


def test_custom_output_keeps_its_relative_links_without_replacing_entry(shell_repo):
    root = shell_repo
    (root / "odylith/index.html").write_text("<html>Prior shell</html>\n")
    entry = _protect(root)
    working = (root / "odylith/tooling-shell.html").read_bytes()
    assert renderer.main(["--repo-root", str(root), "--output", "odylith/export/index.html"]) == 0
    payload = _load_externalized_payload_js(root / "odylith/export/tooling-payload.v1.js")
    assert payload["radar_href"].startswith("../radar/radar.html")
    assert (root / "odylith/index.html").read_bytes() == entry
    assert (root / "odylith/tooling-shell.html").read_bytes() == working


def test_sync_shell_step_and_worker_cache_declare_physical_output(shell_repo, monkeypatch):
    root = shell_repo
    (root / "odylith/index.html").write_text("<html>Prior shell</html>\n")
    _protect(root)
    expected = ("odylith/tooling-shell.html", "odylith/tooling-payload.v1.js", "odylith/tooling-app.v1.js")
    steps = sync._dashboard_surface_steps(repo_root=root, surface="tooling_shell", runtime_mode="standalone", atlas_sync=False)
    assert steps[-1].paths == expected
    assert sync._sync_surface_batch_outputs(("tooling_shell",), repo_root=root) == expected
    assert sync._sync_surface_batch_runtime(repo_root=root).surface_render_outputs("tooling_shell") == expected
    observed = []

    def cache_hit(**kwargs):
        observed.append(kwargs["outputs"])
        return True, {}

    monkeypatch.setattr(sync.surface_refresh_fingerprint_dag, "can_reuse_surface_refresh", cache_hit)
    _output, result = sync._run_surface_worker(
        repo_root=root, surface="tooling_shell", runtime_mode="standalone", atlas_sync=False,
        run_impl=lambda *args, **kwargs: pytest.fail("a cache hit must not execute a renderer"),
    )
    assert result["cache_hit"] is True
    assert observed == [expected]
