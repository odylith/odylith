from pathlib import Path

from odylith.runtime.common import repo_path_resolver
from odylith.runtime.common.repo_path_resolver import RepoPathResolver


def test_repo_path_resolver_reuses_normalized_resolution_and_derived_paths(tmp_path: Path) -> None:
    output_path = tmp_path / "odylith" / "atlas" / "atlas.html"
    target_path = tmp_path / "docs" / "sample.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("# Sample\n", encoding="utf-8")

    resolver = RepoPathResolver(repo_root=tmp_path, output_path=output_path)

    first = resolver.resolve("docs/sample.md")
    second = resolver.resolve("docs/sample.md")

    assert first == target_path.resolve()
    assert first is second
    assert resolver.repo_path(first) == "docs/sample.md"
    assert resolver.href(first) == "../../docs/sample.md"


def test_repo_path_resolver_module_helpers_cover_missing_and_external_paths(tmp_path: Path) -> None:
    output_path = tmp_path / "odylith" / "atlas" / "atlas.html"
    target_path = tmp_path / "docs" / "missing.md"
    external_path = tmp_path.parent / f"{tmp_path.name}-external.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    external_path.write_text("# External\n", encoding="utf-8")

    resolved = repo_path_resolver.resolve_repo_path(repo_root=tmp_path, value="docs/missing.md")

    assert resolved == target_path.resolve()
    assert repo_path_resolver.relative_href(
        repo_root=tmp_path,
        output_path=output_path,
        value="docs/missing.md",
    ) == "../../docs/missing.md"
    assert repo_path_resolver.display_repo_path(repo_root=tmp_path, value=resolved) == "docs/missing.md"
    assert repo_path_resolver.display_repo_path(repo_root=tmp_path, value=external_path) == external_path.resolve().as_posix()
