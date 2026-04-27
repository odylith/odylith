from pathlib import Path

from odylith.runtime.common import diagram_freshness


def test_normalize_mermaid_render_source_ignores_review_comments() -> None:
    definition = "%% Reviewed 2026-04-09\nflowchart TD\n  A-->B  \n"

    normalized = diagram_freshness.normalize_mermaid_render_source(definition)

    assert normalized == "flowchart TD\n  A-->B\n"


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
