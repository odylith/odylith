from __future__ import annotations

from pathlib import Path

from odylith.runtime.common import log_compass_timeline_event


def test_normalize_workstreams_dedupes_and_reports_invalid_tokens() -> None:
    normalized, errors = log_compass_timeline_event._normalize_workstreams(  # noqa: SLF001
        ["b-101", "B-101", "", "invalid", "B101", "B-102"]
    )

    assert normalized == ["B-101", "B-102"]
    assert errors == ["INVALID", "B101"]


def test_normalize_artifact_token_rebases_absolute_repo_members(tmp_path: Path) -> None:
    artifact = tmp_path / "src" / "odylith" / "runtime" / "module.py"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("pass\n", encoding="utf-8")

    normalized = log_compass_timeline_event._normalize_artifact_token(  # noqa: SLF001
        repo_root=tmp_path,
        raw=str(artifact),
    )

    assert normalized == "src/odylith/runtime/module.py"


def test_normalize_artifact_token_preserves_external_absolute_paths(tmp_path: Path) -> None:
    external = tmp_path.parent / f"{tmp_path.name}-external.py"
    external.write_text("pass\n", encoding="utf-8")

    normalized = log_compass_timeline_event._normalize_artifact_token(  # noqa: SLF001
        repo_root=tmp_path,
        raw=str(external),
    )

    assert normalized == external.resolve().as_posix()


def test_normalize_artifacts_dedupes_and_strips_local_prefixes(tmp_path: Path) -> None:
    repo_file = tmp_path / "docs" / "guide.md"
    repo_file.parent.mkdir(parents=True, exist_ok=True)
    repo_file.write_text("# Guide\n", encoding="utf-8")

    normalized = log_compass_timeline_event._normalize_artifacts(  # noqa: SLF001
        repo_root=tmp_path,
        values=["./docs/guide.md", str(repo_file), "./docs/guide.md", ""],
    )

    assert normalized == ["docs/guide.md"]


def test_normalize_components_resolves_aliases_and_reports_unknown_values() -> None:
    normalized, errors = log_compass_timeline_event._normalize_components(  # noqa: SLF001
        values=["Registry Component", "registry-component", "missing-component", "***"],
        alias_to_component={"registry-component": "registry-component"},
    )

    assert normalized == ["registry-component"]
    assert errors == ["missing-component", "***"]
