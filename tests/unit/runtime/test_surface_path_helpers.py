from __future__ import annotations

from pathlib import Path

from odylith.runtime.surfaces import surface_path_helpers


def test_resolve_repo_path_handles_relative_and_absolute_tokens(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target = repo_root / "odylith" / "index.html"
    target.parent.mkdir(parents=True)
    target.write_text("ok", encoding="utf-8")

    assert surface_path_helpers.resolve_repo_path(repo_root=repo_root, token="odylith/index.html") == target.resolve()
    assert surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=str(target)) == target.resolve()


def test_relative_href_and_portable_relative_href_are_posix_stable(tmp_path: Path) -> None:
    output_path = tmp_path / "odylith" / "registry" / "registry.html"
    output_path.parent.mkdir(parents=True)
    output_path.write_text("registry", encoding="utf-8")
    target = tmp_path / "odylith" / "index.html"
    target.write_text("shell", encoding="utf-8")
    missing_target = tmp_path / "odylith" / "atlas" / "atlas.html"

    assert surface_path_helpers.relative_href(output_path=output_path, target=target) == "../index.html"
    assert (
        surface_path_helpers.portable_relative_href(
            output_path=output_path,
            token=str(missing_target),
        )
        == "../atlas/atlas.html"
    )


def test_path_link_and_path_links_preserve_missing_paths_when_requested(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    output_path = repo_root / "odylith" / "registry" / "registry.html"
    existing = repo_root / "src" / "odylith" / "runtime" / "surfaces" / "example.py"
    existing.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("pass\n", encoding="utf-8")
    output_path.write_text("registry\n", encoding="utf-8")

    existing_row = surface_path_helpers.path_link(
        repo_root=repo_root,
        output_path=output_path,
        token="src/odylith/runtime/surfaces/example.py",
    )
    missing_row = surface_path_helpers.path_link(
        repo_root=repo_root,
        output_path=output_path,
        token="docs/missing.md",
        allow_missing=True,
    )

    assert existing_row == {
        "path": "src/odylith/runtime/surfaces/example.py",
        "href": "../../src/odylith/runtime/surfaces/example.py",
    }
    assert missing_row == {
        "path": "docs/missing.md",
        "href": "../../docs/missing.md",
    }
    assert surface_path_helpers.path_links(
        repo_root=repo_root,
        output_path=output_path,
        values=["", "src/odylith/runtime/surfaces/example.py", "docs/missing.md"],
        allow_missing=True,
    ) == [existing_row, missing_row]


def test_path_link_returns_empty_href_for_missing_paths_without_opt_in(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    output_path = repo_root / "odylith" / "registry" / "registry.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("registry\n", encoding="utf-8")

    row = surface_path_helpers.path_link(
        repo_root=repo_root,
        output_path=output_path,
        token="docs/missing.md",
    )

    assert row == {
        "path": "docs/missing.md",
        "href": "",
    }


def test_path_links_skip_whitespace_only_tokens(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    output_path = repo_root / "odylith" / "registry" / "registry.html"
    target = repo_root / "docs" / "guide.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("registry\n", encoding="utf-8")
    target.write_text("# Guide\n", encoding="utf-8")

    rows = surface_path_helpers.path_links(
        repo_root=repo_root,
        output_path=output_path,
        values=[" ", "\n", "docs/guide.md"],
    )

    assert rows == [{"path": "docs/guide.md", "href": "../../docs/guide.md"}]


def test_portable_relative_href_handles_repo_relative_tokens_from_cwd(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "odylith" / "registry" / "registry.html"
    target = tmp_path / "docs" / "guide.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("registry\n", encoding="utf-8")
    target.write_text("# Guide\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    href = surface_path_helpers.portable_relative_href(
        output_path=output_path,
        token="docs/guide.md",
    )

    assert href == "../../docs/guide.md"
