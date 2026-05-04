import hashlib
from pathlib import Path

from odylith.runtime.common import diagram_freshness


def test_normalize_mermaid_render_source_ignores_review_comments() -> None:
    definition = "%% Reviewed 2026-04-09\nflowchart TD\n  A-->B  \n"

    normalized = diagram_freshness.normalize_mermaid_render_source(definition)

    assert normalized == "flowchart TD\n  A-->B\n"


def test_mermaid_render_fingerprint_includes_atlas_render_style(tmp_path: Path) -> None:
    source_mmd = tmp_path / "demo.mmd"
    source_mmd.write_text("%% Reviewed 2026-05-03\nflowchart TD\n  A-->B\n", encoding="utf-8")
    normalized = diagram_freshness.normalize_mermaid_render_source(source_mmd.read_text(encoding="utf-8"))
    raw_source_fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    fingerprint = diagram_freshness.ContentFingerprintCache().mermaid_render_fingerprint(source_mmd)

    assert diagram_freshness.mermaid_render_style_fingerprint()
    assert fingerprint != raw_source_fingerprint


def test_mermaid_render_style_fingerprint_includes_worker_polish(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    config_path = tmp_path / "mermaid_render_config.json"
    worker_path = tmp_path / "mermaid_cli_worker.mjs"
    config_path.write_text('{"theme": "base"}\n', encoding="utf-8")
    worker_path.write_text("const clusterPalette = [];\n", encoding="utf-8")
    monkeypatch.setattr(diagram_freshness, "_MERMAID_RENDER_CONFIG_PATH", config_path)
    monkeypatch.setattr(diagram_freshness, "_MERMAID_RENDER_WORKER_PATH", worker_path)

    first = diagram_freshness.mermaid_render_style_fingerprint()
    worker_path.write_text("const clusterPalette = ['changed'];\n", encoding="utf-8")
    second = diagram_freshness.mermaid_render_style_fingerprint()

    assert first != second


def test_watched_path_fingerprints_ignore_mtime_only_churn(tmp_path: Path) -> None:
    watched_path = tmp_path / "README.md"
    watched_path.write_text("# Demo\n", encoding="utf-8")
    cache = diagram_freshness.ContentFingerprintCache()

    first = diagram_freshness.watched_path_fingerprints(
        repo_root=tmp_path,
        watched_paths=("README.md",),
        resolve_path=lambda token: (tmp_path / token).resolve(),
        cache=cache,
    )
    watched_path.touch()
    second = diagram_freshness.watched_path_fingerprints(
        repo_root=tmp_path,
        watched_paths=("README.md",),
        resolve_path=lambda token: (tmp_path / token).resolve(),
        cache=diagram_freshness.ContentFingerprintCache(),
    )

    assert first == second


def test_watched_path_fingerprints_ignore_python_bytecode_cache(tmp_path: Path) -> None:
    watched_dir = tmp_path / "src" / "odylith" / "runtime" / "intervention_engine"
    module_path = watched_dir / "value_engine.py"
    bytecode_path = watched_dir / "__pycache__" / "value_engine.cpython-313.pyc"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text("def value_engine() -> str:\n    return 'ok'\n", encoding="utf-8")
    bytecode_path.parent.mkdir(parents=True, exist_ok=True)
    bytecode_path.write_bytes(b"compiled")

    first = diagram_freshness.watched_path_fingerprints(
        repo_root=tmp_path,
        watched_paths=("src/odylith/runtime/intervention_engine",),
        resolve_path=lambda token: (tmp_path / token).resolve(),
        cache=diagram_freshness.ContentFingerprintCache(),
    )
    bytecode_path.unlink()
    bytecode_path.parent.rmdir()
    second = diagram_freshness.watched_path_fingerprints(
        repo_root=tmp_path,
        watched_paths=("src/odylith/runtime/intervention_engine",),
        resolve_path=lambda token: (tmp_path / token).resolve(),
        cache=diagram_freshness.ContentFingerprintCache(),
    )

    assert first == second
