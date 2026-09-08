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
