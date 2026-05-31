from __future__ import annotations

import json
import time

from odylith.runtime.domain_intelligence import greenfield_proposals
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import _write_confirmed_intent


def test_greenfield_create_confirm_full_refresh_stays_under_thirty_seconds(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    _write_confirmed_intent(tmp_path)

    started = time.perf_counter()
    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a municipal permit review workspace",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--release",
            "0.0.1",
            "--confirm",
            "--json",
        ]
    )
    elapsed = time.perf_counter() - started
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert elapsed < 30.0
    assert payload["validation_gate"]["status"] == "passed"
    assert payload["dashboard_refresh"]["status"] == "passed"
    assert payload["dashboard_refresh"]["surfaces"] == ["radar", "registry", "atlas", "compass", "tooling_shell"]
    assert len(payload["backlog"]) == 4
    assert len(payload["components"]) == 4
    assert len(payload["diagrams"]) == 6
    assert (tmp_path / "odylith/radar/radar.html").is_file()
    assert (tmp_path / "odylith/registry/registry.html").is_file()
    assert (tmp_path / "odylith/atlas/atlas.html").is_file()
    assert (tmp_path / "odylith/compass/compass.html").is_file()
    assert (tmp_path / "odylith/index.html").is_file()
    assert len(list((tmp_path / "odylith/atlas/source").glob("*.svg"))) == len(payload["diagrams"])
    assert len(list((tmp_path / "odylith/atlas/source").glob("*.png"))) == len(payload["diagrams"])
    catalog = json.loads((tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json").read_text(encoding="utf-8"))
    assert all(diagram["reviewed_watch_fingerprints"] for diagram in catalog["diagrams"])
    assert all(diagram["render_source_fingerprint"] for diagram in catalog["diagrams"])
    assert all(str(diagram.get("source_png", "")).strip().endswith(".png") for diagram in catalog["diagrams"])
    assert all((tmp_path / str(diagram["source_png"])).is_file() for diagram in catalog["diagrams"])
