"""Batch metadata validation precedes writes; publication remains the existing owner's work."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import stat

import pytest

from odylith import cli
from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_repository_lock as leases
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as write_sets
from odylith.runtime.surfaces import render_mermaid_catalog as renderer
from odylith.runtime.surfaces import update_mermaid_diagram as updater
from tests.unit.runtime.test_greenfield_generation_store import _publish
from tests.unit.runtime.test_update_mermaid_diagram import _seed_catalog


_CATALOG = "odylith/atlas/source/catalog/diagrams.v1.json"


def _fixture(root: Path) -> tuple[Path, dict, list[dict]]:
    catalog = _seed_catalog(root)
    payload = json.loads(catalog.read_text())
    original = payload["diagrams"][0]
    rows, updates = [], []
    (root / "guide.md").write_text("Maintained Atlas reference.\n")
    for index in range(6):
        row = deepcopy(original)
        row.update(diagram_id=f"D-{110 + index}", slug=f"flow-{index}")
        for extension in ("mmd", "svg", "png"):
            row[f"source_{extension}"] = f"odylith/atlas/source/flow-{index}.{extension}"
        (root / row["source_mmd"]).write_text('flowchart LR\n  intake["Intake"] --> review["Review"]\n')
        row["related_docs"] = ["guide.md"]
        row["reader_settings"] = {"retained": [index, {"value": "unchanged"}]}
        if index < 5:
            row["related_code"] = row["change_watch_paths"] = [f"src/removed-{index}.py"]
            code = f"src/current-{index}.py"
            (root / code).write_text(f"VALUE = {index}\n")
            updates.append({
                "diagram_id": row["diagram_id"], "related_code": [code],
                "change_watch_paths": [code], "summary": f"Shows the maintained intake and review ownership for flow {index}.",
                "last_reviewed_utc": "2026-09-14",
            })
        rows.append(row)
    updates[-1]["diagram_boxes"] = [
        {"label": "Intake", "role": "Request owner", "description": "The intake owner records the request before review can begin."},
        {"label": "Review", "role": "Decision owner", "description": "The reviewer checks the recorded request and owns its final decision."},
    ]
    payload.update(diagrams=rows, retained_extension={"keep": [1, 2]})
    catalog.write_text(json.dumps(payload, indent=2) + "\n")
    catalog.chmod(0o640)
    return catalog, payload, updates


def _input(root: Path, updates: list[dict]) -> Path:
    path = root / "atlas-updates.json"
    path.write_text(json.dumps({"version": "odylith.atlas.updates.v1", "updates": updates}))
    return path


def _cli(root: Path, path: Path) -> int:
    return cli.main(["atlas", "update", "--repo-root", str(root), "--updates-file", str(path)])


@pytest.fixture(autouse=True)
def _no_product_branch_probe(monkeypatch):
    # Isolated consumer fixtures exercise the real command and publication boundary, not Git.
    monkeypatch.setattr(cli, "_guard_product_repo_main_branch", lambda **_: 0)


def _spies(monkeypatch, catalog: Path):
    writes, refreshes = [], []
    atomic_write = updater.atomic_write_bytes

    def write(path, data, **kwargs):
        assert path == catalog
        writes.append(json.loads(data))
        return atomic_write(path, data, **kwargs)

    def refresh(**kwargs):
        assert len(writes) == 1
        refreshes.append(kwargs)
        assert json.loads(catalog.read_text()) == writes[0]

    monkeypatch.setattr(updater, "atomic_write_bytes", write)
    monkeypatch.setattr(updater.owned_surface_refresh, "raise_for_failed_refresh", refresh)
    return writes, refreshes


def test_five_row_cli_batch_writes_once_and_preserves_unsupplied_truth(tmp_path, monkeypatch):
    catalog, before, updates = _fixture(tmp_path)
    writes, refreshes = _spies(monkeypatch, catalog)

    assert _cli(tmp_path, _input(tmp_path, updates)) == 0

    after = json.loads(catalog.read_text())
    assert len(writes) == len(refreshes) == 1
    assert stat.S_IMODE(catalog.stat().st_mode) == 0o640
    assert after["retained_extension"] == before["retained_extension"]
    assert after["diagrams"][-1] == before["diagrams"][-1]
    for index, patch in enumerate(updates):
        for field, value in before["diagrams"][index].items():
            if field not in patch and field != "reviewed_watch_fingerprints":
                assert after["diagrams"][index][field] == value
        for field, value in patch.items():
            assert after["diagrams"][index][field] == value
        assert "reviewed_watch_fingerprints" not in after["diagrams"][index]


@pytest.mark.parametrize("reverse", [False, True])
def test_directory_references_preserve_spelling_for_updated_and_untouched_rows(tmp_path, monkeypatch, reverse):
    catalog, payload, updates = _fixture(tmp_path)
    for field in ("related_code", "change_watch_paths"):
        payload["diagrams"][-1][field] = ["src/"]
        updates[0][field] = ["src/"]
    catalog.write_text(json.dumps(payload))
    updated_id = updates[0]["diagram_id"]
    if reverse:
        updates.reverse()
    writes, refreshes = _spies(monkeypatch, catalog)

    assert _cli(tmp_path, _input(tmp_path, updates)) == 0

    after = json.loads(catalog.read_text())
    assert len(writes) == len(refreshes) == 1
    assert after["diagrams"][-1] == payload["diagrams"][-1]
    updated = next(row for row in after["diagrams"] if row["diagram_id"] == updated_id)
    assert updated["related_code"] == updated["change_watch_paths"] == ["src/"]


@pytest.mark.parametrize("field", updater._PATH_FIELDS)
def test_directory_reference_fields_accept_exact_single_trailing_slash(tmp_path, field):
    target = tmp_path / "source"
    target.mkdir()
    assert updater._repo_local_path(repo_root=tmp_path, token="source/", field=field) == (target, "source/")


@pytest.mark.parametrize("token", [
    ".", "./", "source//", "source/./", "source/../source/", "./source/", "source//nested/",
    "alias/", "../outside/", "source/file.py/", "missing/",
])
def test_directory_references_reject_noncanonical_or_non_directory_spelling(tmp_path, token):
    (tmp_path / "source/nested").mkdir(parents=True)
    (tmp_path / "source/file.py").write_text("VALUE = 1\n")
    (tmp_path / "alias").symlink_to("source", target_is_directory=True)
    with pytest.raises(ValueError):
        updater._repo_local_path(repo_root=tmp_path, token=token, field="related_code")


@pytest.mark.parametrize("field", ["source_mmd", "source_svg", "source_png", "catalog", "updates_file"])
def test_directory_reference_exception_never_applies_to_file_slots(tmp_path, field):
    (tmp_path / "source").mkdir()
    with pytest.raises(ValueError):
        updater._repo_local_path(repo_root=tmp_path, token="source/", field=field)


@pytest.mark.parametrize("flags", [{"require_file": True}, {"allow_missing": True}])
def test_directory_references_cannot_override_file_requirements(tmp_path, flags):
    (tmp_path / "source").mkdir()
    with pytest.raises(ValueError):
        updater._repo_local_path(repo_root=tmp_path, token="source/", field="related_code", **flags)


@pytest.mark.parametrize("failure", [
    "bad-final-date", "duplicate-id", "unknown-id", "noncanonical-id", "escaping-code",
    "absolute-code", "aliased-code", "unknown-field", "immutable-source", "immutable-slug",
    "null-summary", "wrong-code-type", "malformed-boxes", "box-extra-field", "box-missing-field",
    "box-missing-label", "box-orphan", "box-duplicate", "box-mechanical-copy", "bad-components",
])
def test_invalid_final_patch_cannot_write_an_earlier_valid_patch(tmp_path, monkeypatch, failure):
    catalog, _before, updates = _fixture(tmp_path)
    last = updates[-1]
    if failure == "bad-final-date":
        last["last_reviewed_utc"] = "tomorrow"
    elif failure == "duplicate-id":
        last["diagram_id"] = updates[0]["diagram_id"]
    elif failure == "unknown-id":
        last["diagram_id"] = "D-999"
    elif failure == "noncanonical-id":
        last["diagram_id"] = "d-114"
    elif failure == "escaping-code":
        last["related_code"] = ["../outside.py"]
    elif failure == "absolute-code":
        last["related_code"] = [str(tmp_path / "src/current-4.py")]
    elif failure == "aliased-code":
        last["related_code"] = ["src/../src/current-4.py"]
    elif failure == "unknown-field":
        last["unexpected"] = True
    elif failure == "immutable-source":
        last["source_mmd"] = "odylith/atlas/source/flow-0.mmd"
    elif failure == "immutable-slug":
        last["slug"] = "flow-0"
    elif failure == "null-summary":
        last["summary"] = None
    elif failure == "wrong-code-type":
        last["related_code"] = "src/current-4.py"
    elif failure == "malformed-boxes":
        last["diagram_boxes"] = {"label": "Intake"}
    elif failure == "box-extra-field":
        last["diagram_boxes"][0]["generated"] = False
    elif failure == "box-missing-field":
        del last["diagram_boxes"][0]["role"]
    elif failure == "box-missing-label":
        last["diagram_boxes"].pop()
    elif failure == "box-orphan":
        last["diagram_boxes"][0]["label"] = "Orphan"
    elif failure == "box-duplicate":
        last["diagram_boxes"].append(deepcopy(last["diagram_boxes"][0]))
    elif failure == "box-mechanical-copy":
        last["diagram_boxes"][0]["description"] = "This box has incoming arrows and outgoing arrows in the diagram."
    elif failure == "bad-components":
        last["components"] = [{"name": "Owner", "description": 1}]
    before = catalog.read_bytes()
    writes, refreshes = _spies(monkeypatch, catalog)

    assert _cli(tmp_path, _input(tmp_path, updates)) == 2
    assert catalog.read_bytes() == before
    assert writes == refreshes == []


@pytest.mark.parametrize("field,value", [
    ("related_code", ["src/missing.py"]), ("change_watch_paths", ["src/missing.py"]),
    ("source_mmd", "odylith/atlas/source/flow-0.mmd"), ("diagram_id", "D-110"),
    ("initial_view_fit_factor", 10), ("components", []), ("source_png", "../outside.png"),
    ("diagram_boxes", [{"label": "Intake", "description": "placeholder"}]),
])
def test_complete_candidate_validation_rejects_invalid_unpatched_row(tmp_path, monkeypatch, field, value):
    catalog, payload, updates = _fixture(tmp_path)
    payload["diagrams"][-1][field] = value
    catalog.write_text(json.dumps(payload))
    before = catalog.read_bytes()
    writes, refreshes = _spies(monkeypatch, catalog)

    assert _cli(tmp_path, _input(tmp_path, updates)) == 2
    assert catalog.read_bytes() == before
    assert writes == refreshes == []


@pytest.mark.parametrize("body", [
    "[]", "{}", '{"version":"wrong","updates":[]}',
    '{"version":"odylith.atlas.updates.v1","updates":[]}',
    '{"version":"odylith.atlas.updates.v1","updates":[null]}',
    '{"version":"odylith.atlas.updates.v1","updates":[{"diagram_id":"D-110"}]}',
    '{"version":"odylith.atlas.updates.v1","updates":[],"unexpected":true}',
    '{"version":"odylith.atlas.updates.v1","updates":[],"updates":[]}',
    '{"version":"odylith.atlas.updates.v1","updates":[{"diagram_id":"D-110","summary":"first","summary":"last"}]}',
])
def test_invalid_batch_envelope_fails_before_write(tmp_path, monkeypatch, body):
    catalog, _before, _updates = _fixture(tmp_path)
    path = tmp_path / "input.json"
    path.write_text(body)
    before = catalog.read_bytes()
    writes, refreshes = _spies(monkeypatch, catalog)
    assert _cli(tmp_path, path) == 2
    assert catalog.read_bytes() == before
    assert writes == refreshes == []


@pytest.mark.parametrize("single_flags", [["--diagram-id", "D-110"], ["--summary", "Changed summary"], ["--watch", "src/old.py"]])
def test_batch_and_single_entry_flags_are_mutually_exclusive(tmp_path, monkeypatch, single_flags):
    catalog, _before, updates = _fixture(tmp_path)
    before = catalog.read_bytes()
    writes, refreshes = _spies(monkeypatch, catalog)
    with pytest.raises(SystemExit) as caught:
        cli.main(["atlas", "update", "--repo-root", str(tmp_path), "--updates-file", str(_input(tmp_path, updates)), *single_flags])
    assert caught.value.code == 2
    assert catalog.read_bytes() == before
    assert writes == refreshes == []


@pytest.mark.parametrize("asset_state", ["missing", "directory"])
def test_metadata_api_does_not_weaken_default_render_asset_checks(tmp_path, asset_state):
    catalog, payload, updates = _fixture(tmp_path)
    for row, patch in zip(payload["diagrams"], updates):
        row.update(patch)
    catalog.write_text(json.dumps(payload))
    if asset_state == "directory":
        for row in payload["diagrams"]:
            for field in ("source_svg", "source_png"):
                (tmp_path / row[field]).mkdir()
    assert renderer.validate_catalog_metadata(repo_root=tmp_path, catalog_path=catalog, payload=payload) == []
    _rows, errors, _stats = renderer._load_catalog(
        repo_root=tmp_path, catalog_path=catalog, output_path=tmp_path / "odylith/atlas/atlas.html",
        max_review_age_days=21, component_index={},
    )
    assert sum("source_svg does not exist" in error for error in errors) == 6
    assert sum("source_png does not exist" in error for error in errors) == 6


def test_batch_rejects_a_nonregular_render_destination(tmp_path, monkeypatch):
    catalog, payload, updates = _fixture(tmp_path)
    (tmp_path / payload["diagrams"][0]["source_svg"]).mkdir()
    before = catalog.read_bytes()
    writes, refreshes = _spies(monkeypatch, catalog)
    assert _cli(tmp_path, _input(tmp_path, updates)) == 2
    assert catalog.read_bytes() == before
    assert writes == refreshes == []


def test_batch_rejects_catalog_symlink_and_preserves_target(tmp_path, monkeypatch):
    catalog, _payload, updates = _fixture(tmp_path)
    original = catalog.with_name("original.json")
    catalog.rename(original)
    catalog.symlink_to(original.name)
    before = original.read_bytes()
    writes, refreshes = _spies(monkeypatch, catalog)
    assert _cli(tmp_path, _input(tmp_path, updates)) == 2
    assert catalog.is_symlink()
    assert original.read_bytes() == before
    assert writes == refreshes == []


def test_invalid_source_text_fails_metadata_before_write(tmp_path, monkeypatch):
    catalog, payload, updates = _fixture(tmp_path)
    (tmp_path / payload["diagrams"][-1]["source_mmd"]).write_bytes(b"\xff")
    before = catalog.read_bytes()
    writes, refreshes = _spies(monkeypatch, catalog)
    assert _cli(tmp_path, _input(tmp_path, updates)) == 2
    assert catalog.read_bytes() == before
    assert writes == refreshes == []


@pytest.mark.parametrize("failed_refresh", [False, True])
def test_actual_cli_boundary_publishes_only_after_successful_batch_refresh(tmp_path, monkeypatch, capsys, failed_refresh):
    catalog, before, updates = _fixture(tmp_path)
    (tmp_path / "odylith/index.html").write_text("<!doctype html><title>Complete fixture shell</title>\n")
    write_set = write_sets.compile_greenfield_repository_write_set(source_root=tmp_path, staged_root=tmp_path)
    generation = generations.materialize_immutable_greenfield_generation(
        repo_root=tmp_path, write_set=write_set,
        manifest_text=generations.compile_greenfield_generation_manifest(write_set),
    )
    _publish(tmp_path, generation, write_set)
    original = publication.active_generation_identity(tmp_path)
    calls = []

    def refresh(**_kwargs):
        calls.append(True)
        with pytest.raises(leases.GreenfieldRepositoryBusyError):
            with leases.greenfield_repository_lock(tmp_path):
                pytest.fail("Atlas refresh ran outside the repository writer lock")
        assert publication.active_generation_identity(tmp_path) == original
        assert json.loads(catalog.read_text())["diagrams"][0]["summary"] == updates[0]["summary"]
        if failed_refresh:
            raise RuntimeError("retained injected refresh failure")

    monkeypatch.setattr(updater.owned_surface_refresh, "raise_for_failed_refresh", refresh)
    assert _cli(tmp_path, _input(tmp_path, updates)) == (1 if failed_refresh else 0)
    assert calls == [True]
    assert json.loads((generation.repository_root / _CATALOG).read_text()) == before
    current = publication.active_generation_identity(tmp_path)
    if failed_refresh:
        assert current == original
        assert "no recovery or publication success is claimed" in capsys.readouterr().out
        with pytest.raises(generations.GreenfieldWorkingGenerationDriftError):
            generations.require_greenfield_working_generation(tmp_path)
    else:
        assert current != original
        active = generations.require_greenfield_working_generation(tmp_path)
        assert (active.repository_root / _CATALOG).read_bytes() == catalog.read_bytes()


def test_atomic_write_failure_does_not_refresh(tmp_path, monkeypatch):
    catalog, _before, updates = _fixture(tmp_path)
    before = catalog.read_bytes()
    _writes, refreshes = _spies(monkeypatch, catalog)

    def fail(*_args, **_kwargs):
        raise OSError("injected atomic write failure")

    monkeypatch.setattr(updater, "atomic_write_bytes", fail)
    assert _cli(tmp_path, _input(tmp_path, updates)) == 1
    assert catalog.read_bytes() == before
    assert refreshes == []
