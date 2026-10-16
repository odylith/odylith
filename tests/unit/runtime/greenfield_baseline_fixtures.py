"""Minimal rendered baseline for transaction tests, using real publication setup."""

from pathlib import Path

from odylith import cli
from odylith.runtime.domain_intelligence import greenfield_create_baseline as baseline
from odylith.runtime.domain_intelligence import greenfield_generation_state as state
from odylith.runtime.domain_intelligence import greenfield_generation_store as store


def activate_greenfield_baseline_fixture(repo_root: Path) -> None:
    """Preserve fixture truth and supply only missing first-run rendered outputs."""

    if state.read_active_publication(repo_root) is not None:
        store.require_greenfield_working_generation(repo_root)
        return
    for relative in cli._FIRST_RUN_SURFACE_OUTPUTS:
        path = repo_root / relative
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"<!doctype html><title>{relative}</title>\n", encoding="utf-8")
    baseline.activate_completed_greenfield_baseline(
        repo_root=repo_root, required_surface_outputs=cli._FIRST_RUN_SURFACE_OUTPUTS,
    )
