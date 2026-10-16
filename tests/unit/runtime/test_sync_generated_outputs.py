"""Surface output inventory is owned directly by sync's generated-output module."""

from pathlib import Path

import pytest

from odylith.runtime.governance import sync_generated_outputs as outputs
from odylith.runtime.governance import sync_workstream_artifacts as sync
from tests.unit.runtime.test_greenfield_publication_paths import _protect


SURFACE_OUTPUTS = {
    "tooling_shell": ("odylith/index.html", "odylith/tooling-payload.v1.js", "odylith/tooling-app.v1.js"),
    "radar": (
        "odylith/radar/radar.html",
        "odylith/radar/backlog-payload.v1.js",
        "odylith/radar/backlog-app.v1.js",
        "odylith/radar/traceability-graph.v1.json",
    ),
    "compass": (
        "odylith/compass/compass.html",
        "odylith/compass/compass-payload.v1.js",
        "odylith/compass/compass-app.v1.js",
        "odylith/compass/compass-style-base.v1.css",
        "odylith/compass/compass-style-execution-waves.v1.css",
        "odylith/compass/compass-style-surface.v1.css",
        "odylith/compass/compass-shared.v1.js",
        "odylith/compass/compass-state.v1.js",
        "odylith/compass/compass-summary.v1.js",
        "odylith/compass/compass-timeline.v1.js",
        "odylith/compass/compass-waves.v1.js",
        "odylith/compass/compass-workstreams.v1.js",
        "odylith/compass/compass-ui-runtime.v1.js",
    ),
    "atlas": ("odylith/atlas/atlas.html", "odylith/atlas/mermaid-payload.v1.js", "odylith/atlas/mermaid-app.v1.js"),
    "registry": ("odylith/registry/registry.html", "odylith/registry/registry-payload.v1.js", "odylith/registry/registry-app.v1.js"),
    "casebook": ("odylith/casebook/casebook.html", "odylith/casebook/casebook-payload.v1.js", "odylith/casebook/casebook-app.v1.js"),
    "unknown": (),
}


@pytest.mark.parametrize("protected", (False, True))
@pytest.mark.parametrize("surface, expected", SURFACE_OUTPUTS.items())
def test_surface_inventory_preserves_exact_order_and_only_maps_protected_shell(
    tmp_path: Path, protected: bool, surface: str, expected: tuple[str, ...],
) -> None:
    (tmp_path / "odylith").mkdir()
    (tmp_path / "odylith/index.html").write_text("<html>Complete shell</html>\n")
    if protected:
        _protect(tmp_path)
        if surface == "tooling_shell":
            expected = ("odylith/tooling-shell.html", *expected[1:])
    assert outputs.surface_render_outputs(surface, repo_root=tmp_path) == expected
    assert set(expected) <= set(outputs.generated_output_targets())
    assert sync._sync_surface_batch_outputs((surface,), repo_root=tmp_path) == expected
    assert sync._sync_surface_batch_runtime(repo_root=tmp_path).surface_render_outputs(surface) == expected


@pytest.mark.parametrize("surface", tuple(SURFACE_OUTPUTS)[:-1])
def test_step_and_batch_callbacks_use_output_owner_directly(tmp_path: Path, monkeypatch, surface: str) -> None:
    expected = (f"odylith/{surface}-owner-marker.html",)
    calls = []

    def owned_outputs(name: str, *, repo_root: Path) -> tuple[str, ...]:
        calls.append((name, repo_root))
        return expected

    monkeypatch.setattr(outputs, "surface_render_outputs", owned_outputs)
    steps = sync._dashboard_surface_steps(
        repo_root=tmp_path, surface=surface, runtime_mode="standalone", atlas_sync=False,
    )
    assert any(step.paths == expected for step in steps)
    assert sync._sync_surface_batch_outputs((surface,), repo_root=tmp_path) == expected
    assert sync._sync_surface_batch_runtime(repo_root=tmp_path).surface_render_outputs(surface) == expected
    assert calls == [(surface, tmp_path)] * 3


def test_sync_orchestrator_does_not_keep_removed_output_owner_or_layout_alias() -> None:
    assert not hasattr(sync, "_surface_render_outputs")
    assert not hasattr(sync, "greenfield_repository_layout")


