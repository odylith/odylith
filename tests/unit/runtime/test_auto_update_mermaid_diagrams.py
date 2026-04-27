from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from odylith.runtime.surfaces import auto_update_mermaid_diagrams as mermaid


def test_render_diagrams_batch_falls_back_from_blocking_worker_job(tmp_path: Path, monkeypatch, capsys) -> None:
    rendered: list[str] = []

    class _FlakyWorker:
        def __init__(self, *, repo_root: Path, cli_version: str) -> None:  # noqa: ARG002
            self.calls = 0

        def __enter__(self) -> _FlakyWorker:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            return None

        def render_one(self, *, job, timeout_seconds: float = 60.0) -> None:  # noqa: ANN001, ARG002
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("Mermaid worker timed out after 60s")

    def _fake_render_diagram(*, repo_root: Path, source_mmd: str, source_svg: str, source_png: str, cli_version: str) -> None:  # noqa: ARG001
        rendered.append(source_mmd)

    monkeypatch.setattr(mermaid, "_MermaidWorkerSession", _FlakyWorker)
    monkeypatch.setattr(mermaid, "_render_diagram", _fake_render_diagram)

    mermaid._render_diagrams_batch(  # noqa: SLF001
        repo_root=tmp_path,
        render_jobs=(
            {"diagram_id": "D-001", "source_mmd": "one.mmd", "source_svg": "one.svg", "source_png": "one.png"},
            {"diagram_id": "D-002", "source_mmd": "two.mmd", "source_svg": "two.svg", "source_png": "two.png"},
        ),
        cli_version="11.12.0",
    )

    output = capsys.readouterr().out
    assert "- render D-001 (1/2)" in output
    assert "- render D-002 (2/2)" in output
    assert "warning: Mermaid worker unavailable while rendering D-002; falling back to one-shot renders for D-002" in output
    assert "- render D-002 (2/2) [one-shot]" in output
    assert "Mermaid worker degraded on 1 diagram(s): D-002" in output
    assert rendered == ["two.mmd"]


def test_render_diagrams_batch_raises_blocking_ids_when_one_shot_fallback_fails(tmp_path: Path, monkeypatch, capsys) -> None:
    class _DeadWorker:
        def __init__(self, *, repo_root: Path, cli_version: str) -> None:  # noqa: ARG002
            return None

        def __enter__(self) -> _DeadWorker:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            return None

        def render_one(self, *, job, timeout_seconds: float = 60.0) -> None:  # noqa: ANN001, ARG002
            raise RuntimeError("Mermaid worker timed out after 60s")

    def _failing_render_diagram(*, repo_root: Path, source_mmd: str, source_svg: str, source_png: str, cli_version: str) -> None:  # noqa: ARG001
        raise subprocess.CalledProcessError(returncode=1, cmd=["npx", "mmdc"])

    monkeypatch.setattr(mermaid, "_MermaidWorkerSession", _DeadWorker)
    monkeypatch.setattr(mermaid, "_render_diagram", _failing_render_diagram)

    with pytest.raises(RuntimeError, match="Blocking diagram ids: D-001"):
        mermaid._render_diagrams_batch(  # noqa: SLF001
            repo_root=tmp_path,
            render_jobs=(
                {"diagram_id": "D-001", "source_mmd": "one.mmd", "source_svg": "one.svg", "source_png": "one.png"},
            ),
            cli_version="11.12.0",
        )

    output = capsys.readouterr().out
    assert "warning: Mermaid worker unavailable while rendering D-001; falling back to one-shot renders for D-001" in output
    assert "warning: one-shot Mermaid render failed for D-001" in output


