from __future__ import annotations

from pathlib import Path

import pytest

from odylith import cli


_ROOT = Path(__file__).resolve().parents[2]


def test_atlas_update_help_forwards_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["atlas", "update", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith atlas update" in output
    assert "--diagram-id" in output
    assert "--summary" in output
    assert "--watch" in output


def test_atlas_parent_help_lists_update(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["atlas", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "update" in output
    assert "Update one existing Atlas diagram catalog entry." in output


def test_atlas_update_help_is_documented_in_public_and_bundle_assets() -> None:
    source_readme = (_ROOT / "odylith" / "README.md").read_text(encoding="utf-8")
    bundle_readme = (
        _ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "README.md"
    ).read_text(encoding="utf-8")
    source_skill = (
        _ROOT / "odylith" / "skills" / "odylith-diagram-catalog" / "SKILL.md"
    ).read_text(encoding="utf-8")
    bundle_skill = (
        _ROOT
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "skills"
        / "odylith-diagram-catalog"
        / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "./.odylith/bin/odylith atlas update --help" in source_readme
    assert "./.odylith/bin/odylith atlas update --help" in bundle_readme
    assert "./.odylith/bin/odylith atlas update --repo-root ." in source_skill
    assert "./.odylith/bin/odylith atlas update --repo-root ." in bundle_skill
