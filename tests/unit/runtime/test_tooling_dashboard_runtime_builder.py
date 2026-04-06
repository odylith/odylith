from __future__ import annotations

from pathlib import Path

from odylith.runtime.surfaces import tooling_dashboard_runtime_builder as builder


def test_validate_surface_paths_reports_missing_htmls(tmp_path: Path) -> None:
    paths = builder.ToolingDashboardSurfacePaths(
        output_path=tmp_path / "odylith" / "index.html",
        radar_path=tmp_path / "odylith" / "radar" / "radar.html",
        atlas_path=tmp_path / "odylith" / "atlas" / "atlas.html",
        compass_path=tmp_path / "odylith" / "compass" / "compass.html",
        registry_path=tmp_path / "odylith" / "registry" / "registry.html",
        casebook_path=tmp_path / "odylith" / "casebook" / "casebook.html",
    )

    errors = builder.validate_surface_paths(paths)

    assert len(errors) == 5
    assert any("missing radar html" in item for item in errors)
    assert any("missing compass html" in item for item in errors)


def test_build_runtime_payload_adds_release_notes_link_and_surface_hrefs(tmp_path: Path) -> None:
    output_path = tmp_path / "odylith" / "index.html"
    paths = builder.ToolingDashboardSurfacePaths(
        output_path=output_path,
        radar_path=tmp_path / "odylith" / "radar" / "radar.html",
        atlas_path=tmp_path / "odylith" / "atlas" / "atlas.html",
        compass_path=tmp_path / "odylith" / "compass" / "compass.html",
        registry_path=tmp_path / "odylith" / "registry" / "registry.html",
        casebook_path=tmp_path / "odylith" / "casebook" / "casebook.html",
    )
    for path in (
        paths.radar_path,
        paths.atlas_path,
        paths.compass_path,
        paths.registry_path,
        paths.casebook_path,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<!doctype html>\n", encoding="utf-8")

    result = builder.build_runtime_payload(
        repo_root=tmp_path,
        surface_paths=paths,
        shell_payload={"window_title": "Odylith"},
        welcome_state={"show": True},
        release_spotlight={"show": True, "to_version": "1.2.3", "release_tag": "v1.2.3"},
        version_story={"show": True, "to_version": "1.2.3", "headline": "What changed since v1.2.2?"},
        benchmark_story={"show": True, "status": "pass"},
        shell_source_payload={"shell_repo_label": "Repo · Odylith"},
        self_host_payload={"repo_role": "product_repo"},
        brand_payload={"brand_head_html": "<meta />"},
        shell_version_label="v1.2.3",
    )

    assert result.release_notes_path == output_path.parent / "release-notes" / "1.2.3.html"
    assert result.runtime_payload["radar_href"].startswith("radar/radar.html?v=")
    assert result.runtime_payload["compass_href"].startswith("compass/compass.html?v=")
    assert result.runtime_payload["release_spotlight"]["notes_href"] == "release-notes/1.2.3.html"
    assert result.runtime_payload["version_story"]["notes_href"] == "release-notes/1.2.3.html"
    assert result.runtime_payload["benchmark_story"]["status"] == "pass"
    assert result.runtime_payload["shell_version_label"] == "v1.2.3"


def test_build_runtime_payload_uses_version_story_when_popup_payload_is_absent(tmp_path: Path) -> None:
    output_path = tmp_path / "odylith" / "index.html"
    paths = builder.ToolingDashboardSurfacePaths(
        output_path=output_path,
        radar_path=tmp_path / "odylith" / "radar" / "radar.html",
        atlas_path=tmp_path / "odylith" / "atlas" / "atlas.html",
        compass_path=tmp_path / "odylith" / "compass" / "compass.html",
        registry_path=tmp_path / "odylith" / "registry" / "registry.html",
        casebook_path=tmp_path / "odylith" / "casebook" / "casebook.html",
    )
    for path in (
        paths.radar_path,
        paths.atlas_path,
        paths.compass_path,
        paths.registry_path,
        paths.casebook_path,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<!doctype html>\n", encoding="utf-8")

    result = builder.build_runtime_payload(
        repo_root=tmp_path,
        surface_paths=paths,
        shell_payload={},
        welcome_state={"show": False},
        release_spotlight={},
        version_story={"show": True, "to_version": "1.2.3", "headline": "What changed since v1.2.2?"},
        benchmark_story={},
        shell_source_payload={},
        self_host_payload={},
        brand_payload={},
        shell_version_label="v1.2.3",
    )

    assert result.release_notes_path == output_path.parent / "release-notes" / "1.2.3.html"
    assert result.runtime_payload["release_spotlight"] == {}
    assert result.runtime_payload["version_story"]["notes_href"] == "release-notes/1.2.3.html"


def test_build_runtime_payload_uses_product_name_for_public_product_repo(tmp_path: Path) -> None:
    output_path = tmp_path / "odylith" / "index.html"
    paths = builder.ToolingDashboardSurfacePaths(
        output_path=output_path,
        radar_path=tmp_path / "odylith" / "radar" / "radar.html",
        atlas_path=tmp_path / "odylith" / "atlas" / "atlas.html",
        compass_path=tmp_path / "odylith" / "compass" / "compass.html",
        registry_path=tmp_path / "odylith" / "registry" / "registry.html",
        casebook_path=tmp_path / "odylith" / "casebook" / "casebook.html",
    )
    for path in (
        paths.radar_path,
        paths.atlas_path,
        paths.compass_path,
        paths.registry_path,
        paths.casebook_path,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<!doctype html>\n", encoding="utf-8")
    (tmp_path / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='odylith'\n", encoding="utf-8")

    result = builder.build_runtime_payload(
        repo_root=tmp_path,
        surface_paths=paths,
        shell_payload={},
        welcome_state={},
        release_spotlight={},
        version_story={},
        benchmark_story={},
        shell_source_payload={},
        self_host_payload={},
        brand_payload={},
        shell_version_label="source-local",
    )

    assert result.runtime_payload["shell_repo_name"] == "odylith"