@pytest.mark.parametrize("invalid", [False, True])
def test_casebook_refresh_preserves_authored_bug_bytes_and_normalizes_index(tmp_path, invalid):
    from odylith.runtime.surfaces import render_casebook_dashboard
    bugs = tmp_path / "odylith/casebook/bugs"
    bugs.mkdir(parents=True)
    bug = bugs / "2026-10-06-retained-observation.md"
    bug.write_bytes(("- Bug ID: CB-001\r\n- Status: Open\r\n- Created: 2026-10-06\r\n- Severity: P2\r\n"
                     "- Reproducibility: " + ("High; invalid value" if invalid else "High") + "\r\n- Type: Product" +
                     "\r\n- Description: Retain café observation.\r\n").encode())
    bug.chmod(0o640)
    index = bugs / "INDEX.md"
    index.write_bytes(b"# Authored index\r\n\r\nKeep this exact operator annotation.\r\n")
    index.chmod(0o600)
    link = bugs / "operator-copy.txt"
    link.symlink_to(bug.name)
    before = {p.name: (p.read_bytes(), p.stat().st_mode & 0o777) for p in (bug, index)}
    generated = [tmp_path / name for name in SURFACE_OUTPUTS["casebook"]]
    for path in generated:
        path.write_bytes(b"old generated view\n")
    calls = []

    def render(**args):
        assert args["args"][2] == "odylith.runtime.surfaces.render_casebook_dashboard"
        calls.append(True)
        return render_casebook_dashboard.main(["--repo-root", str(tmp_path), "--runtime-mode", "standalone"])

    steps = sync._dashboard_surface_steps(repo_root=tmp_path, surface="casebook", runtime_mode="standalone",
                                          atlas_sync=False, casebook_migrate_bug_ids=True)
    assert steps[0].paths == ("odylith/casebook/bugs/",)
    result = sync._execute_dashboard_refresh_surface(repo_root=tmp_path, surface="casebook", steps=steps,
                                                    runtime_mode="standalone", run_impl=render)
    assert result["status"] == ("failed" if invalid else "passed")
    assert result["rc"] == (2 if invalid else 0)
    assert calls == ([] if invalid else [True])
    assert (bug.read_bytes(), bug.stat().st_mode & 0o777) == before[bug.name]
    assert index.stat().st_mode & 0o777 == before[index.name][1]
    assert (index.read_bytes() == before[index.name][0]) == invalid
    if not invalid:
        assert "CB-001" in index.read_text(encoding="utf-8")
    assert link.is_symlink() and link.readlink() == Path(bug.name)
    assert all(path.read_bytes() == b"old generated view\n" for path in generated) if invalid else all(
        path.read_bytes() != b"old generated view\n" for path in generated)


def test_explicit_casebook_index_normalization_keeps_its_source_owner(tmp_path):
    bugs = tmp_path / "odylith/casebook/bugs"
    bugs.mkdir(parents=True)
    bug = bugs / "2026-10-06-normalize-explicitly.md"
    bug.write_text("- Status: Open\n- Created: 2026-10-06\n- Severity: P2\n"
                   "- Reproducibility: High\n- Type: Product\n- Description: Grounded observation.\n")
    step = sync._casebook_index_refresh_step(repo_root=tmp_path, label="Explicit governed normalization",
                                              next_command_on_failure="odylith casebook validate --repo-root .")
    assert step.action() == 0
    assert "- Bug ID: CB-001" in bug.read_text()
    assert "CB-001" in (bugs / "INDEX.md").read_text()


@pytest.fixture
def logical_checkpoint_repo(tmp_path: Path, monkeypatch, request):
    from types import SimpleNamespace
    from odylith.install import manager
    from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary as boundary
    from tests.unit.runtime.test_greenfield_baseline_activation import _activate, _complete

    _complete(tmp_path)
    (tmp_path / "odylith/index.html").chmod(getattr(request, "param", 0o644))
    (tmp_path / ".gitignore").write_text(".odylith/\n")
    _checkpoint_git(tmp_path, "init", "--quiet")
    _checkpoint_git(tmp_path, "add", ".")
    _checkpoint_git(tmp_path, "-c", "user.name=freedom-research", "-c",
                    "user.email=freedom@freedompreetham.org", "commit", "--quiet", "-m", "baseline")
    _activate(tmp_path)
    before = (tmp_path / "odylith/tooling-shell.html").read_bytes()

    def synthetic_render(_fd):
        (tmp_path / "odylith/tooling-shell.html").write_bytes(b"<!doctype html><title>Current published shell</title>\n")
        return 0

    assert boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=tmp_path, command_tokens=("dashboard", "refresh"), operation=synthetic_render,
    ) == 0
    status = SimpleNamespace(repo_role=manager.PRODUCT_REPO_ROLE,
                             posture=manager.DETACHED_SOURCE_LOCAL_POSTURE,
                             runtime_source=manager.SOURCE_CHECKOUT_RUNTIME_SOURCE)
    monkeypatch.setattr(manager, "version_status", lambda **_kwargs: status)
    _stage_checkpoint_shell(tmp_path)
    return tmp_path, status, before


def _checkpoint_git(root: Path, *arguments, data=None):
    import subprocess
    return subprocess.run(["git", "-C", str(root), *arguments], input=data,
                          capture_output=True, check=True).stdout


