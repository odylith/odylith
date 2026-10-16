"""Disposable browser snapshots preserve logical working ownership and source bytes."""

from pathlib import Path
import stat

import pytest

from odylith.runtime.domain_intelligence import greenfield_generation_state as state
from tests.integration.runtime.surface_browser_test_support import _copy_logical_working_fixture


def _source(tmp_path: Path, *, active: bool) -> Path:
    root = tmp_path / "source"
    product = root / "odylith"
    product.mkdir(parents=True)
    shell = product / ("tooling-shell.html" if active else "index.html")
    shell.write_text("<!doctype html><html><body>Working shell</body></html>\n")
    shell.chmod(0o640)
    (product / "tooling-app.v1.js").write_text("window.working = true;\n")
    (product / "empty").mkdir()
    (product / "source").mkdir()
    (product / "source" / "note.md").write_text("Working source\n")
    if active:
        (product / "index.html").write_text(state.compile_greenfield_publication_entry(
            write_set_hash="a" * 64, generation_manifest_sha256="b" * 64,
        ))
    pinned = root / ".odylith/runtime/greenfield/generations" / ("a" * 64) / "repository/odylith"
    pinned.mkdir(parents=True)
    (pinned / "index.html").write_text("Published shell must not replace the working snapshot\n")
    return root


def _files(root: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.relative_to(root).as_posix(): (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
        for path in root.rglob("*") if path.is_file()
    }


@pytest.mark.parametrize("active", [False, True], ids=["inactive", "active"])
def test_copy_uses_one_logical_working_tree_and_preserves_source(tmp_path: Path, active: bool) -> None:
    source = _source(tmp_path, active=active)
    before = _files(source)
    fixture = tmp_path / "fixture"

    origins = _copy_logical_working_fixture(source, fixture)

    physical_shell = source / "odylith" / ("tooling-shell.html" if active else "index.html")
    assert origins["index.html"] == physical_shell
    assert (fixture / "odylith/index.html").read_bytes() == physical_shell.read_bytes()
    assert stat.S_IMODE((fixture / "odylith/index.html").stat().st_mode) == 0o640
    assert (fixture / "odylith/tooling-app.v1.js").read_bytes() == before["odylith/tooling-app.v1.js"][0]
    assert (fixture / "odylith/empty").is_dir()
    assert (fixture / "odylith/source/note.md").read_text() == "Working source\n"
    assert not (fixture / "odylith/tooling-shell.html").exists()
    assert not (fixture / ".odylith").exists()
    assert state.read_active_publication(fixture) is None
    (fixture / "odylith/index.html").write_text("Fixture-only mutation\n")
    assert _files(source) == before


@pytest.mark.parametrize("active", [False, True], ids=["inactive", "active"])
def test_filtered_copy_retains_physical_shell_provenance(tmp_path: Path, active: bool) -> None:
    source = _source(tmp_path, active=active)
    before = _files(source)
    fixture = tmp_path / "fixture"

    origins = _copy_logical_working_fixture(
        source, fixture, include_file=lambda relative: relative.suffix in {".html", ".js"},
    )

    assert set(origins) == {"index.html", "tooling-app.v1.js"}
    assert not (fixture / "odylith/source").exists()
    assert not (fixture / "odylith/empty").exists()
    for relative, physical in origins.items():
        assert (fixture / "odylith" / relative).read_bytes() == physical.read_bytes()
    assert state.read_active_publication(fixture) is None
    assert _files(source) == before


@pytest.mark.parametrize("defect", [
    "missing-root", "missing-index", "missing-working-shell", "malformed-entry",
    "replaced-entry", "carrier-as-working-shell", "symlink-working-shell", "symlink-asset",
])
def test_invalid_source_is_refused_before_fixture_creation(tmp_path: Path, defect: str) -> None:
    source = _source(tmp_path, active=defect != "missing-index")
    product = source / "odylith"
    if defect == "missing-root":
        source = tmp_path / "absent"
    elif defect == "missing-index":
        (product / "index.html").unlink()
    elif defect == "missing-working-shell":
        (product / "tooling-shell.html").unlink()
    elif defect == "malformed-entry":
        entry = product / "index.html"
        entry.write_text(entry.read_text() + "unsealed suffix")
    elif defect == "replaced-entry":
        (product / "index.html").write_text("<html><body>Replaced entry</body></html>")
    elif defect == "carrier-as-working-shell":
        (product / "tooling-shell.html").write_bytes((product / "index.html").read_bytes())
    elif defect == "symlink-working-shell":
        (product / "tooling-shell.html").unlink()
        (product / "tooling-shell.html").symlink_to(product / "index.html")
    elif defect == "symlink-asset":
        (product / "linked.js").symlink_to(product / "tooling-app.v1.js")
    fixture = tmp_path / "fixture"

    with pytest.raises((ValueError, RuntimeError)):
        _copy_logical_working_fixture(source, fixture)

    assert not fixture.exists()


def test_existing_destination_is_not_overwritten(tmp_path: Path) -> None:
    source = _source(tmp_path, active=True)
    fixture = tmp_path / "fixture"
    (fixture / "odylith").mkdir(parents=True)
    (fixture / "odylith/index.html").write_text("Existing destination\n")
    before = _files(fixture)

    with pytest.raises(FileExistsError):
        _copy_logical_working_fixture(source, fixture)

    assert _files(fixture) == before