def test_mermaid_worker_request_prints_heartbeat(monkeypatch, capsys) -> None:
    class _FakeStdout:
        def readline(self) -> str:
            return '{"ok": true}\n'

    class _FakeStdin:
        def write(self, text: str) -> int:
            return len(text)

        def flush(self) -> None:
            return None

    class _FakeProcess:
        def __init__(self) -> None:
            self.stdin = _FakeStdin()
            self.stdout = _FakeStdout()
            self.stderr = None

        def poll(self) -> None:
            return None

    calls = {"count": 0}

    def _fake_select(read, write, error, timeout):  # noqa: ANN001
        calls["count"] += 1
        return ([], [], []) if calls["count"] == 1 else ([read[0]], [], [])

    monotonic_values = iter([0.0, 10.1])
    monkeypatch.setattr(mermaid.select, "select", _fake_select)
    monkeypatch.setattr(mermaid.time, "monotonic", lambda: next(monotonic_values))

    session = mermaid._MermaidWorkerSession(repo_root=Path("."), cli_version="11.12.0")  # noqa: SLF001
    session.process = _FakeProcess()

    response = session._request({"command": "render", "jobs": []}, heartbeat_label="Mermaid worker render for D-001")  # noqa: SLF001
    output = capsys.readouterr().out

    assert response == {"ok": True}
    assert "- heartbeat: waiting on Mermaid worker render for D-001 (10s)" in output


def test_mermaid_worker_request_raises_validation_error_for_structured_response(monkeypatch) -> None:
    class _FakeStdout:
        def readline(self) -> str:
            return (
                '{"ok": false, "name": "MermaidValidationError", "error": "D-021 failed: odylith/atlas/source/demo.mmd:19", '
                '"diagram_id": "D-021", "source_mmd": "odylith/atlas/source/demo.mmd", "line": 19, '
                '"line_context": "note right of A: bad", "detail": "Parse error on line 19"}\n'
            )

    class _FakeStdin:
        def write(self, text: str) -> int:
            return len(text)

        def flush(self) -> None:
            return None

    class _FakeProcess:
        def __init__(self) -> None:
            self.stdin = _FakeStdin()
            self.stdout = _FakeStdout()
            self.stderr = None

        def poll(self) -> None:
            return None

    monkeypatch.setattr(mermaid.select, "select", lambda read, write, error, timeout: ([read[0]], [], []))

    session = mermaid._MermaidWorkerSession(repo_root=Path("."), cli_version="11.12.0")  # noqa: SLF001
    session.process = _FakeProcess()

    with pytest.raises(mermaid.MermaidDiagramValidationError) as exc_info:
        session._request({"command": "validate", "jobs": []}, heartbeat_label="Mermaid worker syntax preflight")  # noqa: SLF001

    error = exc_info.value
    assert str(error) == "D-021 failed: odylith/atlas/source/demo.mmd:19"
    assert error.diagram_id == "D-021"
    assert error.source_mmd == "odylith/atlas/source/demo.mmd"
    assert error.line == 19
    assert error.line_context == "note right of A: bad"
    assert error.detail == "Parse error on line 19"


