from pathlib import Path

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
