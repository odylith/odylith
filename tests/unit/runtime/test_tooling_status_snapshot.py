"""Snapshot acquisition owns rendered status, never independently mutable telemetry."""

from pathlib import Path

import pytest

from odylith.install.state import write_install_state, write_version_pin
from odylith.runtime.context_engine import odylith_control_state as telemetry
from odylith.runtime.domain_intelligence import greenfield_create_baseline as baseline
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary as boundary
from odylith.runtime.surfaces import render_tooling_dashboard as renderer
from tests.unit.runtime.test_render_tooling_dashboard import _load_externalized_payload_js
from tests.unit.runtime.test_tooling_dashboard_publication_output import shell_repo  # noqa: F401


@pytest.mark.parametrize("output", ["odylith/index.html", "odylith/radar/custom-shell.html", "odylith/custom.html", "odylith/tooling-shell.html"])
@pytest.mark.parametrize("published", [False, True])
def test_every_managed_bundle_captures_status_before_and_after_publication(shell_repo, output, published):
    telemetry.write_state(repo_root=shell_repo, payload={"updated_utc": "2026-09-09T18:00:00Z", "private_detail": "not browser data"})
    args = ["--repo-root", str(shell_repo), "--output", output]
    if published:
        assert renderer.main(["--repo-root", str(shell_repo)]) == 0
        baseline.activate_completed_greenfield_baseline(repo_root=shell_repo, required_surface_outputs=[Path("odylith/index.html")])
        prior = generations.require_greenfield_working_generation(shell_repo)
        prior_payload = prior.repository_root / "odylith/tooling-payload.v1.js"
        prior_bytes = prior_payload.read_bytes()
        assert boundary.run_with_greenfield_managed_mutation_boundary(
            repo_root=shell_repo, command_tokens=["dashboard", "refresh", "--force"],
            operation=lambda _fd: renderer.main(args),
        ) == 0
        generations.require_greenfield_working_generation(shell_repo)
        assert prior_payload.read_bytes() == prior_bytes
    else:
        assert renderer.main(args) == 0
    payload = _load_externalized_payload_js(shell_repo / Path(output).parent / "tooling-payload.v1.js")
    snapshot = payload["status_snapshot"]
    assert snapshot["context_updated_utc"] == "2026-09-09T18:00:00Z"
    assert snapshot["version_state"]["source"] == "odylith version"
    assert snapshot["captured_utc"] == snapshot["version_state"]["generated_utc"]
    assert "private_detail" not in str(payload)
    assert not payload["version_state_href"]
    assert not payload["version_state_global_name"]
    assert "live_refresh" not in payload


def test_telemetry_remains_independent_and_refresh_captures_a_coherent_successor(shell_repo):
    root = shell_repo
    telemetry.write_state(repo_root=root, payload={"updated_utc": "2026-09-09T18:00:00Z"})
    assert renderer.main(["--repo-root", str(root)]) == 0
    baseline.activate_completed_greenfield_baseline(repo_root=root, required_surface_outputs=[Path("odylith/index.html")])
    prior = generations.require_greenfield_working_generation(root)
    prior_payload_path = prior.repository_root / "odylith/tooling-payload.v1.js"
    prior_bytes = prior_payload_path.read_bytes()
    prior_payload = _load_externalized_payload_js(prior_payload_path)

    telemetry.write_state(repo_root=root, payload={"updated_utc": "2026-09-09T18:01:00Z"})
    assert generations.require_greenfield_working_generation(root) == prior
    assert prior_payload_path.read_bytes() == prior_bytes

    def refresh(_fd):
        write_install_state(repo_root=root, payload={"active_version": "1.2.4"})
        write_version_pin(repo_root=root, version="1.2.4")
        return renderer.main(["--repo-root", str(root)])

    assert boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=root,
        command_tokens=["dashboard", "refresh", "--repo-root", str(root), "--force"],
        operation=refresh,
    ) == 0
    successor = generations.require_greenfield_working_generation(root)
    current = _load_externalized_payload_js(successor.repository_root / "odylith/tooling-payload.v1.js")
    assert successor.write_set_hash != prior.write_set_hash
    assert current["status_snapshot"]["context_updated_utc"] == "2026-09-09T18:01:00Z"
    assert prior_payload["status_snapshot"]["context_updated_utc"] == "2026-09-09T18:00:00Z"
    assert current["status_snapshot"]["version_state"]["authoritative_version"] == "1.2.4"
    assert prior_payload_path.read_bytes() == prior_bytes
    for path in (prior.repository_root, successor.repository_root):
        assert not (path / ".odylith/runtime/odylith-context-engine-state.v1.json").exists()
        assert not (path / ".odylith/runtime/odylith-version-state.v1.js").exists()


def test_changed_telemetry_capture_invalidates_only_the_render_cache(shell_repo):
    for timestamp in ("2026-09-09T18:00:00Z", "2026-09-09T18:01:00Z"):
        telemetry.write_state(repo_root=shell_repo, payload={"updated_utc": timestamp})
        assert renderer.main(["--repo-root", str(shell_repo)]) == 0
        payload = _load_externalized_payload_js(shell_repo / "odylith/tooling-payload.v1.js")
        assert payload["status_snapshot"]["context_updated_utc"] == timestamp


def test_unmanaged_direct_output_keeps_live_acquisition(shell_repo):
    assert renderer.main(["--repo-root", str(shell_repo), "--output", "odylith/export/index.html"]) == 0
    payload = _load_externalized_payload_js(shell_repo / "odylith/export/tooling-payload.v1.js")
    assert "status_snapshot" not in payload
    assert payload["version_state_href"] == "../../.odylith/runtime/odylith-version-state.v1.js"
    assert payload["live_refresh"]["mode"] == "passive_runtime_probe"
    assert payload["live_refresh"]["state_href"] == "../../.odylith/runtime/odylith-context-engine-state.v1.js"
