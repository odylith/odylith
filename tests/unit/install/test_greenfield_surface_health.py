"""Static release readback must follow the verified logical publication."""

import json
from pathlib import Path
import shutil
import sys

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_surface_health import (
    INDEX_SHELL_TAB_CONTRACTS,
    SURFACE_PAYLOAD_CONTRACTS,
    rendered_surface_health_issues,
    rendered_surface_payload_count,
)
from odylith.runtime.domain_intelligence import greenfield_generation_state as state
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as writes


def _surface_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    payload = {key: href for _, key, href in INDEX_SHELL_TAB_CONTRACTS.values()}
    payload["project_intelligence"] = {
        "host_handoff_prompts": [{"prompt": f"Execute bounded step {i}."} for i in range(5)],
    }
    for relative, assets in SURFACE_PAYLOAD_CONTRACTS.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        links = []
        for asset in assets:
            is_payload = asset == "tooling-payload.v1.js"
            script_id = ' id="toolingDashboardData"' if is_payload else ""
            links.append(f'<script{script_id} src="{asset}"></script>')
            (path.parent / asset).write_text(
                "window.__ODYLITH_TOOLING_DATA__=" + json.dumps(payload) if is_payload else "/* asset */",
            )
        if relative == "odylith/index.html":
            links.append('<button data-tab="project">Project</button>')
            links.extend(
                f'<button data-tab="{tab}">{tab}</button><iframe id="{frame}"></iframe>'
                for tab, (frame, _, _) in INDEX_SHELL_TAB_CONTRACTS.items()
            )
        path.write_text("<!doctype html>\n" + "\n".join(links))
    return root


def _publish(root: Path, tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    write_set = writes.compile_greenfield_repository_write_set(source_root=empty, staged_root=root)
    generation = generations.materialize_immutable_greenfield_generation(
        repo_root=root, write_set=write_set,
        manifest_text=generations.compile_greenfield_generation_manifest(write_set),
    )
    generations.publish_greenfield_generation(
        repo_root=root, generation=generation, write_set=write_set,
        publication_entry_text=state.compile_greenfield_publication_entry(
            write_set_hash=generation.write_set_hash,
            generation_manifest_sha256=generation.manifest_sha256,
        ),
    )
    shutil.copy2(generation.repository_root / "odylith/index.html", root / "odylith/tooling-shell.html")
    return generation


@pytest.mark.parametrize("published", (False, True))
def test_surface_health_uses_logical_shell_without_requiring_scripts_in_carrier(tmp_path: Path, published: bool) -> None:
    root = _surface_repo(tmp_path)
    if published:
        _publish(root, tmp_path)
        assert "tooling-app.v1.js" not in (root / "odylith/index.html").read_text()
    assert rendered_surface_health_issues(repo_root=root) == ()
    assert rendered_surface_payload_count(root) == 12


@pytest.mark.parametrize("damage", ("missing_carrier", "replaced_carrier", "sealed_asset", "working_shell"))
def test_surface_health_rejects_broken_publication_without_fallback(tmp_path: Path, damage: str) -> None:
    root = _surface_repo(tmp_path)
    generation = _publish(root, tmp_path)
    if damage == "missing_carrier":
        (root / "odylith/index.html").unlink()
    elif damage == "replaced_carrier":
        shutil.copy2(root / "odylith/tooling-shell.html", root / "odylith/index.html")
    elif damage == "sealed_asset":
        (generation.repository_root / "odylith/tooling-app.v1.js").write_text("tampered")
    else:
        (root / "odylith/tooling-shell.html").write_text("changed")
    assert any("publication" in issue for issue in rendered_surface_health_issues(repo_root=root))


def test_unpublished_surface_health_still_detects_missing_local_asset(tmp_path: Path) -> None:
    root = _surface_repo(tmp_path)
    (root / "odylith/tooling-app.v1.js").unlink()
    assert any("missing local asset tooling-app.v1.js" in issue for issue in rendered_surface_health_issues(repo_root=root))