def test_atlas_auto_update_dry_run_prints_mutation_plan(tmp_path: Path, capsys) -> None:
    catalog_path = tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    source_mmd = tmp_path / "odylith" / "atlas" / "source" / "demo.mmd"
    source_mmd.parent.mkdir(parents=True, exist_ok=True)
    source_mmd.write_text("graph TD; A-->B;\n", encoding="utf-8")
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(
            {
                "diagrams": [
                    {
                        "diagram_id": "D-001",
                        "source_mmd": "odylith/atlas/source/demo.mmd",
                        "source_svg": "odylith/atlas/source/demo.svg",
                        "source_png": "odylith/atlas/source/demo.png",
                        "change_watch_paths": ["src/odylith/runtime"],
                        "last_reviewed_utc": "",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rc = mermaid.main(
        [
            "--repo-root",
            str(tmp_path),
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--changed-path",
            "src/odylith/runtime/example.py",
            "--runtime-mode",
            "standalone",
            "--dry-run",
        ]
    )
    output = capsys.readouterr().out

    assert rc == 0
    assert "atlas auto-update dry-run" in output
    assert "mutation_classes: repo_owned_truth" in output
    assert "mutation_classes: generated_surfaces" in output


def test_build_execution_plan_skips_render_step_for_review_only_selection(tmp_path: Path) -> None:
    plan = mermaid._build_execution_plan(  # noqa: SLF001
        repo_root=tmp_path,
        catalog_repo_path="odylith/atlas/source/catalog/diagrams.v1.json",
        render_catalog=True,
        classification=mermaid.AtlasImpactClassification(
            impacted_items=(
                {
                    "diagram_id": "D-001",
                    "source_mmd": "odylith/atlas/source/demo.mmd",
                    "source_svg": "odylith/atlas/source/demo.svg",
                    "source_png": "odylith/atlas/source/demo.png",
                },
            ),
            render_jobs=(),
            render_ids=(),
            review_only_ids=("D-001",),
        ),
    )

    assert plan.headline == "Refresh 1 impacted Atlas diagram(s) (0 render, 1 review-only)."
    assert [step.label for step in plan.steps] == [
        "Refresh catalog review markers and freshness fingerprints for the selected diagrams.",
        "Rerender the Atlas dashboard and payload bundle from the updated catalog.",
    ]
    assert any("review-only" in note for note in plan.notes)


def test_atlas_auto_update_bypasses_cached_skip_when_all_stale_diagrams_exist(
    tmp_path: Path,
    monkeypatch,
) -> None:
    catalog_path = tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    source_mmd = tmp_path / "odylith" / "atlas" / "source" / "demo.mmd"
    source_svg = tmp_path / "odylith" / "atlas" / "source" / "demo.svg"
    source_png = tmp_path / "odylith" / "atlas" / "source" / "demo.png"
    source_mmd.parent.mkdir(parents=True, exist_ok=True)
    source_mmd.write_text("graph TD; A-->B;\n", encoding="utf-8")
    source_svg.write_text("<svg />\n", encoding="utf-8")
    source_png.write_bytes(b"png")
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(
            {
                "diagrams": [
                    {
                        "diagram_id": "D-001",
                        "source_mmd": "odylith/atlas/source/demo.mmd",
                        "source_svg": "odylith/atlas/source/demo.svg",
                        "source_png": "odylith/atlas/source/demo.png",
                        "change_watch_paths": ["src/odylith/runtime"],
                        "last_reviewed_utc": "2026-01-01",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    guard_calls = {"count": 0}

    def _guard_should_not_run(**_kwargs):  # noqa: ANN003
        guard_calls["count"] += 1
        return (True, "cached", {})

    def _classification(*, items, **_kwargs):  # noqa: ANN003
        return mermaid.AtlasImpactClassification(
            impacted_items=tuple(items),
            render_jobs=(),
            render_ids=(),
            review_only_ids=("D-001",),
        )

    monkeypatch.setattr(mermaid, "_select_stale_diagram_indexes", lambda **_: [0])
    monkeypatch.setattr(mermaid, "_classify_diagram_items", _classification)
    monkeypatch.setattr(mermaid.generated_refresh_guard, "should_skip_rebuild", _guard_should_not_run)
    monkeypatch.setattr(mermaid.generated_refresh_guard, "compute_input_fingerprint", lambda **_: "fp")
    monkeypatch.setattr(mermaid.generated_refresh_guard, "record_rebuild", lambda **_: None)

    rc = mermaid.main(
        [
            "--repo-root",
            str(tmp_path),
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--all-stale",
            "--skip-render-catalog",
            "--runtime-mode",
            "standalone",
        ]
    )

    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert rc == 0
    assert guard_calls["count"] == 0
    assert payload["diagrams"][0]["last_reviewed_utc"] == mermaid.dt.date.today().isoformat()


def test_atlas_auto_update_dry_run_reports_review_only_sync_without_render_assets(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    catalog_path = tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    source_mmd = tmp_path / "odylith" / "atlas" / "source" / "demo.mmd"
    source_svg = tmp_path / "odylith" / "atlas" / "source" / "demo.svg"
    source_png = tmp_path / "odylith" / "atlas" / "source" / "demo.png"
    source_mmd.parent.mkdir(parents=True, exist_ok=True)
    source_mmd.write_text("graph TD; A-->B;\n", encoding="utf-8")
    source_svg.write_text("<svg />\n", encoding="utf-8")
    source_png.write_bytes(b"png")
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(
            {
                "diagrams": [
                    {
                        "diagram_id": "D-001",
                        "source_mmd": "odylith/atlas/source/demo.mmd",
                        "source_svg": "odylith/atlas/source/demo.svg",
                        "source_png": "odylith/atlas/source/demo.png",
                        "change_watch_paths": ["README.md"],
                        "last_reviewed_utc": "",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mermaid, "_diagram_needs_render", lambda **kwargs: False)  # noqa: ARG005

    rc = mermaid.main(
        [
            "--repo-root",
            str(tmp_path),
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--changed-path",
            "README.md",
            "--runtime-mode",
            "standalone",
            "--dry-run",
        ]
    )
    output = capsys.readouterr().out

    assert rc == 0
    assert "Refresh 1 impacted Atlas diagram(s) (0 render, 1 review-only)." in output
    assert "Selected diagrams are review-only" in output
    assert "odylith/atlas/source/demo.svg" not in output


def test_atlas_auto_update_fails_fast_on_mermaid_validation_error(tmp_path: Path, monkeypatch, capsys) -> None:
    catalog_path = tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    source_mmd = tmp_path / "odylith" / "atlas" / "source" / "demo.mmd"
    source_mmd.parent.mkdir(parents=True, exist_ok=True)
    source_mmd.write_text("flowchart TD\n  A-->B\n", encoding="utf-8")
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(
            {
                "diagrams": [
                    {
                        "diagram_id": "D-021",
                        "source_mmd": "odylith/atlas/source/demo.mmd",
                        "source_svg": "odylith/atlas/source/demo.svg",
                        "source_png": "odylith/atlas/source/demo.png",
                        "change_watch_paths": ["src/odylith/runtime"],
                        "last_reviewed_utc": "",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    render_calls: list[str] = []

    def _fake_render_diagrams_batch(*, repo_root: Path, render_jobs, cli_version: str) -> None:  # noqa: ANN001, ARG001
        raise mermaid.MermaidDiagramValidationError(
            diagram_id="D-021",
            source_mmd="odylith/atlas/source/demo.mmd",
            line=19,
            line_context="note right of A: invalid text",
            detail="Parse error on line 19",
        )

    monkeypatch.setattr(mermaid, "_render_diagrams_batch", _fake_render_diagrams_batch)
    monkeypatch.setattr(mermaid, "_render_catalog", lambda **kwargs: render_calls.append("catalog"))  # noqa: ARG005

    rc = mermaid.main(
        [
            "--repo-root",
            str(tmp_path),
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--changed-path",
            "src/odylith/runtime/example.py",
            "--runtime-mode",
            "standalone",
        ]
    )
    output = capsys.readouterr().out

    assert rc == 1
    assert render_calls == []
    assert "atlas auto-update failed" in output
    assert "- error: D-021 failed: odylith/atlas/source/demo.mmd:19" in output
    assert "- line_context: note right of A: invalid text" in output
    assert "- detail: Parse error on line 19" in output


def test_atlas_auto_update_skips_repeated_identical_sync(tmp_path: Path, monkeypatch) -> None:
    catalog_path = tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    source_mmd = tmp_path / "odylith" / "atlas" / "source" / "demo.mmd"
    readme_path = tmp_path / "README.md"
    source_mmd.parent.mkdir(parents=True, exist_ok=True)
    source_mmd.write_text("graph TD; A-->B;\n", encoding="utf-8")
    readme_path.write_text("# Demo\n", encoding="utf-8")
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(
            {
                "diagrams": [
                    {
                        "diagram_id": "D-001",
                        "source_mmd": "odylith/atlas/source/demo.mmd",
                        "source_svg": "odylith/atlas/source/demo.svg",
                        "source_png": "odylith/atlas/source/demo.png",
                        "change_watch_paths": ["README.md"],
                        "last_reviewed_utc": "",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mermaid, "_validate_diagrams_batch", lambda **kwargs: None)  # noqa: ARG005

    def _write_render_outputs(*, render_jobs, **kwargs):  # noqa: ANN001
        for job in render_jobs:
            (tmp_path / str(job["source_svg"])).write_text("<svg />\n", encoding="utf-8")
            (tmp_path / str(job["source_png"])).write_bytes(b"png")

    def _write_catalog_outputs(*, repo_root: Path, **kwargs) -> None:  # noqa: ARG001
        atlas_root = tmp_path / "odylith" / "atlas"
        atlas_root.mkdir(parents=True, exist_ok=True)
        (atlas_root / "atlas.html").write_text("<!doctype html>\n", encoding="utf-8")
        (atlas_root / "mermaid-payload.v1.js").write_text("window['__ODYLITH_MERMAID_DATA__']={};\n", encoding="utf-8")
        (atlas_root / "mermaid-app.v1.js").write_text("console.log('atlas');\n", encoding="utf-8")

    monkeypatch.setattr(mermaid, "_render_diagrams_batch", _write_render_outputs)
    monkeypatch.setattr(mermaid, "_render_catalog", _write_catalog_outputs)

    first_rc = mermaid.main(["--repo-root", str(tmp_path), "--changed-path", "README.md"])
    assert first_rc == 0

    monkeypatch.setattr(
        mermaid,
        "_render_diagrams_batch",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("Mermaid render should have been skipped")),
    )
    monkeypatch.setattr(
        mermaid,
        "_render_catalog",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("catalog render should have been skipped")),
    )

    second_rc = mermaid.main(["--repo-root", str(tmp_path), "--changed-path", "README.md"])

    assert second_rc == 0


def test_atlas_auto_update_skips_mermaid_work_for_review_only_sync(tmp_path: Path, monkeypatch) -> None:
    catalog_path = tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    source_mmd = tmp_path / "odylith" / "atlas" / "source" / "demo.mmd"
    source_svg = tmp_path / "odylith" / "atlas" / "source" / "demo.svg"
    source_png = tmp_path / "odylith" / "atlas" / "source" / "demo.png"
    readme_path = tmp_path / "README.md"
    source_mmd.parent.mkdir(parents=True, exist_ok=True)
    source_mmd.write_text("graph TD; A-->B;\n", encoding="utf-8")
    source_svg.write_text("<svg />\n", encoding="utf-8")
    source_png.write_bytes(b"png")
    readme_path.write_text("# Demo\n", encoding="utf-8")
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(
            {
                "diagrams": [
                    {
                        "diagram_id": "D-001",
                        "source_mmd": "odylith/atlas/source/demo.mmd",
                        "source_svg": "odylith/atlas/source/demo.svg",
                        "source_png": "odylith/atlas/source/demo.png",
                        "change_watch_paths": ["README.md"],
                        "last_reviewed_utc": "",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        mermaid,
        "_validate_diagrams_batch",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("Mermaid validation should have been skipped")),
    )
    monkeypatch.setattr(
        mermaid,
        "_render_diagrams_batch",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("Mermaid render should have been skipped")),
    )
    monkeypatch.setattr(mermaid, "_diagram_needs_render", lambda **kwargs: False)  # noqa: ARG005
    monkeypatch.setattr(mermaid, "_render_catalog", lambda **kwargs: None)  # noqa: ARG005

    source_mmd_mtime_before = source_mmd.stat().st_mtime_ns
    source_svg_mtime_before = source_svg.stat().st_mtime_ns
    source_png_mtime_before = source_png.stat().st_mtime_ns

    rc = mermaid.main(["--repo-root", str(tmp_path), "--changed-path", "README.md"])

    assert rc == 0
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert payload["diagrams"][0]["last_reviewed_utc"] == mermaid.dt.date.today().isoformat()
    assert payload["diagrams"][0]["reviewed_watch_fingerprints"]["README.md"]
    assert payload["diagrams"][0]["render_source_fingerprint"]
    assert source_mmd.stat().st_mtime_ns == source_mmd_mtime_before
    assert source_svg.stat().st_mtime_ns == source_svg_mtime_before
    assert source_png.stat().st_mtime_ns == source_png_mtime_before


def test_diagram_needs_render_skips_when_render_source_fingerprint_matches_comment_only_change(
    tmp_path: Path,
) -> None:
    source_mmd = tmp_path / "demo.mmd"
    source_svg = tmp_path / "demo.svg"
    source_png = tmp_path / "demo.png"
    source_mmd.write_text("%% Reviewed 2026-04-09\nflowchart TD\n  A-->B\n", encoding="utf-8")
    source_svg.write_text("<svg />\n", encoding="utf-8")
    source_png.write_bytes(b"png")

    fingerprint_cache = mermaid.diagram_freshness.ContentFingerprintCache()
    fingerprint = fingerprint_cache.mermaid_render_fingerprint(source_mmd)
    source_mmd.write_text("%% Reviewed 2026-04-10\nflowchart TD\n  A-->B\n", encoding="utf-8")

    assert (
        mermaid._diagram_needs_render(  # noqa: SLF001
            repo_root=tmp_path,
            item={
                "source_mmd": "demo.mmd",
                "source_svg": "demo.svg",
                "source_png": "demo.png",
                "render_source_fingerprint": fingerprint,
            },
            fingerprint_cache=mermaid.diagram_freshness.ContentFingerprintCache(),
        )
        is False
    )


def test_diagram_needs_render_bootstraps_from_clean_tracked_outputs(tmp_path: Path, monkeypatch) -> None:
    source_mmd = tmp_path / "demo.mmd"
    source_svg = tmp_path / "demo.svg"
    source_png = tmp_path / "demo.png"
    source_mmd.write_text("flowchart TD\n  A-->B\n", encoding="utf-8")
    source_svg.write_text("<svg />\n", encoding="utf-8")
    source_png.write_bytes(b"png")

    item = {
        "source_mmd": "demo.mmd",
        "source_svg": "demo.svg",
        "source_png": "demo.png",
    }
    monkeypatch.setattr(mermaid, "_git_paths_tracked_and_clean", lambda **kwargs: True)  # noqa: ARG005

    needs_render = mermaid._diagram_needs_render(  # noqa: SLF001
        repo_root=tmp_path,
        item=item,
        fingerprint_cache=mermaid.diagram_freshness.ContentFingerprintCache(),
    )

    assert needs_render is False
    assert item["render_source_fingerprint"]


def test_select_stale_diagram_indexes_honors_reviewed_watch_fingerprints_over_mtime(tmp_path: Path) -> None:
    source_mmd = tmp_path / "demo.mmd"
    watched = tmp_path / "watched.txt"
    source_mmd.write_text("flowchart TD\n  A-->B\n", encoding="utf-8")
    watched.write_text("same\n", encoding="utf-8")
    current_watch_fingerprint = mermaid._current_watch_fingerprints(  # noqa: SLF001
        repo_root=tmp_path,
        watch_paths=("watched.txt",),
        cache=mermaid.diagram_freshness.ContentFingerprintCache(),
    )
    watched.touch()

    indexes = mermaid._select_stale_diagram_indexes(  # noqa: SLF001
        repo_root=tmp_path,
        diagrams=[
            {
                "diagram_id": "D-001",
                "source_mmd": "demo.mmd",
                "source_svg": "demo.svg",
                "source_png": "demo.png",
                "change_watch_paths": ["watched.txt"],
                "last_reviewed_utc": mermaid.dt.date.today().isoformat(),
                "reviewed_watch_fingerprints": current_watch_fingerprint,
            }
        ],
        max_review_age_days=21,
    )

    assert indexes == []


def test_validate_diagrams_batch_falls_back_to_browser_scratch_mode_on_dompurify_runtime_error(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    validation_calls: list[tuple[str, object]] = []

    class _FallbackWorker:
        def __init__(self, *, repo_root: Path, cli_version: str) -> None:  # noqa: ARG002
            return None

        def __enter__(self) -> _FallbackWorker:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            return None

        def validate_many(self, *, jobs) -> None:  # noqa: ANN001
            validation_calls.append(("validate", list(jobs)))
            raise mermaid.MermaidDiagramValidationError(
                diagram_id="D-024",
                source_mmd="odylith/atlas/source/demo.mmd",
                detail="DOMPurify.addHook is not a function",
            )

        def render_one(self, *, job, label: str = "", timeout_seconds: float = 60.0) -> None:  # noqa: ANN001, ARG002
            validation_calls.append(("render", dict(job)))

    monkeypatch.setattr(mermaid, "_MermaidWorkerSession", _FallbackWorker)

    mermaid._validate_diagrams_batch(  # noqa: SLF001
        repo_root=tmp_path,
        validation_jobs=(
            {
                "diagram_id": "D-024",
                "source_mmd": "odylith/atlas/source/demo.mmd",
                "source_svg": "odylith/atlas/source/demo.svg",
                "source_png": "odylith/atlas/source/demo.png",
            },
        ),
        cli_version="11.12.0",
    )

    output = capsys.readouterr().out

    assert "warning: Mermaid syntax preflight hit a Node parser contract drift" in output
    assert "- validate D-024 (1/1) [browser]" in output
    assert validation_calls[0][0] == "validate"
    assert validation_calls[1][0] == "render"
    browser_job = validation_calls[1][1]
    assert browser_job["source_svg"] != "odylith/atlas/source/demo.svg"
    assert browser_job["source_png"] != "odylith/atlas/source/demo.png"
    assert "odylith-mermaid-validate-" in browser_job["source_svg"]
    assert "odylith-mermaid-validate-" in browser_job["source_png"]


def test_render_catalog_uses_current_python_and_absolutized_pythonpath(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(cmd, cwd, env, check):  # noqa: ANN001
        captured["cmd"] = list(cmd)
        captured["cwd"] = cwd
        captured["env"] = dict(env)
        captured["check"] = check

        class _Completed:
            returncode = 0

        return _Completed()

    monkeypatch.setenv("PYTHONPATH", "src")
    monkeypatch.setattr(mermaid.subprocess, "run", _fake_run)

    mermaid._render_catalog(repo_root=tmp_path, fail_on_stale=False, runtime_mode="standalone")  # noqa: SLF001

    assert captured["cmd"][0] == mermaid.sys.executable
    assert captured["cmd"][1:4] == ["-m", "odylith.runtime.surfaces.render_mermaid_catalog_refresh", "--repo-root"]
    assert captured["cwd"] == str(tmp_path)
    assert captured["check"] is True
    assert captured["env"]["PYTHONPATH"] == str((Path.cwd() / "src").resolve())


def test_render_catalog_uses_in_process_wrapper_outside_standalone(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _RefreshModule:
        @staticmethod
        def main(argv: list[str]) -> int:
            captured["argv"] = list(argv)
            return 0

    import odylith.runtime.surfaces as surfaces_pkg

    refresh_module = _RefreshModule()
    monkeypatch.setitem(sys.modules, "odylith.runtime.surfaces.render_mermaid_catalog_refresh", refresh_module)
    monkeypatch.setattr(surfaces_pkg, "render_mermaid_catalog_refresh", refresh_module, raising=False)

    mermaid._render_catalog(repo_root=tmp_path, fail_on_stale=True, runtime_mode="auto")  # noqa: SLF001

    assert captured["argv"] == [
        "--repo-root",
        str(tmp_path),
        "--runtime-mode",
        "auto",
        "--fail-on-stale",
    ]