def _stage_checkpoint_shell(root: Path, *, data=None, mode="100644"):
    if data is None:
        data = (root / "odylith/tooling-shell.html").read_bytes()
    blob = _checkpoint_git(root, "hash-object", "-w", "--stdin", data=data).decode().strip()
    _checkpoint_git(root, "update-index", "--cacheinfo", mode, blob, "odylith/index.html")


@pytest.mark.parametrize("logical_checkpoint_repo", (0o644, 0o600), indirect=True)
def test_exact_published_logical_shell_checkpoint_preserves_carrier_and_generation(logical_checkpoint_repo):
    from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
    from odylith.runtime.domain_intelligence import greenfield_generation_store as generations

    root, _, _ = logical_checkpoint_repo
    carrier = (root / "odylith/index.html").read_bytes()
    active = publication.active_generation_identity(root)
    pinned = generations.require_greenfield_working_generation(root)
    assert "odylith/index.html" in outputs.git_dirty_generated_outputs(repo_root=root)
    assert "?? odylith/tooling-shell.html" in outputs.git_dirty_generated_outputs(repo_root=root)
    assert outputs.git_commit_ready_generated_outputs(repo_root=root) == ""
    assert _checkpoint_git(root, "show", ":odylith/index.html") == (pinned.repository_root / "odylith/index.html").read_bytes()
    assert (root / "odylith/index.html").read_bytes() == carrier
    assert (root / "odylith/tooling-shell.html").stat().st_mode & 0o777 == (pinned.repository_root / "odylith/index.html").stat().st_mode & 0o777
    assert publication.active_generation_identity(root) == active
    assert generations.require_greenfield_working_generation(root) == pinned


@pytest.mark.parametrize("defect", ("wrong_bytes", "old_shell", "carrier", "wrong_index_mode", "wrong_working_mode", "stale_publication", "corrupt_generation"))
def test_logical_checkpoint_rejects_wrong_seal_or_staged_identity(logical_checkpoint_repo, defect):
    from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
    from odylith.runtime.domain_intelligence import greenfield_generation_store as generations

    root, _, old = logical_checkpoint_repo
    if defect == "wrong_bytes":
        _stage_checkpoint_shell(root, data=b"different shell")
    elif defect == "old_shell":
        _stage_checkpoint_shell(root, data=old)
    elif defect == "carrier":
        _checkpoint_git(root, "add", "odylith/index.html")
    elif defect == "wrong_index_mode":
        _stage_checkpoint_shell(root, mode="100755")
    elif defect == "wrong_working_mode":
        (root / "odylith/tooling-shell.html").chmod(0o755)
    elif defect == "stale_publication":
        (root / "odylith/index.html").write_text(publication.compile_greenfield_publication_entry(
            write_set_hash="a" * 64, generation_manifest_sha256="b" * 64,
        ))
    else:
        pinned = generations.pin_active_greenfield_generation(root)
        (pinned.repository_root / "odylith/index.html").write_bytes(b"corrupt immutable shell")
    assert outputs.git_commit_ready_generated_outputs(repo_root=root)


@pytest.mark.parametrize("field,value", (("repo_role", "consumer_repo"), ("posture", "pinned_release"), ("runtime_source", "pinned_runtime")))
def test_logical_export_does_not_change_consumer_or_pinned_checks(logical_checkpoint_repo, field, value):
    root, status, _ = logical_checkpoint_repo
    setattr(status, field, value)
    result = outputs.git_commit_ready_generated_outputs(repo_root=root)
    assert "odylith/index.html" in result
    assert "?? odylith/tooling-shell.html" in result


def test_unrelated_generated_untracked_file_still_refuses_checkpoint(logical_checkpoint_repo):
    from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary as boundary
    root, _, _ = logical_checkpoint_repo

    def synthetic_render(_fd):
        (root / "odylith/registry/registry-payload.v1.js").write_bytes(b"window.registry = {};\n")
        return 0

    assert boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=root, command_tokens=("registry", "refresh"), operation=synthetic_render,
    ) == 0
    assert outputs.git_commit_ready_generated_outputs(repo_root=root) == "?? odylith/registry/registry-payload.v1.js"


def test_publication_changed_during_staged_read_refuses_logical_export(logical_checkpoint_repo, monkeypatch):
    from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
    root, _, _ = logical_checkpoint_repo
    real_run = outputs.subprocess.run

    def changed_during_read(arguments, **kwargs):
        result = real_run(arguments, **kwargs)
        if "show" in arguments:
            (root / "odylith/index.html").write_text(publication.compile_greenfield_publication_entry(
                write_set_hash="c" * 64, generation_manifest_sha256="d" * 64,
            ))
        return result

    monkeypatch.setattr(outputs.subprocess, "run", changed_during_read)
    assert outputs.git_commit_ready_generated_outputs(repo_root=root)
