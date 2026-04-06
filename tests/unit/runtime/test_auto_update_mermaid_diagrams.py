from __future__ import annotations

import json
import subprocess
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

    def _fake_validate_diagrams_batch(*, repo_root: Path, validation_jobs, cli_version: str) -> None:  # noqa: ANN001, ARG001
        raise mermaid.MermaidDiagramValidationError(
            diagram_id="D-021",
            source_mmd="odylith/atlas/source/demo.mmd",
            line=19,
            line_context="note right of A: invalid text",
            detail="Parse error on line 19",
        )

    monkeypatch.setattr(mermaid, "_validate_diagrams_batch", _fake_validate_diagrams_batch)
    monkeypatch.setattr(mermaid, "_render_diagrams_batch", lambda **kwargs: render_calls.append("render"))  # noqa: ARG005
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
    assert captured["cmd"][1:4] == ["-m", "odylith.runtime.surfaces.render_mermaid_catalog", "--repo-root"]
    assert captured["cwd"] == str(tmp_path)
    assert captured["check"] is True
    assert captured["env"]["PYTHONPATH"] == str((Path.cwd() / "src").resolve())
